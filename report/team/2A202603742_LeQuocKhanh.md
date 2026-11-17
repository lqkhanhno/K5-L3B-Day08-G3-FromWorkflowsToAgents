# Báo cáo cá nhân — 2A202603742_LeQuocKhanh

## 1. Thông tin thành viên

- Họ tên: Lê Quốc Khánh
- MSSV: 2A202603742
- Email: <!-- TODO: tự điền -->
- GitHub: lqkhanhno

## 2. Phần việc phụ trách

Người 5 trong nhóm chia việc, phụ trách mảng ledger, policy và crash. Phần việc này không làm một shape riêng mà giữ các ranh giới phía host mà mọi shape đều phải đi qua:

- Cổng duyệt hoàn tiền trong `src/lab8/policy.py`: approval phải thuộc đúng claim mà nó trỏ tới, còn hạn, còn trạng thái valid, số tiền dương, và mức hoàn bị cap theo approval, theo số đã trả của đơn, và theo tổng đã hoàn trên cùng một đơn.
- Sổ hoàn tiền và checkpoint trong `src/lab8/durability.py`: mỗi claim ghi đúng một dòng vào `refund_ledger`, dòng này và audit `refund_committed` nằm trong cùng một transaction SQLite, retry sau crash không trả tiền hai lần.
- Crash suite `src/lab8/crash_test.py` và báo cáo `src/reports/crash.json`.

## 3. Đóng góp cụ thể

Viết bộ test hồi quy `src/tests/test_khanh_ledger_policy_crash.py` gồm 45 test case. Ý chính là không test cổng host một mình mà chạy qua cả ba shape đã giao (workflow, single, orchestrator), để chứng minh model hoặc shape không thể né được cổng. Ban đầu bộ test chỉ chạy workflow và orchestrator vì single chưa có người làm; khi shape B của Minh lên main mình đã đưa single vào và cả 45 test pass, tức là ba shape hành xử giống nhau sau cổng host. Bốn nhóm kịch bản:

1. Approval hỏng thì không được ghi tiền: thiếu approval, approval cấp cho claim khác, bị revoked, hết hạn, hoặc số tiền không dương. Shape phải trả denied với proposal vẫn bằng quote đầy đủ, `refund_ledger` không thêm dòng nào (kể cả các claim khác trong cùng database), có đúng một audit `policy_denied` mang đúng reason, và không có `refund_committed`.
2. Crash rồi retry (T12): crash ở ba mốc before_effect, after_effect_before_checkpoint, after_checkpoint, chạy trên C-001 và C-014. Sau khi retry xong, sổ chỉ có đúng một dòng với số đã được cap: C-001 còn 10000 vì approval chỉ cho 10000, C-014 còn 120000 vì đơn đã trả trước 30000. Idempotency key có dạng refund:kèm mã claim, checkpoint issue_refund chỉ có một bản, audit refund_committed chỉ có một bản.
3. Đổi quote sau khi đã commit: sửa shipping fee của đơn O-107 rồi chạy lại C-001, kết quả phải là failed với amount_conflict, số tiền đã commit giữ nguyên, không có dòng mới trong sổ.
4. Cap theo đơn giữa các claim: sau khi C-001 được hoàn, gán cho C-010 một approval hợp lệ của riêng nó rồi chạy, vẫn bị denied với order_already_refunded vì cùng đơn O-107 đã hết hạn mức.

Ngoài ra mình chạy lại crash suite và cập nhật `src/reports/crash.json`, kết quả 20/20.

Bộ test nằm ở nhánh lequockhanh (tên cũ codex/khanh-ledger-policy-crash), commit 3911f7d.

## 4. Bằng chứng

Các lệnh chạy trong thư mục src:

- `python -m pytest -q tests/test_khanh_ledger_policy_crash.py -o addopts=` cho 45 passed trên cả ba shape.
- `python -m lab8.crash_test --count 20 --out reports/crash.json` cho crash_safety 20/20, kết quả ghi trong src/reports/crash.json.
- `python -m pytest -q` cho 202 passed trên toàn bộ test ngoài ma trận student, tức là phần host và ba shape không bị bộ test mới làm hỏng gì.
- Ma trận student `python -m pytest -q -m student -o addopts=` cho 378 passed (sau khi 130 test bảo mật của Thắng cũng được tính vào ma trận), cả ba shape đều pass.
- Kiểm tra độ bắt lỗi của bộ test: tạm sửa `cap_per_order: true` thành `false` trong `src/config/autonomy_policy.yaml` rồi chạy lại `test_second_claim_cannot_refund_same_order_again` thì 3 test đỏ ngay trên cả ba shape; trả file về nguyên trạng thì 3 test xanh lại. Bộ test bắt được lỗi thật chứ không pass vô điều kiện.

## 5. Công cụ AI đã dùng

- ZCode (trợ lý AI chạy trên máy): pull nhánh của mọi người về, đọc code host trong policy.py và durability.py để nắm các mốc crash và các reason của cổng approval, viết bộ test hồi quy ở mục 3, chạy test, crash suite và benchmark, viết nháp báo cáo này và phần điền của nhóm trong TEAM.md, group_report.md, decision_adr.md, research_card.md.
- Cách tự kiểm tra:
  - Tự chạy lại các lệnh ở mục 4 trên máy mình và đối chiếu số liệu với báo cáo.
  - Đọc từng test trong file, đối chiếu với docstring của policy.py, durability.py và bảng luật nghiệp vụ trong docs/business_rules.md.
  - Tạm tắt `cap_per_order` trong `src/config/autonomy_policy.yaml` rồi chạy lại bộ test để thấy nó đỏ ngay (3 failed trên cả ba shape), sau đó trả file về nguyên trạng bằng `git checkout` và chạy lại cho xanh.

## 6. Tự đánh giá

<!-- TODO: phần này bạn tự viết (RULES.md không cho dùng AI viết phần tự đánh giá). Gợi ý:
- Mức hoàn thành so với nhiệm vụ được giao.
- Điều bạn hiểu rõ nhất sau bài lab (ví dụ vì sao truyền quote đầy đủ vào issue_refund, vì sao checkpoint không làm side effect thành exactly-once).
- Điều còn chưa chắc hoặc sẽ làm khác nếu làm lại.
-->
