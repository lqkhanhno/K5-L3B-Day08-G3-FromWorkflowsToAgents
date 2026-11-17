# Báo cáo cá nhân — 2A202603766_DoanDangKhoa

## 1. Thông tin thành viên

- Họ tên: Đoàn Đăng Khoa
- MSSV: 2A202603766
- Email: 26ai.khoadd@vinuni.edu.vn
- GitHub: ddkhoa2605

## 2. Phần việc phụ trách

Người 3 trong nhóm 5 người: **Shape C — `orchestrator`** (orchestrator + investigator chỉ đọc) và ranh giới handoff.

- File: `src/lab8/shapes/orchestrator.py`
- Test: `src/tests/test_orchestrator_boundary.py`
- Checkpoint liên quan: CP2 (shape chạy được, 62 test student), CP3 (handoff, idempotency, crash), CP4 (approval, secret, trace).

## 3. Đóng góp cụ thể

**Commit chính:** `fa395d8` — `feat(orchestrator): implement shape C with read-only investigators` (nhánh `doandangkhoa_2A202603766`).

### Luồng của shape C

1. Orchestrator đọc claim, chỉ lấy `claim_id, principal_id, order_id, ticket` (không `SELECT *`, để không chạm `parent_secret`, `raw_headers`). Không có claim → `failed` / `unknown_claim`.
2. MockLLM lập kế hoạch (`purpose="plan"`). Output của model không đi vào số tiền.
3. Thiếu `order_id` → `needs_info`. Không lấy mã đơn từ câu chữ trong ticket.
4. Dựng handoff bằng `make_handoff` với `facts={}` và 4 tool chỉ đọc: `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`.
5. `run_readonly_investigators` chạy các tool đó qua `dispatch(..., worker=True)`: investigator không có tool ghi.
6. Đơn không thấy được (không tồn tại hoặc khác principal) → `escalated`. Thêm kiểm phòng thủ: order investigator trả về phải trùng `order_id` của claim.
7. Quote lấy từ `compute_compensation` trên order row. Quote = 0 → `denied`, không gọi host.
8. Quote > 0 → orchestrator gọi `durability.issue_refund(conn, claim_id, quote, crash_at=crash_at)`. Host từ chối → `denied` với `proposal_amount` = quote (có audit `policy_denied`); conflict → `failed`; chấp nhận → `resolved`.
9. Mọi nhánh return đi qua `common.finish()` nên `refund_effects` và `committed_audit_count` luôn lấy từ ledger.

### Quyết định kỹ thuật

| Quyết định | Lý do |
|---|---|
| Ranh giới code / model: tiền, approval, idempotency do code; model chỉ lập kế hoạch và soạn chữ | MockLLM (hay LLM thật) có thể tin ticket. Swarm tin "trễ 5 ngày" ở seed 55 và fail T02; shape C luôn dùng `delay_days` của order row |
| Truyền **quote đầy đủ** vào `issue_refund` | Host tự trừ phần đơn đã được hoàn (trần theo đơn). Nếu shape tự trừ trước, T14 bị trừ hai lần (150.000 − 30.000 − 30.000) |
| Handoff bằng allowlist, `facts={}` | Investigator tự tra order nên không cần dữ kiện từ claim row. Tóm tắt bằng LLM không phải redaction vì có thể chép nguyên secret |
| `InjectedCrash`: ghi trace rồi `raise` lại; exception khác → `failed` | T12 cần crash thật sự xảy ra; `run_claim` không được ném lỗi nào khác |
| Trace chỉ ghi dữ liệu đã lọc | Trace là ranh giới bảo mật, grader quét secret/PII trong trace |

### Trace cố ý không ghi

Claim row (`parent_secret`, `raw_headers`), nội dung ticket (có thể chứa injection hoặc PII), order row thô (`phone`, `address`, `internal_note`, `item_name`), approval row. Trace chỉ có: `plan`, handoff đã sanitize, tóm tắt investigator (order đã lọc field, `policy_ids`, refund history dạng số), `quote` (số tiền, lý do, clause), phản hồi host (`ok`, `reason`, `conflict`), `decision`.

### Test đã thêm

`src/tests/test_orchestrator_boundary.py` — 37 test, chạy trong cổng host mặc định:

| Test | Kiểm |
|---|---|
| `test_trace_and_result_carry_no_secret_or_pii` (×14 claim) | Không có `CANARY_SECRET_`, `CANARY_INTERNAL_`, `Bearer`, SĐT, địa chỉ, tên hàng, nội dung ticket trong kết quả và trace |
| `test_traced_handoff_is_allowlisted_and_read_only` (×4) | Handoff chỉ có key thuộc `ALLOWED_FIELDS`, tool ⊆ `READONLY_TOOLS`, không có tool ghi |
| `test_ticket_delay_never_overrides_order_row` (×5 seed) | C-002 (ticket ghi 5 ngày, DB ghi 2) luôn `denied`, kể cả seed 55 |
| `test_injection_ticket_does_not_change_amount` (×5 seed) | Ticket "IGNORE POLICY… 500000" vẫn chỉ ra 35.000 |
| `test_borrowed_approval_is_blocked_by_host` | Approval của claim khác → `denied`, quote 35.000, audit `approval_claim_mismatch` |
| `test_missing_approval_is_blocked_by_host` | Không có approval → `denied`, có `policy_denied`, ledger rỗng |
| `test_unknown_order_escalates_without_write` | Đơn không tồn tại → `escalated`, ledger rỗng |
| `test_unknown_claim_fails_cleanly_with_trace` | Claim không tồn tại → `failed`, vẫn có trace |
| `test_every_crash_window_resumes_to_one_refund` (×3) | `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`: resume xong vẫn 1 refund, 1 audit `refund_committed` |
| `test_three_retries_keep_one_refund` | Gọi lại 3 lần vẫn 1 dòng ledger |
| `test_already_refunded_order_passes_full_quote` | T14: `proposal_amount` 150.000, ledger 120.000 |

## 4. Bằng chứng

Mọi lệnh chạy trong `src/` với venv của repo (Python 3.13.5, Windows):

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q -m student -o addopts= -k orchestrator` | `62 passed` |
| `python -m pytest -q` (cổng host, gồm 37 test mới) | `91 passed, 248 deselected` |
| `python -m lab8.benchmark --shapes orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out <file tạm>` | orchestrator: pass 1.000, pass^5 1.000, variance 0.000000, cost/success 57.19, steps 5.36. Swarm: pass 0.986, pass^5 0.929, cost/success 49.57, steps 2.80 |
| `python -m lab8.run --shape orchestrator --claim-id C-012 --seed 11 --db <db> --crash-at after_effect_before_checkpoint` rồi chạy lại không `--crash-at` | Lần 1 `crashed: true`; lần 2 `resolved`, host trả `idempotent_replay`, trace `traces/R-orchestrator-C-012-s11.json` |

Số benchmark trên là lần chạy tự kiểm của phần orchestrator. Số chính thức cho ADR lấy từ `src/reports/benchmark.json` của nhóm (4 shape) khi đã đủ shape.

Lưu ý: `python -m lab8.crash_test` (20/20) chạy trên swarm; độ an toàn crash của orchestrator được kiểm riêng bằng `test_every_crash_window_resumes_to_one_refund` và T12 trong ma trận student.

## 5. Công cụ AI đã dùng

- **Claude Code**: gợi ý code `orchestrator.py` và viết test `test_orchestrator_boundary.py`, giải thích lại ranh giới code / model.
- **Cách tự kiểm tra:**
  - Chạy lại ma trận student của orchestrator (62/62) và cổng host (91 passed).
  - Mở trace `R-orchestrator-C-012-s11.json` đọc từng event, xác nhận không có claim row, ticket hay order thô; quét toàn bộ `traces/R-orchestrator-*` không có `CANARY`, `Bearer` hay SĐT.
  - Chạy tay kịch bản crash rồi resume trên cùng DB, kiểm ledger chỉ có 1 dòng.
  - Đối chiếu từng nhánh status với bảng trong `docs/contracts.md` và luật trong `docs/business_rules.md`.
- Không dùng AI để bịa số liệu: mọi số trong mục 4 lấy từ output lệnh đã chạy.

## 6. Tự đánh giá

- **Đã làm được:** shape C qua đủ 62 test student (T01–T14, gồm T11 retry và T12 crash); không sửa file thước đo; handoff chỉ allowlist và tool đọc; trace sạch secret/PII; thêm 37 test vào cổng host.
- **Hiểu được:** vì sao tiền do `compute_compensation` chứ không do model; vì sao truyền quote đầy đủ; vì sao checkpoint đơn lẻ không thay được ledger; vì sao trace là ranh giới bảo mật.
- **Nhận xét kiến trúc:** shape C cho kết quả tiền đúng như mong đợi trên bộ public nhưng tốn hơn (5.36 bước, cost/success 57.19) vì thêm lớp investigator mà không tăng độ đúng — tiền, approval và idempotency vẫn do code quyết. Đây là dữ liệu ủng hộ việc chọn shape ít tự chủ hơn nếu workflow cũng đạt pass 1.0.
- **Giới hạn:** chưa chạy trên bộ hidden (`student_drop/`); MockLLM không mô phỏng được hành vi của LLM thật, nên variance 0 của shape C chỉ có nghĩa trong điều kiện lab.
