# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: fb60113
- Run id dẫn chứng: R-workflow-C-014-s11, R-workflow-C-002-s55 (trong `src/traces/`)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0 (nguồn `src/reports/benchmark.json`, 14 claim x seed 11–55)
- Cost per success (mô phỏng, VND): 27.86 (nguồn `src/reports/benchmark.json`)
- Crash safety: 20/20 (`src/reports/crash.json`)
- Secret leak / approval bypass: không có. Quét 282 file trace trong `src/traces/` tìm `CANARY_SECRET`, `parent_secret`, `raw_headers`, `Bearer ` ra 0 file; 378 test student (gồm 130 test bảo mật `tests/test_security_shapes.py` quét cả stdout/stderr và PII của mọi đơn) đều pass.

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

So trên cùng corpus public 14 claim và cùng 5 seed, workflow là shape duy nhất đạt pass 1.000, pass^5 1.000, variance 0 và rẻ nhất (27.86 VND mô phỏng mỗi lần thành công). Ba shape còn lại cùng đạt pass 1.000 nhưng tốn hơn từ 1.6 đến 2.1 lần (single 44.33, orchestrator 57.19), còn swarm pass^5 chỉ 0.929 vì sai C-002 ở seed 55 khi tin số ngày trễ ghi trong ticket. Bài toán claims vốn tuần tự: đọc claim, đọc order, tính quote, gọi host. Thêm investigator hay thêm bước ReAct không mở được nhánh nào mới, chỉ thêm lời gọi model. Với workload như vậy, quy trình cố định vừa rẻ vừa ổn định hơn.

## Có đáng đổi lấy multi-agent không

Nhóm giữ workflow. Cùng điều kiện, multi-agent không mua được gì về độ đúng: pass bằng nhau ở mức tốt nhất, trong khi cost/success cao hơn và swarm còn có trial sai. Chỉ đổi nếu ba điều kiện sau xảy ra: (1) bộ hidden có claim bắt buộc tra cứu song song nhiều nguồn mà một luồng tuần tự xử lý không hết, (2) pass rate của workflow trên bộ hidden tụt xuống dưới multi-agent, (3) bài toán thêm mục tiêu mới (đàm phán, viết văn bản trả lời khách) cần model soạn thảo. Khi đó single (44.33, vẫn 1.000 pass) là lựa chọn đổi đầu tiên, orchestrator chỉ đáng dùng khi investigator thực sự khai thác được dữ liệu mà luồng tuần tự bỏ sót.

## Trace và bằng chứng

Trace của nhóm ghi event `claim` (`claim_id`, `has_order_id`), `order` (đã qua allowlist của `lookup_order`), `quote`, `host` (`ok`, `reason`, `conflict`), `crash` (khi có inject) và `decision`. Cố ý không ghi: nội dung ticket, claim row thô (`parent_secret`, `raw_headers`), order row thô (SĐT, địa chỉ, tên hàng, ghi chú nội bộ), approval row và prompt gửi model. Lý do: ticket là dữ liệu không tin cậy được của khách, và các field còn lại là PII hoặc secret của principal.

Cách chứng minh hệ thống không lộ secret: (1) allowlist nằm trong host (`get_claim_view`, `lookup_order`), shape không có đường đọc trực tiếp DB; (2) quét tự động toàn bộ 282 trace trong `src/traces/` theo các chuỗi trên, kết quả 0 file; (3) bộ 130 test của Vũ Đình Thắng quét cả stdout/stderr và PII của mọi đơn trong world (không chỉ các chuỗi gắn với claim đang chạy) trên cả ba shape, gồm cả kịch bản prompt injection và claim có canary riêng chèn thêm vào DB tạm.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75.
