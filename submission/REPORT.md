# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Thùy Linh
- **MSSV:** 2A202602497
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/nalinh1102/K4-L3-DAY13-NguyenThuyLinh-2A202602497-Monitoring-LLMOps
- **Commit SHA dùng để chấm:** SHA của commit `feat: complete Day 13 monitoring and LLMOps submission` được push lên `origin/main` và nộp trên LMS/Codelabs
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602497`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Baseline CP0 | `evidence/00-cp0-baseline.txt` |
| Pytest cuối | [`evidence/01-pytest.png`](evidence/01-pytest.png), [`evidence/01-pytest.txt`](evidence/01-pytest.txt) |
| Log validator | [`evidence/02-log-validator.png`](evidence/02-log-validator.png), [`evidence/02-log-validator.txt`](evidence/02-log-validator.txt) |
| Dashboard validator | [`evidence/03-dashboard-validator.png`](evidence/03-dashboard-validator.png), [`evidence/03-dashboard-validator.txt`](evidence/03-dashboard-validator.txt) |
| Structured log | [`evidence/04-structured-log.png`](evidence/04-structured-log.png), [`evidence/04-structured-log.txt`](evidence/04-structured-log.txt) |
| PII redaction | [`evidence/05-pii-redaction.png`](evidence/05-pii-redaction.png), [`evidence/05-pii-redaction.txt`](evidence/05-pii-redaction.txt) |
| Trace list | [`evidence/06-trace-list.png`](evidence/06-trace-list.png), [`evidence/06-trace-list.txt`](evidence/06-trace-list.txt) |
| Trace waterfall | [`evidence/07-trace-waterfall.png`](evidence/07-trace-waterfall.png), [`evidence/07-trace-waterfall.txt`](evidence/07-trace-waterfall.txt) |
| Trace metadata | [`evidence/08a-trace-correlation-model.png`](evidence/08a-trace-correlation-model.png), [`evidence/08-trace-metadata.txt`](evidence/08-trace-metadata.txt) |
| Prompt versions | [`evidence/09-prompt-versions.png`](evidence/09-prompt-versions.png), [`evidence/09a-prompt-v2-candidate.png`](evidence/09a-prompt-v2-candidate.png) |
| Prompt rollback | [`evidence/10a-prompt-promote-v2.png`](evidence/10a-prompt-promote-v2.png), [`evidence/10b-prompt-rollback-v1.png`](evidence/10b-prompt-rollback-v1.png), [`evidence/10-prompt-rollback.txt`](evidence/10-prompt-rollback.txt) |
| Dashboard runtime | [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png), [`evidence/11-dashboard-overview.txt`](evidence/11-dashboard-overview.txt) |
| Incident metric | [`evidence/12-incident-metric.png`](evidence/12-incident-metric.png), [`evidence/12-incident-metric.txt`](evidence/12-incident-metric.txt) |
| Incident log | [`evidence/13-incident-log.png`](evidence/13-incident-log.png), [`evidence/13-incident-log.txt`](evidence/13-incident-log.txt) |
| Incident trace | [`evidence/14-incident-trace.png`](evidence/14-incident-trace.png), [`evidence/14-incident-trace.txt`](evidence/14-incident-trace.txt) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Không còn thiếu schema, context hoặc correlation ID |
| `validate_dashboard.py` | 6/6 | 6/6 | Dashboard runtime hoạt động tại `/dashboard` |
| `pytest` | 22 passed | 31 passed | Bổ sung test middleware, PII, tracing và dashboard runtime |
| Số traces hợp lệ | Chưa ghi nhận | 20 trace trees | Mỗi trace có root, retrieval và generation; xác nhận qua Observations API |
| Số PII leak | 0 | 0 | Runtime đã kiểm tra email, điện thoại, CCCD và thẻ thanh toán |
| Latency P95 / TTFT P95 | 1535ms / 50ms trước challenge | 2652ms / 50ms trong cửa sổ incident | P95 vượt ngưỡng challenge 2000ms; workload sau mitigation còn 151–152ms/request |
| Retrieval success rate | Chưa đo | 100% | Dashboard runtime, cửa sổ 60 phút |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ ở đầu mỗi request. Nếu header `x-request-id` đúng dạng `req-<8 ký tự hex>` thì giữ nguyên; nếu thiếu hoặc sai định dạng thì sinh ID mới từ UUID. ID được bind vào context, lưu trong `request.state`, trả lại qua response header và response body. Header `x-response-time-ms` ghi thời gian xử lý request.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, cùng timestamp, level, event, latency, TTFT, token, cost và quality khi có.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` duyệt đệ quy các chuỗi trong log và được đặt trước `JsonlFileProcessor`/JSON renderer. `user_id` không được lưu thô mà được băm SHA-256 và rút gọn còn 12 ký tự.
- **Cách kiểm chứng kết quả:** `validate_logs.py` đạt 100/100, không thiếu trường/context và không phát hiện PII. Test runtime xác nhận email, điện thoại Việt Nam, CCCD và thẻ thanh toán đều được thay bằng nhãn `[REDACTED_*]`. Xem `evidence/02-log-validator.png`, `evidence/04-structured-log.png` và `evidence/05-pii-redaction.png`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project cá nhân được cấu hình bằng key riêng trong `.env` (không commit). Langfuse Observations API xác nhận 20 trace trees hợp lệ; ảnh `evidence/06-trace-list.png` cho thấy project cá nhân và danh sách root observations, còn `evidence/06-trace-list.txt` lưu 10 trace ID kiểm chứng.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` có hai child observations: `retrieval` loại RETRIEVER ghi query preview đã scrub và số tài liệu; `generation` loại GENERATION ghi model, prompt managed, token, cost, TTFT cùng input/output preview đã scrub.
- **Cách nối trace với log:** `correlation_id` được truyền từ middleware vào metadata của root trace và xuất hiện trong structured log.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 — labels `baseline`, `production`
- **Version/label candidate:** v2 — label `candidate` (`latest` do Langfuse tự quản lý)
- **Trace ID của mỗi version:** baseline v1 `85c9a5fd24d8741d1e6cc2f1b652970f`; candidate v2 `6e3088356ed72cb03e97fc243f0c3f04`.
- **Cách promote và rollback `production`:** Chuyển `production` sang v2 và tạo trace `f975eedec46442a8294ea41b20f87431`; sau đó chuyển `production` về v1 và tạo trace `39683b7b20b9541559c20acac0309722`. Trạng thái cuối là `production → v1`.
- **Evidence rollback:** `evidence/10a-prompt-promote-v2.png` chụp trạng thái `production → v2`; `evidence/10b-prompt-rollback-v1.png` chụp trạng thái sau rollback `production → v1`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard runtime tại `/dashboard` đọc `data/logs.jsonl`, dùng cửa sổ 60 phút và tự refresh 30 giây. Sáu panel gồm Latency/TTFT, Traffic, Errors/Retrieval, Cost, Tokens và Quality; mỗi panel có đơn vị và threshold. Snapshot trước challenge có P95 1535ms, TTFT P95 50ms, error rate 0%, retrieval success 100%, cost $0.064521, 5147 token và quality 0.855.
- **SLO và lý do chọn:** 99.5% request trong 28 ngày phải có `response_sent` và latency không quá 3000ms. Ngưỡng này đo trực tiếp trải nghiệm người dùng và cho phép một phần nhỏ sai số để thay đổi hệ thống có kiểm soát.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`. Với 10,000 request trong 28 ngày, tối đa `10,000 × 0.5% = 50` request được phép lỗi hoặc chậm quá 3000ms.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (>3000ms trong 5m), `HighErrorRate` (>2% trong 5m), `LowRetrievalSuccess` (<90% trong 10m). Cả ba gửi Slack `#k4-l3b-alerts`, owner `student-2A202602497` và có hướng dẫn Metrics → Logs → Traces tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`, cohort K4, feature bị ảnh hưởng `monitoring`.
- **Khoảng thời gian điều tra:** 11:57:21–11:59:46 ngày 30/09/2026 (UTC+7). Workload sự cố chạy lúc 11:57:22–11:57:37; workload kiểm tra phục hồi chạy lúc 11:59:45–11:59:46.
- **Triệu chứng từ metrics:** Sau 5 request challenge, latency P95 của cửa sổ 60 phút tăng từ 1535ms lên 2652ms, vượt ngưỡng challenge 2000ms; P99 tăng từ 1997ms lên 4485ms. TTFT P95 vẫn 50ms, error rate vẫn 0% và retrieval success vẫn 100%, nên đây là sự cố chậm chứ không phải request lỗi.
- **Log line và correlation ID liên quan:** Log `response_sent` lúc `2026-09-30T04:57:26.967961Z` có `correlation_id=req-5b55ac49`, `feature=monitoring`, `latency_ms=4485`, `ttft_ms=50`, `tool_success=true` và `cost_usd=0.00135`.
- **Trace ID và span gây ảnh hưởng:** Trace `207b0a9724355ee340cf8603e63147a2` có root `lab-agent-run` 4.486s. Child `retrieval` (`91ff00d96f1e763b`) mất 2.501s, trong khi child `generation` (`88eb98919fafd916`) chỉ mất 0.151s và TTFT 0.049s.
- **Root cause:** Độ trễ được thêm tại tầng RAG retrieval khi incident `rag_slow` hoạt động. Metric cho thấy tail latency tăng, log chọn đúng request chậm và trace cùng correlation ID khoanh vùng `retrieval`, trong khi generation vẫn bình thường.
- **Fix action:** Tắt `rag_slow` bằng script điều khiển incident, xác nhận `/health` trả toàn bộ incident là `false`, rồi chạy lại đúng 5 request challenge. Log sau khôi phục còn 151–152ms/request, TTFT 50ms và tất cả đều thành công.
- **Preventive measure:** Thêm alert latency riêng cho feature `monitoring` ở ngưỡng 2000ms, giữ `correlation_id` xuyên metric/log/trace, theo dõi riêng span retrieval và áp dụng timeout/circuit breaker cùng cache hoặc fallback khi vector store chậm. Runbook phải yêu cầu xác nhận phục hồi bằng cùng workload sau mitigation.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Chỉ chấp nhận request ID đúng định dạng và sinh ID mới khi giá trị đầu vào không hợp lệ, giúp log/trace luôn có khóa theo dõi nhất quán. PII processor được áp dụng đệ quy và chạy trước bước ghi file để không phụ thuộc dữ liệu nhạy cảm nằm ở trường nào.
- **Một lỗi/blocker đã gặp:** VS Code tự tạo `.venv-1` bằng Python 3.14 nên `pydantic-core` cài đặt thất bại.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra `pyvenv.cfg`, chọn lại `.venv/Scripts/python.exe` dùng Python 3.11.9; sau đó `pip check` xác nhận dependency hợp lệ và toàn bộ test chạy thành công.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cho biết triệu chứng và khoảng thời gian; logs chọn đúng request bằng `correlation_id`; trace cùng ID cho biết bước con nào chậm hoặc lỗi; chỉ sau đó mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version cho biết chính xác chỉ dẫn nào tạo ra một câu trả lời; token/cost cho biết tác động tài nguyên; SLO định nghĩa mức dịch vụ chấp nhận được; rollback đưa hệ thống về prompt ổn định khi version mới làm latency, cost hoặc quality xấu đi.
- **Điều quan trọng nhất đã học:** Một kết luận vận hành phải nối được tín hiệu tổng quan với request cụ thể và từng bước xử lý, thay vì suy đoán từ một biểu đồ hoặc một trace ngẫu nhiên.
- **Hạn chế còn lại:** Dashboard dùng nguồn log JSONL cục bộ nên phù hợp cho lab và tái hiện sự cố, nhưng chưa có backend time-series/retention cho production. File challenge riêng được giữ ngoài Git theo yêu cầu.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit dùng để chấm.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh nộp không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
