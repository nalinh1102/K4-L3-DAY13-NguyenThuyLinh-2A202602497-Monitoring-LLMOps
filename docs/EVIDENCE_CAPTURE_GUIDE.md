# Hướng dẫn thu thập ảnh submission

Thư mục đích: `submission/evidence/`. Mỗi ảnh phải được tạo từ trạng thái
runtime thật trên commit sẽ nộp. Không chỉnh sửa ảnh theo cách làm thay đổi ý
nghĩa kết quả; luôn che secret hoặc PII nếu vô tình xuất hiện.

## 1. Chuẩn bị

Mở hai terminal tại root repository và kích hoạt đúng virtual environment.

```powershellw
Set-Location D:\VinUni\K4-L3-DAY13-NguyenThuyLinh-2A202602497-Monitoring-LLMOps
.\.venv\Scripts\Activate.ps1
```

Terminal 1 chạy API:

```powershell
uvicorn app.main:app --reload --env-file .env
```

Terminal 2 chạy workload, validator và các lệnh bên dưới. Trước khi thu thập
log cuối, xóa hoặc đổi tên log baseline để validator chỉ đọc log sau khi đã sửa:

```powershell
Remove-Item data\logs.jsonl -ErrorAction SilentlyContinue
python scripts\load_test.py
```

Không đưa `.env`, API key hoặc `config/challenge.json` vào ảnh hay Git.

## 2. Ảnh terminal và structured log

Chụp toàn bộ cửa sổ terminal, gồm lệnh vừa chạy và dòng kết quả cuối.

| File | Cách tạo | Điều bắt buộc thấy trong ảnh |
|---|---|---|
| `01-pytest.png` | `python -m pytest -q` | Lệnh và tổng số passed/failed. |
| `02-log-validator.png` | `python scripts\validate_logs.py` | Điểm cuối tối thiểu 80/100. |
| `03-dashboard-validator.png` | `python scripts\validate_dashboard.py` | Kết quả đủ 6/6. |
| `04-structured-log.png` | `Get-Content data\logs.jsonl -Tail 5` | JSON có timestamp, event, `correlation_id`, model, env, feature, latency. |
| `05-pii-redaction.png` | Gọi request có PII giả, sau đó xem log | Email, SĐT VN, CCCD và thẻ đã là `[REDACTED_*]`, không hiện dữ liệu thô. |
| `13-incident-log.png` | Lọc log sau workload incident | Một request bất thường có `correlation_id`, metric lỗi/chậm và timestamp. |

Ví dụ lọc log theo correlation ID đã chọn:

```powershell
Select-String -Path data\logs.jsonl -Pattern 'req-xxxxxxxx'
```

Thay `req-xxxxxxxx` bằng ID thực tế. Không dùng ID mẫu trong ảnh hay report.

## 3. Ảnh dashboard

Mở `http://127.0.0.1:8000/dashboard` sau khi đã có log từ workload.

| File | Thao tác | Điều bắt buộc thấy trong ảnh |
|---|---|---|
| `11-dashboard-overview.png` | Chụp toàn bộ dashboard; có thể tách `11a`, `11b` nếu không đọc rõ. | Cả 6 panel: Latency/TTFT, Traffic, Errors/Retrieval, Cost, Tokens, Quality; dữ liệu, time range, đơn vị và threshold/SLO line. |
| `12-incident-metric.png` | Sau challenge, chọn time range bao phủ đúng thời gian chạy challenge. | Metric bất thường (ví dụ P95/P99 latency), khoảng thời gian và giá trị quan sát được. |

Dashboard trống hoặc ảnh không nhìn thấy time range không hợp lệ. Ghi lại chính
xác time range trong `submission/REPORT.md`.

## 4. Ảnh Langfuse: traces và prompt

Đăng nhập Langfuse bằng project cá nhân `day13-k4-l3b-2A202602497`. Không mở
hoặc chụp trang **API Keys**. Trước khi chụp, tự chạy workload để sinh ít nhất
10 trace trong project này.

| File | Màn hình Langfuse cần mở | Điều bắt buộc thấy trong ảnh |
|---|---|---|
| `06-trace-list.png` | Trace list. | Tên project cá nhân và tối thiểu 10 traces do bạn tạo. |
| `07-trace-waterfall.png` | Một trace detail/waterfall. | Root observation, child `retrieval`, child `generation`, quan hệ cha-con và duration. |
| `08-trace-metadata.png` | Metadata của trace hoặc generation. | `correlation_id`, model, prompt name/version/label, token, cost; không PII thô. |
| `09-prompt-versions.png` | Prompt `day13-chat`. | Hai version v1/v2 và labels `baseline`, `candidate`, `production`. |
| `10-prompt-rollback.png` | Prompt labels/history, trước và sau rollback. | Bằng chứng `production` đã promote sang v2 và quay về v1; ghi trace ID hai version trong report. |
| `14-incident-trace.png` | Trace detail của request từ `13-incident-log.png`. | Cùng `correlation_id`, trace ID và span gây chậm/lỗi. |

Ảnh `14` phải nối được với `13`: so sánh trực tiếp `correlation_id` trước khi
chụp. Với incident latency, ảnh nên cho thấy duration của `retrieval` hoặc
`generation` lớn bất thường.

## 5. Chuỗi incident chính thức

Chỉ khi Lab Coach đã gửi file challenge riêng trong `config/challenge.json`:

```powershell
python scripts\inject_incident.py
python scripts\load_test.py --challenge --concurrency 5
```

Sau đó thực hiện theo thứ tự, không suy đoán nguyên nhân trước:

1. Dashboard: chụp `12-incident-metric.png`, xác định metric xấu và time range.
2. Logs: lọc log trong time range, chọn request bất thường, chụp `13-incident-log.png`.
3. Langfuse: tìm trace cùng `correlation_id`, chụp `14-incident-trace.png`.
4. Ghi challenge ID, time range, correlation ID, trace ID, span, root cause, fix và preventive measure vào report.

Không tự tạo, sửa, commit, push hoặc chia sẻ `config/challenge.json`. Nếu chưa
có challenge hợp lệ, chỉ thu thập evidence practice và để phần incident chờ
hướng dẫn của Lab Coach.

## 6. Hoàn tất report và kiểm tra

Đặt ảnh đúng tên trong `submission/evidence/`, rồi thay các link `.txt` tương
ứng trong `submission/REPORT.md`, ví dụ:

```markdown
![Trace waterfall](evidence/07-trace-waterfall.png)
```

Thực hiện kiểm tra cuối trên đúng commit sẽ nộp:

```powershell
python -m pytest -q
python scripts\validate_logs.py
python scripts\validate_dashboard.py
git status --short
git log -1 --oneline
```

Checklist:

- [ ] Ảnh `01` đến `14` đã có, hoặc `11a`/`11b` thay cho `11` khi cần.
- [ ] Mọi ảnh Langfuse là từ project cá nhân và không lộ key/secret.
- [ ] `12` → `13` → `14` cùng một incident qua time range và `correlation_id`.
- [ ] Mọi link ảnh trong report là đường dẫn tương đối, mở được trên GitHub.
- [ ] Report có commit SHA cuối trước khi push và nộp LMS/Codelabs.
