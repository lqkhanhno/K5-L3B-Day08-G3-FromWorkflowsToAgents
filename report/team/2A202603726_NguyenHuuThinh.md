# Báo cáo cá nhân — 2A202603726_NguyenHuuThinh

## 1. Thông tin thành viên

- Họ tên: Nguyễn Hữu Thịnh
- MSSV: 2A202603726
- Email: <!-- TODO: tự điền -->
- GitHub: <!-- TODO: tự điền username GitHub -->

## 2. Phần việc phụ trách

Người 1, Workflow (Core Developer). Phụ trách Shape A `workflow`:

- Viết `src/lab8/shapes/workflow.py`: quy trình xử lý claim tuần tự.
- Nối các phần policy (`compute_compensation`), tracking (`lookup_order`), compensation và approval (cổng host `durability.issue_refund`).
- Bảo đảm chỉ gọi refund khi đủ điều kiện, và chạy đủ 62 student test cho workflow.
- Viết báo cáo kiến trúc Workflow: `report/team/workflow_architecture.md`.

## 3. Đóng góp cụ thể

**Commit chính**

- `1484656` feat(workflow): implement shape A deterministic workflow + crash report. Gồm `src/lab8/shapes/workflow.py` và `src/reports/crash.json`. Branch `feat/workflow` trên repo nhóm.

**Test.** Không thêm test mới. Đã chạy và làm pass toàn bộ 62 student test của workflow trong `tests/test_public_matrix.py`:

- `test_public_single_run_cases[*-workflow-*]`: 12 claim (`C-001`..`C-010`, `C-013`, `C-014`) × 5 seed = 60 test
- `test_t11_retry_keeps_one_refund[workflow]`
- `test_t12_crash_before_checkpoint_does_not_double_pay[workflow]`

**Quyết định kỹ thuật**

1. **Truyền quote đầy đủ vào `issue_refund`**, không tự trừ phần đã hoàn. Host tự cap theo đơn, nhờ đó T14 (`C-014`) ghi đúng 120.000.
2. **Quote = 0 thì không gọi host. Quote > 0 thì luôn gọi host**, để host ghi audit `policy_denied` khi approval hỏng hoặc đơn đã hoàn đủ (`C-007`, `C-013`).
3. **Tính tiền từ order row, bỏ qua số ngày trong ticket.** Nhờ đó `C-002` ra `denied` ở cả 5 seed, kể cả seed 55 là seed mà swarm bị sai.
4. **Truyền `crash_at` và ném lại `InjectedCrash`** sau khi flush trace (T12).
5. **Một cửa ra `_done()`** cho mọi nhánh. Mọi lần return đều đi qua `finish()`, nên không có nhánh nào thiếu trace và không tự điền tay `refund_effects`.
6. **Trace chỉ ghi các field đã qua allowlist** (`claim_id`, `has_order_id`, order đã lọc, quote, kết quả của host). Không ghi ticket hay claim/order row thô.
7. **Không gọi MockLLM** (0 model call). Grader không chấm câu trả lời khách, nên bỏ bước draft giúp cost thấp nhất. Giới hạn này đã ghi trong báo cáo kiến trúc.

## 4. Bằng chứng

| Kiểm tra | Lệnh (chạy trong `src/`) | Kết quả |
| --- | --- | --- |
| Student test workflow | `python -m pytest -q -m student -o addopts= -k workflow` | 62 passed |
| Cổng host | `python -m pytest -q` | 54 passed |
| Crash suite | `python -m lab8.crash_test --count 20 --out reports/crash.json` | `crash_safety 20/20` |
| Quét secret | `grep -lE "CANARY_SECRET\|parent_secret" traces/R-workflow-*` | Không có file nào |
| Benchmark public | `python -m lab8.benchmark --shapes workflow,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark_workflow.json` | workflow: pass 1.000, pass^5 1.000, var 0, cost/success 27.86. swarm: pass 0.986, pass^5 0.929, cost/success 49.57 |

Một số run id: `R-workflow-C-002-s55` (denied, đúng nhãn, đúng ở seed mà swarm sai), `R-workflow-C-014-s11` (resolved, proposal 150.000, ledger 120.000), `R-workflow-C-013-s11` (denied, có `policy_denied`).

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Opus).** Dùng vào các việc:
  - Đọc repo và lập kế hoạch làm việc theo checkpoint.
  - Giải thích luật nghiệp vụ, contract, và lỗi cài đặt môi trường (venv không được bật trong Git Bash, plugin `web3` làm pytest bị lỗi).
  - Tạo khung `workflow.py` có TODO, rồi viết thân hàm `_run`.
  - Chạy test, crash suite, quét secret.
  - Giải thích output benchmark.
  - Viết nháp báo cáo kiến trúc và báo cáo cá nhân này.
- **Cách tự kiểm tra:** <!-- TODO: sửa cho đúng việc bạn đã làm thật, ví dụ: -->
  - Tự chạy lại các lệnh ở mục 4 trên máy mình và đối chiếu output.
  - Tự chạy benchmark và kiểm số trong báo cáo khớp với `src/reports/benchmark_workflow.json`.
  - Đọc lại từng nhánh trong `_run` và đối chiếu với bảng ở `docs/contracts.md` và `docs/business_rules.md`.
  - Mở một file trace `traces/R-workflow-*.json` để xem trace không chứa ticket hay PII.

## 6. Tự đánh giá

<!-- TODO: phần này bạn tự viết (RULES.md không cho dùng AI viết phần tự đánh giá). Gợi ý:
- Mức hoàn thành so với nhiệm vụ được giao.
- Điều bạn hiểu rõ nhất sau bài lab (ví dụ vì sao truyền quote đầy đủ, vì sao ticket là dữ liệu).
- Điều còn chưa chắc hoặc sẽ làm khác nếu làm lại.
-->
