# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Hữu Thịnh | 2A202603726 | nht702812@gmail.com | huuthinh812 | Workflow (Core Developer), Shape A |
|   2 |        |      |       |        |         |
|   3 | Đoàn Đăng Khoa | 2A202603766 | 26ai.khoadd@vinuni.edu.vn | ddkhoa2605 | orchestrator + handoff (Shape C) |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Hữu Thịnh (2A202603726) | Workflow (Core Developer), Shape A | `1484656` feat(workflow): implement shape A deterministic workflow + crash report; `057ee06` test(workflow): add shape A boundary tests | Thêm `src/tests/test_workflow_boundary.py` (31 test: ticket là dữ liệu, chỉ gọi host khi quote > 0 với quote đầy đủ, trace không lộ ticket/secret/PII). Chạy pass 62 student test workflow |
| Đoàn Đăng Khoa (2A202603766) | orchestrator + handoff (Shape C) | `fa395d8` | `src/tests/test_orchestrator_boundary.py` (37 test: trace không lộ secret/PII, handoff allowlist chỉ đọc, ticket không ghi đè delay/injection, approval mượn/thiếu bị chặn, 3 điểm crash resume ra 1 refund, retry, T14 quote đầy đủ) |

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
