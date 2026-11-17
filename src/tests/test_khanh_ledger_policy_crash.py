"""Regression tests by Le Quoc Khanh: host boundaries through completed shapes.

Only temporary databases are mutated; official fixtures and host code stay intact.
Every delivered shape (workflow, single, orchestrator) must behave the same
behind the host gate.
"""

import json

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash
from lab8.shapes import SHAPES


@pytest.fixture(params=["workflow", "single", "orchestrator"])
def run_shape(request):
    return SHAPES[request.param]


def edit_db(path, sql, params=()):
    conn = connect(path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def rows(path, sql, params=()):
    conn = connect(path)
    try:
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def effects(path):
    return rows(path, "SELECT * FROM refund_ledger ORDER BY claim_id")


def audits(path, claim_id, event):
    return rows(path, "SELECT * FROM audit_events WHERE claim_id = ? AND event_type = ?", (claim_id, event))


@pytest.mark.parametrize("sql,params,reason", [
    ("UPDATE claims SET approval_id = NULL WHERE claim_id = 'C-001'", (), "missing_approval"),
    ("UPDATE claims SET approval_id = 'A-NOT-FOUND' WHERE claim_id = 'C-001'", (), "missing_approval"),
    ("UPDATE approvals SET claim_id = 'C-OTHER' WHERE approval_id = 'A-001'", (), "approval_claim_mismatch"),
    ("UPDATE approvals SET status = 'revoked' WHERE approval_id = 'A-001'", (), "approval_revoked"),
    ("UPDATE approvals SET expires_at = '2026-11-14' WHERE approval_id = 'A-001'", (), "approval_expired"),
    ("UPDATE approvals SET approved_vnd = ? WHERE approval_id = 'A-001'", (0,), "non_positive_amount"),
    ("UPDATE approvals SET approved_vnd = ? WHERE approval_id = 'A-001'", (-1,), "non_positive_amount"),
])
def test_invalid_approval_retry_never_writes(public_db, run_shape, sql, params, reason):
    edit_db(public_db, sql, params)
    before = effects(public_db)
    for seed in (11, 55):
        result = run_shape("C-001", seed=seed, store_path=str(public_db))
        assert result.status == "denied"
        assert result.proposal_amount == 35000
        assert result.refund_effects == []
        assert result.committed_audit_count == 0
    assert effects(public_db) == before  # Includes other claims: no disguised write.
    denied = audits(public_db, "C-001", "policy_denied")
    assert len(denied) == 1
    assert json.loads(denied[0]["details_json"])["reason"] == reason
    assert audits(public_db, "C-001", "refund_committed") == []


@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
@pytest.mark.parametrize("claim_id,quote,amount", [("C-001", 35000, 10000), ("C-014", 150000, 120000)])
def test_capped_refund_crash_and_retries(public_db, run_shape, crash_at, claim_id, quote, amount):
    # C-001: approval cap. C-014: subtract 30000 already paid on this order.
    if claim_id == "C-001":
        edit_db(public_db, "UPDATE approvals SET approved_vnd = 10000 WHERE approval_id = 'A-001'")
    before = effects(public_db)
    with pytest.raises(InjectedCrash):
        run_shape(claim_id, seed=11, store_path=str(public_db), crash_at=crash_at)
    new_rows = [r for r in effects(public_db) if r not in before]
    assert len(new_rows) == (0 if crash_at == "before_effect" else 1)
    assert len(audits(public_db, claim_id, "refund_committed")) == len(new_rows)
    for seed in (11, 22, 55):
        result = run_shape(claim_id, seed=seed, store_path=str(public_db))
        assert result.status == "resolved"
        assert result.proposal_amount == quote
        assert result.committed_audit_count == 1
    final = effects(public_db)
    assert all(r in final for r in before)
    new_rows = [r for r in final if r not in before]
    assert len(new_rows) == 1
    assert new_rows[0]["claim_id"] == claim_id
    assert new_rows[0]["amount_vnd"] == amount
    assert new_rows[0]["idempotency_key"] == f"refund:{claim_id}"
    assert len(audits(public_db, claim_id, "refund_committed")) == 1
    assert len(rows(public_db, "SELECT * FROM checkpoints WHERE claim_id = ? AND step = 'issue_refund'", (claim_id,))) == 1


def test_changed_quote_retry_preserves_committed_money(public_db, run_shape):
    first = run_shape("C-001", seed=11, store_path=str(public_db))
    assert first.status == "resolved"
    before = effects(public_db)
    edit_db(public_db, "UPDATE orders SET shipping_fee_vnd = 10000 WHERE order_id = 'O-107'")
    retry = run_shape("C-001", seed=22, store_path=str(public_db))
    assert retry.status == "failed"
    assert retry.proposal_amount == 10000
    assert retry.error_reason == "amount_conflict"
    assert effects(public_db) == before
    assert len(audits(public_db, "C-001", "refund_committed")) == 1
    assert len(audits(public_db, "C-001", "amount_conflict")) == 1


def test_second_claim_cannot_refund_same_order_again(public_db, run_shape):
    # Give C-010 a valid, own approval; rejection must be the order cap.
    edit_db(public_db, "INSERT INTO approvals VALUES ('A-KHANH-010', 'C-010', 35000, 'valid', '2026-12-31')")
    edit_db(public_db, "UPDATE claims SET approval_id = 'A-KHANH-010' WHERE claim_id = 'C-010'")
    assert run_shape("C-001", seed=11, store_path=str(public_db)).status == "resolved"
    before = effects(public_db)
    for seed in (22, 55):
        result = run_shape("C-010", seed=seed, store_path=str(public_db))
        assert result.status == "denied"
        assert result.proposal_amount == 35000
        assert result.error_reason == "order_already_refunded"
    assert effects(public_db) == before
    assert audits(public_db, "C-010", "refund_committed") == []
    assert len(audits(public_db, "C-010", "policy_denied")) == 1
