"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.

Boundary in this shape
----------------------
Orchestrator (code): owns the claim row, builds the allowlisted handoff, reads the
quote produced by `compute_compensation` on the *order row*, and is the only
caller of `durability.issue_refund`.
Investigator: sees only the sanitized handoff and the read tools it names.
MockLLM: plans and drafts text. It never decides an amount, and the delay the
ticket *claims* is never used (ticket text is user data, not instructions).

Deliberately NOT traced: the claim row (parent_secret, raw_headers), the ticket
text, raw order rows (phone, address, internal_note, item_name), approval rows.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"
INVESTIGATOR_TOOLS = [
    "lookup_order",
    "lookup_policy",
    "lookup_refund_history",
    "compute_compensation",
]


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": int(proposal), "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    try:
        return _orchestrate(conn, claim_id, seed=seed, crash_at=crash_at, budget=budget, trace=trace, done=done)
    except InjectedCrash:
        # Fault lab: flush what we have, then let the crash reach the caller (T12).
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    except Exception as exc:  # run_claim must never raise; report a failed trial instead.
        return done("failed", 0, f"exception:{type(exc).__name__}")


def _orchestrate(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
    budget: Budget,
    trace: Trace,
    done,
) -> RunResult:
    # Only the columns the orchestrator needs. Never SELECT * (parent_secret, raw_headers).
    budget.add_tool(tool_cost())
    row = conn.execute(
        "SELECT claim_id, principal_id, order_id, ticket FROM claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if row is None:
        return done("failed", 0, "unknown_claim")

    # The model reads the ticket to plan. Its output never feeds the amount.
    complete(budget, seed=seed, purpose="plan", prompt=row["ticket"] or "")
    trace.add("plan", {"steps": ["check_order_id", "handoff", "investigate", "quote", "issue_refund"]})

    order_id = row["order_id"]
    if not order_id:
        # Do not mine an order id from the ticket text.
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        return done("needs_info", 0, "missing_order_id")

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="investigate_claim",
        facts={},
        allowed_tools=list(INVESTIGATOR_TOOLS),
    )
    trace.add("handoff", safe_dump(handoff))

    investigated = run_readonly_investigators(conn, budget, handoff, principal_id=row["principal_id"])
    tools: dict[str, Any] = investigated["tools"]
    order_view = tools.get("lookup_order") or {}
    history = tools.get("lookup_refund_history") or {}
    policies = (tools.get("lookup_policy") or {}).get("policies") or []
    trace.add("investigator", _investigator_summary(order_view, history, policies))

    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return done("escalated", 0, order_view.get("reason") or "order_not_visible")

    # The investigator only saw the claim's own order. Refuse a view for any other order.
    if (order_view.get("order") or {}).get("order_id") != order_id:
        return done("escalated", 0, "order_view_mismatch")

    quote = tools.get("compute_compensation") or {}
    if "amount_vnd" not in quote:
        return done("failed", 0, "missing_quote")
    proposal = int(quote["amount_vnd"])
    trace.add(
        "quote",
        {
            "amount_vnd": proposal,
            "reason": quote.get("reason"),
            "clause_ids": list(quote.get("clause_ids") or []),
        },
    )

    if proposal <= 0:
        complete(budget, seed=seed, purpose="draft", prompt="denied")
        return done("denied", 0, quote.get("reason") or "zero_quote")

    # Full quote. The host checks approval, per-order cap, and idempotency.
    # crash_at is forwarded; InjectedCrash propagates (handled in _run).
    outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    trace.add(
        "host",
        {
            "ok": bool(outcome["ok"]),
            "reason": outcome["reason"],
            "conflict": bool(outcome["conflict"]),
        },
    )
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return done(status, proposal, outcome["reason"])
    return done("resolved", proposal, None)


def _investigator_summary(
    order_view: dict[str, Any],
    history: dict[str, Any],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allowlisted findings only. lookup_order already strips PII fields."""
    summary: dict[str, Any] = {
        "order_visible": bool(order_view.get("visible")),
        "order_reason": order_view.get("reason"),
        "policy_ids": [p.get("policy_id") for p in policies],
    }
    order = order_view.get("order")
    if order:
        summary["order"] = {
            key: order.get(key)
            for key in ("order_id", "status", "delay_days", "shipping_fee_vnd", "paid_vnd", "damage_verified", "carrier")
        }
    if history.get("visible"):
        summary["refund_history"] = {
            "refund_count": int(history.get("refund_count") or 0),
            "refunded_vnd": int(history.get("refunded_vnd") or 0),
        }
    return summary
