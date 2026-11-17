"""Shape A — deterministic workflow. Student work.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Suggested steps. Money stays in code (`lab8.tools.compute_compensation`).

1. Open the store. Read the claim through `get_claim_view` (not SELECT *).
2. Missing order_id -> status `needs_info`. Do not write the ledger.
3. `lookup_order`. If not visible -> `escalated`. Do not copy phone, address, item, internal note.
4. Quote from the order row. Ignore delay numbers written in the ticket.
5. Quote amount 0 -> `denied`. Do not call issue_refund.
6. Quote amount > 0 -> `durability.issue_refund(conn, claim_id, <full quote>)`.
   Pass the FULL quote. The host checks the claim's own approval and subtracts
   what earlier claims already got for the same order (T13, T14). Do not
   subtract it yourself or the host subtracts twice.
   Auth failure or order already refunded -> `denied` (the host writes `policy_denied`).
   `proposal_amount` stays the full quote. Amount conflict -> `failed`.
7. Success -> `resolved`. One ledger row, one `refund_committed` audit.
8. Use MockLLM only to draft the reply text, if you want a model call at all.

The model must not choose the refund amount and must not commit the refund.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "workflow"


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    # Mở DB, chạy logic, và LUÔN đóng connection (kể cả khi có InjectedCrash).
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _done(
    conn: sqlite3.Connection,
    claim_id: str,
    seed: int,
    budget: Budget,
    trace: Trace,
    status: str,
    proposal: int = 0,
    reason: str | None = None,
) -> RunResult:
    """Một cửa ra duy nhất: ghi event 'decision' vào trace rồi gọi finish().

    finish() tự ghi file trace, tự lấy refund_effects + committed_audit_count từ ledger.
    Mọi nhánh return trong _run đều nên đi qua hàm này -> không bao giờ thiếu trace.
    """
    trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
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


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    # ---------------- BƯỚC 1 — Đọc claim qua view có allowlist ----------------
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)  # view không có parent_secret
    if not claim["found"]:
        return _done(conn, claim_id, seed, budget, trace, "failed", reason="unknown_claim")
    # Chỉ ghi field an toàn; KHÔNG ghi nguyên claim / ticket vào trace.
    trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(claim["order_id"])})

    # ---------------- BƯỚC 2 — Thiếu order_id -> needs_info ----------------
    if not claim["order_id"]:
        # Không đoán mã đơn từ ticket, không ghi ledger.
        return _done(conn, claim_id, seed, budget, trace, "needs_info", reason="missing_order_id")

    # ---------------- BƯỚC 3 — Tra đơn + kiểm quyền sở hữu ----------------
    budget.add_tool(tool_cost())
    order_view = lookup_order(conn, claim["order_id"], claim["principal_id"])
    if not order_view["visible"]:
        # "not_found" hoặc "outside_principal_scope". Không trả PII.
        return _done(conn, claim_id, seed, budget, trace, "escalated", reason=order_view["reason"])
    order = order_view["order"]
    trace.add("order", safe_dump(order))  # đã allowlist, không SĐT / địa chỉ

    # ---------------- BƯỚC 4 — Quote do CODE tính từ order row ----------------
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order)  # dùng delay_days trong DB, bỏ qua số trong ticket
    proposal = int(quote["amount_vnd"])
    trace.add("quote", safe_dump(quote))

    # ---------------- BƯỚC 5 — Quote 0 -> denied, KHÔNG gọi host ----------------
    if proposal <= 0:
        return _done(conn, claim_id, seed, budget, trace, "denied", 0, quote.get("reason"))

    # ---------------- BƯỚC 6 — Ghi refund qua cổng host ----------------
    try:
        # Truyền QUOTE ĐẦY ĐỦ; host tự kiểm approval, trần theo đơn, idempotency (T13, T14).
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        # Flush trace rồi ném tiếp — không được nuốt (T12).
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    trace.add("host", {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]})

    # ---------------- BƯỚC 7 — Map kết quả host -> status ----------------
    if not outcome["ok"]:
        # conflict: gọi lại với số khác số đã commit -> failed
        # còn lại: approval hỏng / sai claim / đơn đã hoàn đủ -> denied (host đã ghi policy_denied)
        status = "failed" if outcome["conflict"] else "denied"
        return _done(conn, claim_id, seed, budget, trace, status, proposal, outcome["reason"])

    # proposal vẫn là quote đầy đủ; số thực ghi ledger do host tính sau khi cap.
    return _done(conn, claim_id, seed, budget, trace, "resolved", proposal)
