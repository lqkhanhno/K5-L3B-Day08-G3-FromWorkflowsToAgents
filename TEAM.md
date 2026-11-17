# Team

## Thông tin nhóm

- Tên nhóm: G3
- Lớp: L3B
- Repo nhóm: `K5-L3B-Day08-G3-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/lqkhanhno/K5-L3B-Day08-G3-FromWorkflowsToAgents, nhánh `main`, commit chốt: fb60113

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Hữu Thịnh | 2A202603726 | 26ai.thinhnh2@vinuni.edu.vn | huuthinh812 | Workflow (Core Developer), Shape A |
|   2 | Lê Quốc Khánh | 2A202603742 | 26ai.khanhlq2@vinuni.edu.vn | lqkhanhno | ledger/policy/crash (cổng host) |
|   3 | Vũ Đình Thắng | 2A202603753 | 26ai.thangvd2@vinuni.edu.vn | ThangVu2303 | Durability & Security (QA độc lập) |
|   4 | Đoàn Đăng Khoa | 2A202603766 | 26ai.khoadd@vinuni.edu.vn | ddkhoa2605 | orchestrator + handoff (Shape C) |
|   5 | Nguyễn Văn Minh | 2A202603771 | 26ai.minhnv7@vinuni.edu.vn | vminh21 | Single ReAct Agent (Shape B) |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Hữu Thịnh (2A202603726) | Workflow (Core Developer), Shape A | `1484656` feat(workflow): implement shape A deterministic workflow + crash report; `057ee06` test(workflow): add shape A boundary tests | Thêm `src/tests/test_workflow_boundary.py` (31 test: ticket là dữ liệu, chỉ gọi host khi quote > 0 với quote đầy đủ, trace không lộ ticket/secret/PII). Chạy pass 62 student test workflow |
| Lê Quốc Khánh (2A202603742) | ledger/policy/crash (cổng host) | `3911f7d` test(ledger): add host boundary regression tests | `src/tests/test_khanh_ledger_policy_crash.py` (45 test chạy qua cả 3 shape: approval hỏng không ghi tiền, crash ở 3 mốc rồi retry không trả kép, đổi quote sau commit ra amount_conflict, cap theo đơn giữa các claim) |
| Vũ Đình Thắng (2A202603753) | Durability & Security (QA độc lập) | `c95242e` security | `src/tests/test_security_shapes.py` (130 test cho cả 3 shape: crash/resume, idempotency, approval hỏng, prompt injection, quét rò rỉ secret/PII cả stdout/stderr, handoff allowlist) |
| Đoàn Đăng Khoa (2A202603766) | orchestrator + handoff (Shape C) | `fa395d8` | `src/tests/test_orchestrator_boundary.py` (37 test: trace không lộ secret/PII, handoff allowlist chỉ đọc, ticket không ghi đè delay/injection, approval mượn/thiếu bị chặn, 3 điểm crash resume ra 1 refund, retry, T14 quote đầy đủ) |
| Nguyễn Văn Minh (2A202603771) | Single ReAct Agent (Shape B) | `05dd833` feat(single): implement shape B single ReAct agent with boundary tests | `src/tests/test_single_shape.py` (35 test: giới hạn bước ReAct, chống prompt injection trong ticket, trace không lộ secret/ticket, model không với được tool ghi) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-

## 2A202603726_NguyenHuuThinh

### Phần việc phụ trách

- Người 1, Workflow (Core Developer): Shape A `src/lab8/shapes/workflow.py`. Quy trình xử lý claim tuần tự, nối policy, tracking, compensation và approval qua cổng host `durability.issue_refund`.

### Đóng góp cụ thể

- Commit `1484656`: implement workflow (`src/lab8/shapes/workflow.py`). File `src/reports/crash.json` đã gỡ khỏi branch này và giao cho Người 4.
- Commit `057ee06`: thêm `src/tests/test_workflow_boundary.py` (31 test boundary cho workflow).
- Báo cáo kiến trúc Workflow (`report/team/workflow_architecture.md`) và báo cáo cá nhân (`report/team/2A202603726_NguyenHuuThinh.md`).

### Bằng chứng

- Student test workflow 62/62, test boundary 31/31, cổng host 85 passed, `crash_safety 20/20`, 0 trace lộ secret.
- Benchmark public workflow: pass 1.000, pass^5 1.000, var 0, cost/success 27.86 VND mô phỏng (swarm: 0.986, 0.929, 49.57).

## 2A202603766_DoanDangKhoa

Báo cáo đầy đủ: [report/team/2A202603766_DoanDangKhoa.md](report/team/2A202603766_DoanDangKhoa.md).

### Phần việc phụ trách

- Shape C — `orchestrator` (orchestrator + investigator chỉ đọc) và ranh giới handoff: `src/lab8/shapes/orchestrator.py`.
- Test: `src/tests/test_orchestrator_boundary.py`.
- Checkpoint: CP2 (62 test student), CP3 (handoff, idempotency, crash), CP4 (approval, secret, trace).

### Đóng góp cụ thể

- Commit `fa395d8` — `feat(orchestrator): implement shape C with read-only investigators`.
- Orchestrator đọc claim chỉ 4 cột (không `SELECT *`), dựng handoff bằng `make_handoff` với `facts={}` và 4 tool chỉ đọc, chạy `run_readonly_investigators`, quote từ `compute_compensation` trên order row, là bên duy nhất gọi `durability.issue_refund` với **quote đầy đủ** và `crash_at`.
- Ranh giới code / model: tiền, approval, idempotency do code; MockLLM chỉ lập kế hoạch và soạn chữ; delay ghi trong ticket không bao giờ được dùng.
- `InjectedCrash` được ghi trace rồi `raise` lại; exception khác trả `failed`, `run_claim` không ném lỗi.
- Trace cố ý không ghi: claim row (`parent_secret`, `raw_headers`), nội dung ticket, order row thô (`phone`, `address`, `internal_note`, `item_name`), approval row.
- Thêm 37 test ranh giới vào cổng host.

### Bằng chứng

- `python -m pytest -q -m student -o addopts= -k orchestrator` → `62 passed`.
- `python -m pytest -q` → `91 passed, 248 deselected` (gồm 37 test mới).
- Benchmark tự kiểm `--shapes orchestrator,swarm`, seed `11,22,33,44,55`: orchestrator pass 1.000, pass^5 1.000, cost/success 57.19, steps 5.36; swarm pass 0.986, pass^5 0.929.
- Crash rồi resume C-012 (`after_effect_before_checkpoint`): lần 2 `resolved`, `idempotent_replay`, ledger 1 dòng, trace `R-orchestrator-C-012-s11`.

## 2A202603742_LeQuocKhanh

Báo cáo đầy đủ: [report/team/2A202603742_LeQuocKhanh.md](report/team/2A202603742_LeQuocKhanh.md).

### Phần việc phụ trách

- Người 5, mảng ledger, policy và crash: giữ các ranh giới host mà mọi shape phải đi qua — cổng approval (`src/lab8/policy.py`), sổ hoàn tiền và checkpoint (`src/lab8/durability.py`), crash suite (`src/lab8/crash_test.py`).

### Đóng góp cụ thể

- Commit `3911f7d`: thêm `src/tests/test_khanh_ledger_policy_crash.py` — 45 test hồi quy chạy qua cả ba shape đã giao (workflow, single, orchestrator) để chứng minh shape/model không thể né cổng host.
- Chạy lại crash suite và cập nhật `src/reports/crash.json` (20/20).

### Bằng chứng

- `python -m pytest -q tests/test_khanh_ledger_policy_crash.py -o addopts=` → 45 passed.
- `python -m pytest -q` → 202 passed; ma trận student → 248 passed (cả ba shape).
- `python -m lab8.crash_test --count 20 --out reports/crash.json` → crash_safety 20/20.

## 2A202603753_VuDinhThang

Báo cáo đầy đủ: [report/team/2A202603753_VuDinhThang.md](report/team/2A202603753_VuDinhThang.md).

### Phần việc phụ trách

- Durability & Security, QA độc lập cho cả ba shape nhóm viết (không viết shape): bộ test bảo mật và độ bền `src/tests/test_security_shapes.py`, chạy crash suite 20 điểm, đọc kiểm các file host mà không sửa.

### Đóng góp cụ thể

- Commit `c95242e` (nhánh `vudinhthang`): thêm `src/tests/test_security_shapes.py` (130 test, marker student) và `src/reports/crash.json`.
- 130 test phủ: crash ở 3 điểm rồi resume, idempotency qua 5 seed, approval thu hồi/hết hạn/số tiền 0/mượn của claim khác, prompt injection (kể cả chữ `О` Cyrillic trong mã đơn), quét rò rỉ `CANARY_SECRET`/header/PII của mọi đơn trên cả kết quả, trace và stdout/stderr, handoff allowlist của orchestrator.
- Kiểm chứng chính bộ test: chạy trên swarm bắt đúng điểm yếu seed 55, chạy trên stub thấy 130 fail (không pass vô nghĩa) trước khi dùng để chấm shape của nhóm.

### Bằng chứng

- `python -m lab8.crash_test --count 20 --out reports/crash.json` → `crash_safety 20/20`.
- `python -m pytest -q -m student -o addopts= tests/test_security_shapes.py` → 130 passed trên cả ba shape đã merge.
- Cổng host `python -m pytest -q` luôn xanh sau mỗi lần thêm test.

## 2A202603771_NguyenVanMinh

Báo cáo đầy đủ: [report/team/2A202603771_NguyenVanMinh.md](report/team/2A202603771_NguyenVanMinh.md).

### Phần việc phụ trách

- Shape B `single` ReAct agent: `src/lab8/shapes/single.py` cùng bộ test `src/tests/test_single_shape.py` (35 test). Một agent duy nhất trong vòng ReAct tối đa 8 bước, model chỉ chọn bước đọc tiếp theo; tiền, approval, ghi ledger do code và host.

### Đóng góp cụ thể

- Commit `05dd833` (nhánh `2A202603771_NguyenVanMinh`): cài `single.py` và 35 test ranh giới.
- Prompt gửi MockLLM có `SYSTEM_RULES` (7 luật) ở mọi bước, ticket chỉ nằm ở bước 1 trong thẻ `untrusted`; prompt không bao giờ ghi vào trace.
- Truyền quote đầy đủ vào `durability.issue_refund`, truyền `crash_at` và không nuốt `InjectedCrash`.

### Bằng chứng

- Student test single 62/62; `python -m lab8.check_submission` OK shape single.
- Benchmark (src/reports/benchmark.json, 14 claim × seed 11–55): single pass 1.000, pass^5 1.000, var 0, cost/success 44.33, steps 4.79.
