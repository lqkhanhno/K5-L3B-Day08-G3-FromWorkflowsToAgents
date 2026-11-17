# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: G3 (Lớp L3B)
- Thành viên: xem `TEAM.md` — 5 người: Thịnh (workflow), Khánh (ledger/policy/crash), Thắng (Durability & Security), Khoa (orchestrator), Minh (single)
- Commit chốt (trùng `report/team/decision_adr.md`): COMMIT_CHOT

## 2. Mục tiêu và cách tiếp cận

Bài toán hoàn tiền cho khiếu nại vận đơn có một đặc điểm: quyết định nguy hiểm (số tiền, approval, ghi sổ) đều có thể xác định bằng quy tắc, phần cần model chỉ là đọc và chọn bước. Nhóm đặt nguyên tắc từ đầu: mọi shape phải đi qua cùng một cổng host (`policy.authorize` + `durability.issue_refund`), model không bao giờ chạm được tool ghi, và ticket của khách chỉ là dữ liệu.

Chia việc theo năm vai: một người làm shape A workflow trước vì nó cố định và chốt contract gọi host; một người làm shape C orchestrator; một người làm shape B single; một người giữ mảng ledger/policy/crash và viết test hồi quy chạy xuyên qua các shape; một người làm QA Durability & Security độc lập, viết test để tìm cách phá cả ba shape (swarm có sẵn của lab dùng làm reference). Thứ tự làm: workflow trước, rồi orchestrator và single song song, QA và test hồi quy chạy liên tục qua từng PR. Mọi số liệu trong báo cáo này lấy từ file trong `src/reports/` do lệnh benchmark/crash_test sinh ra ở commit chốt, không chép tay từ terminal.

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

### 3.2 Shape B — Single (Nguyễn Văn Minh)

Code: `src/lab8/shapes/single.py`. Một agent duy nhất chạy vòng ReAct tối đa 8 bước. Mỗi bước MockLLM chỉ chọn tool đọc tiếp theo (xem ticket, `lookup_order`, `compute_compensation`); hành động `propose` cuối cùng không mang số tiền. Code lấy quote từ output của tool rồi gọi `durability.issue_refund` với quote đầy đủ. Prompt có `SYSTEM_RULES` 7 luật gửi lại ở mọi bước (giống API thật), ticket chỉ nằm ở bước 1 trong thẻ `untrusted` nên thẻ đóng giả trong ticket không thoát được khối dữ liệu; prompt không bao giờ ghi vào trace. Đường đi dài nhất chỉ 3 bước ReAct. Ranh giới code/model: model chọn bước đọc, tiền do `compute_compensation`, approval và ledger do host. Kết quả: student test 62/62, 35 boundary test pass, benchmark pass 1.000, pass^5 1.000, var 0, cost/success 44.33, steps 4.79.

### 3.3 Shape C — Orchestrator (Đoàn Đăng Khoa)

Code: `src/lab8/shapes/orchestrator.py`. Orchestrator đọc claim qua view 4 cột (không `SELECT *`), dựng handoff bằng `make_handoff` với `facts={}` và 4 tool chỉ đọc cho các investigator, chạy `run_readonly_investigators`: mỗi investigator nhận handoff đã sanitize, trả văn bản, orchestrator tổng hợp rồi quote từ `compute_compensation` trên order row. Orchestrator là bên duy nhất gọi `durability.issue_refund` với quote đầy đủ và `crash_at`. `InjectedCrash` được ghi trace rồi ném lại; exception khác trả `failed`. Handoff đi qua allowlist (`ALLOWED_FIELDS`, `FACT_KEYS`) nên không mang `parent_secret`, header hay PII; payload `handoff.v1` ghi trong trace để kiểm chứng. Kết quả: student test 62/62, 37 boundary test pass, benchmark pass 1.000, pass^5 1.000, var 0, cost/success 57.19, steps 5.36.

### 3.4 Cổng host chung và QA (Lê Quốc Khánh, Vũ Đình Thắng)

Host giữ hai chốt không ai bỏ qua được: `policy.authorize` (approval phải thuộc đúng claim, còn hạn, valid, số tiền dương; hoàn bị cap theo approval, theo số đã trả của đơn và theo tổng đã hoàn trên cùng đơn) và `durability.issue_refund` (mỗi claim một dòng ledger nhờ idempotency `refund:{claim_id}`, dòng refund và audit `refund_committed` chung một transaction SQLite, tổng đơn được đọc lại bên trong transaction nên hai claim cùng đơn không thể cùng trả đủ). Khánh viết 45 test hồi quy (`tests/test_khanh_ledger_policy_crash.py`) chạy xuyên qua cả ba shape: approval hỏng không ghi tiền, crash ở 3 mốc rồi retry vẫn một refund, đổi quote sau commit ra `amount_conflict`, cap theo đơn giữa các claim. Thắng viết 130 test bảo mật (`tests/test_security_shapes.py`) bao cả prompt injection, rò rỉ secret/PII trên kết quả, trace và stdout/stderr, handoff allowlist; bộ test này đã được kiểm chứng trên swarm (bắt đúng điểm yếu seed 55) và trên stub (130 fail) trước khi dùng chấm shape của nhóm.

...

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public, 14 claim × seed 11–55, cùng MockLLM, cùng tool, cùng giá (nguồn `src/reports/benchmark.json`, sinh ở commit chốt):

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean steps |
| --- | --- | --- | --- | --- | --- | --- |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0 | 27.86 | 4.36 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0 | 44.33 | 4.79 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0 | 57.19 | 5.36 |
| swarm (reference) | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 |

Trial sai duy nhất của swarm là `C-002` seed 55: ticket khai trễ 5 ngày, order ghi 2 ngày, swarm tin ticket nên trả `resolved` thay vì `denied`.

Crash safety: `20/20` (`src/reports/crash.json`). Rò rỉ: quét 282 file trace trong `src/traces/` tìm `CANARY_SECRET`, `parent_secret`, `raw_headers`, `Bearer ` ra 0 file; 130 test bảo mật của Thắng quét thêm cả stdout/stderr và PII của mọi đơn, đều pass. Cổng host: 202 passed ngoài ma trận student; ma trận student đầy đủ: 378 passed (T01–T14 × 5 seed cho workflow, single, orchestrator, swarm + 130 test bảo mật). Chưa có kết quả tự kiểm trên `student_drop/` vì bộ hidden chưa được phát.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- Swarm sai ở seed 55 (C-002) do tin số ngày trong ticket. Nhóm không sửa swarm vì nó là reference có điểm yếu cố ý; thay vào đó dùng chính trial này làm dẫn chứng cho ranh giới ticket-là-dữ-liệu, và cả ba shape nhóm viết đều đọc ngày trễ từ order row nên không sai trial này ở seed nào.
- `lab8.crash_test` chỉ gọi thẳng `durability.issue_refund` chứ không gọi shape của nhóm, nên `20/20` chưa chứng minh shape truyền `crash_at` và không nuốt `InjectedCrash`. Nhóm bổ sung test crash ở cấp shape: 45 test hồi quy của Khánh và nhóm crash trong 130 test của Thắng.
- Bản đầu bộ test bảo mật có 45 test pass trên stub — stub không làm gì nên cũng không rò gì. Thắng thêm `_assert_handled` buộc shape phải xử lý claim thật; sau đó stub đỏ toàn bộ 130 test.
- Năm người cùng sửa `TEAM.md` và báo cáo gây conflict khi merge. Nhóm thống nhất khuôn khổ: mỗi người một file báo cáo cá nhân, phần chung chỉ thêm dòng của mình.
- Môi trường: venv không tự bật trong Git Bash và plugin `web3` xung đột làm pytest lỗi trên máy một thành viên; xử lý bằng cách kích hoạt venv thủ công và gỡ plugin khỏi môi trường chạy test.

...

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất và tất định theo seed, nên 5 seed chỉ phủ một phần hành vi; với model thật, rủi ro chính là model chọn sai tool, dừng sớm hoặc bị injection theo kiểu ngoài danh sách nhóm đã test. Latency là `unavailable` vì lab không đo. Kết luận "workflow rẻ nhất mà vẫn 1.000 pass" chỉ đúng trên corpus public 14 claim; nếu bộ hidden có claim cần tra cứu song song nhiều nguồn hoặc mục tiêu soạn văn bản trả lời khách, khoảng cách cost có thể thu hẹp và lời khuyên đổi shape xem điều kiện ở `decision_adr.md`. Chưa kiểm hai claim cùng đơn chạy đồng thời end-to-end (host đã có test riêng ở `test_order_cap_and_approval_binding.py`). Hướng cải thiện: chạy lại toàn bộ cổng trên `student_drop/` khi nhận bộ hidden, và thêm kịch bản injection theo các loại claim của bộ hidden.

## 8. Tài liệu tham khảo

- Google Research 2026, *Towards a Science of Scaling Agent Systems* — cơ sở cho phiếu R1 trong `research_card.md`.
- MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* — phân loại lỗi multi-agent (tham khảo R2).
- AgentArch, AACL 2026 — so sánh lựa chọn kiến trúc agent (tham khảo R3).
- EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* — confounder khi đánh giá multi-agent (tham khảo R4).
- Tài liệu lab: `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
