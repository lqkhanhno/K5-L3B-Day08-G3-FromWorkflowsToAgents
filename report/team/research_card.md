# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Google Research 2026, "Towards a Science of Scaling Agent Systems" (slide 68–69, bằng chứng benchmark) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Thêm agent hoặc thêm bước chỉ cải thiện chất lượng khi phần việc thực sự song song; với workload tuần tự, pass rate không tăng trong khi cost tăng theo số lời gọi model |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết quả lấy trên benchmark và model của riêng nguồn; trong lab chỉ có MockLLM tất định theo seed nên nhóm chỉ kiểm được hướng thay đổi, không phải độ lớn thực trên model sản xuất |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Từ workflow (0 model call, 27.86) sang orchestrator (orchestrator + 3 investigator, 5.36 steps) cost/success tăng khoảng 2 lần, pass rate giữ 1.000; sang swarm thì pass^5 giảm vì có seed tin dữ liệu ghi trong ticket |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định MockLLM, `tools.manifest.v1.1.yaml`, corpus `data/public_claims.jsonl` (14 claim), seed 11–55, giá `config/pricing.yaml`, evaluator (nhãn expected + `trial_pass`). Biến duy nhất thay đổi: topology (workflow, single, orchestrator, swarm) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: swarm tin số ngày trễ ghi trong ticket ở seed chia hết cho 5 (C-002, seed 55) trả `resolved` thay vì `denied`. Đo bằng pass rate, pass^5, variance và cost/success |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` (chạy trong `src/`, tại commit `06ff940`)
- Run id / file report: `src/reports/benchmark.json`; trace dẫn chứng `src/traces/R-workflow-C-002-s55.json`, `src/traces/R-workflow-C-014-s11.json`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: Đúng. workflow pass 1.000, pass^5 1.000, var 0, cost/success 27.86; single 1.000 / 1.000 / 0 / 44.33; orchestrator 1.000 / 1.000 / 0 / 57.19; swarm 0.986 / 0.929 / 0.000816 / 49.57 với đúng 1 trial sai là C-002 seed 55. Thêm agent không tăng pass, cost/success tăng từ 1.6 (single) đến 2.1 (orchestrator) lần so với workflow, và chỉ swarm có variance khác 0 đúng như lỗi dự kiến.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
