# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm:
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Nhóm hiểu bài toán thế nào, chia việc ra sao, thứ tự làm bốn shape.

...

## 3. Giải pháp

Mô tả ba shape nhóm viết (workflow, single, orchestrator): mỗi shape đọc gì, quyết định gì, gọi host ra sao. Chỉ rõ ranh giới code / model (tham khảo [docs/architecture.md](../../docs/architecture.md)), cách handoff được sanitize và trace ghi những event nào.

### 3.1 Shape A — Workflow (Nguyễn Hữu Thịnh)

Bản đầy đủ: [workflow_architecture.md](workflow_architecture.md). Code: `src/lab8/shapes/workflow.py`.

**Đọc gì.** Shape đọc claim qua `get_claim_view`, view này không có `parent_secret`. Sau đó đọc order qua `lookup_order` theo `principal_id`, order trả về đã qua allowlist nên không có SĐT, địa chỉ, tên hàng hay ghi chú nội bộ.

**Quyết định gì.** Luồng Python cố định, không gọi model (0 model call):

| Điều kiện | Kết quả |
| --- | --- |
| Claim không tồn tại | `failed` |
| Thiếu `order_id` | `needs_info`, không đoán mã đơn từ ticket |
| Không thấy đơn hoặc sai principal | `escalated` |
| `compute_compensation` trên order row ra quote = 0 | `denied`, **không** gọi host |
| Quote > 0 | Gọi `durability.issue_refund` với **quote đầy đủ** và `crash_at` |

**Gọi host ra sao.** Host kiểm approval, trần theo đơn và idempotency `refund:{claim_id}`. Khi `ok` thì `resolved`. Khi `conflict` thì `failed`. Khi host từ chối thì `denied` và host ghi `policy_denied`. `proposal_amount` luôn là quote đầy đủ (T13, T14). Shape không nuốt `InjectedCrash`: ghi trace trước rồi ném tiếp (T12).

**Ranh giới code / model.** Tiền do `compute_compensation` tính, chỉ dùng policy `is_current`. Approval, cap và ghi ledger do host làm. Ticket chỉ là dữ liệu: số ngày trễ hay số tiền khách tự ghi không được dùng.

**Trace.** Gồm các event `claim` (`claim_id`, `has_order_id`), `order` (đã allowlist), `quote`, `host` (`ok`, `reason`, `conflict`), `crash` (khi bị inject) và `decision`. Trace không ghi ticket, claim row hay order row thô. Mọi nhánh return đều đi qua `finish()`.

**Kết quả.** Student test 62/62. Test boundary `tests/test_workflow_boundary.py` 31/31. Benchmark public (`src/reports/benchmark_workflow.json`, 14 claim × seed 11–55): pass 1.000, pass^5 1.000, var 0, cost/success 27.86 VND mô phỏng. Cùng điều kiện, swarm đạt 0.986, 0.929 và 49.57, sai `C-002` ở seed 55 vì tin số ngày ghi trong ticket.

...

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (từ `src/reports/benchmark.json`): pass rate, pass^5, seed min–max, variance, cost/success, mean/p95 steps. Kèm crash safety (`src/reports/crash.json`) và, nếu có, kết quả tự kiểm trên `student_drop/`.

...

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Lỗi gặp phải (kèm lệnh, output hoặc ảnh chụp) và cách nhóm xử lý.

...

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Nêu thêm giới hạn của nhóm và điều kiện làm kết luận thay đổi.

...

## 8. Tài liệu tham khảo

...
