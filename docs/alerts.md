# Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của event `response_sent`
- Điều kiện và thời gian duy trì: P95 lớn hơn 3000ms liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: người dùng phải chờ quá lâu trước khi nhận câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency, xác nhận P95/P99, TTFT và khoảng thời gian vượt ngưỡng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, chọn một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id`, so sánh span `retrieval` và `generation` để tìm bước chậm.
- Mitigation tạm thời: rollback prompt nếu generation/token tăng sau đổi version; nếu retrieval chậm thì khôi phục cấu hình retrieval hoặc giảm tải trong lúc điều tra.
- Owner: `student-2A202602497`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ `request_failed` trên tổng `request_received`.
- Điều kiện và thời gian duy trì: error rate lớn hơn 2% liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: nhiều người dùng không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors & Retrieval, xác nhận error rate và loại lỗi tăng nhiều nhất.
  2. Lọc event `request_failed`, lấy `correlation_id`, `error_type` và thời điểm xảy ra.
  3. Mở trace cùng ID để xem span thất bại và metadata prompt/model liên quan.
- Mitigation tạm thời: rollback thay đổi/prompt gần nhất nếu có tương quan thời gian; tắt incident practice hoặc khôi phục dependency lỗi.
- Owner: `student-2A202602497`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ thành công của tool `retrieval`.
- Điều kiện và thời gian duy trì: retrieval success thấp hơn 90% liên tục trong 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu context, sai hoặc chuyển sang fallback.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors & Retrieval, xác nhận tỷ lệ retrieval và khoảng thời gian giảm.
  2. Lọc các log có `tool_name=retrieval` và `tool_success=false`, lấy một `correlation_id`.
  3. Mở trace cùng ID, kiểm tra span `retrieval`, lỗi và thời gian thực thi.
- Mitigation tạm thời: tạm dùng fallback an toàn, khôi phục kết nối/index retrieval hoặc vô hiệu hóa scenario gây lỗi.
- Owner: `student-2A202602497`
