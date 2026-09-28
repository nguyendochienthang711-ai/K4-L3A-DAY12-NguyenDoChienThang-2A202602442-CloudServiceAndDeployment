# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng `> *Câu trả lời của bạn*` bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Nguyễn Đỗ Chiến Thắng  Mã học viên: 2A202602442

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Giả sử ta đặt giá trị mặc định `agent_api_key = "changeme"`. Khi deploy lên môi trường Production (như Render hoặc Cloud Run), nếu người vận hành sơ suất quên cấu hình biến `AGENT_API_KEY` trong Environment Variables, ứng dụng vẫn sẽ khởi động thành công mà không phát ra bất kỳ cảnh báo nào. Khi đó, toàn bộ endpoint `/ask` sẽ chấp nhận khóa mặc định `"changeme"`. Bất kỳ kẻ tấn công hoặc bot nào trên Internet khi quét các endpoint phổ biến đều có thể dùng khóa này để gọi API trái phép, làm rò rỉ dữ liệu hoặc tiêu hao hết ngân sách LLM của hệ thống.
Ngược lại, khi không đặt giá trị mặc định, hệ thống áp dụng nguyên tắc **Fail Fast**: Pydantic lập tức ném lỗi `ValidationError` và làm ứng dụng crash ngay trong pha khởi động. Container không thể chuyển sang trạng thái sẵn sàng (ready), các hệ thống giám sát và triển khai sẽ lập tức báo động đỏ (Deployment Failed), giúp lập trình viên phát hiện và bổ sung biến môi trường ngay tức thì trước khi hệ thống mở cửa cho người dùng bên ngoài.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thực tế thu được từ service:
```json
{"timestamp": "2026-09-28T10:15:32.124500Z", "level": "INFO", "service": "day12-agent", "event": "ask_completed", "user_id": "sv-test", "tokens_in": 39, "tokens_out": 52, "cost_usd": 0.000037}
```

Hai việc làm được với dòng log JSON này mà `print("đã trả lời xong")` không thể làm được:
1. **Truy vấn và lọc theo trường dữ liệu (Structured Querying & Filtering)**: Các nền tảng quản lý log tập trung (như Datadog, Grafana Loki, ELK Stack, CloudWatch) có thể tự động phân tích (parse) cú pháp JSON để lập chỉ mục. Nhờ đó, kỹ sư vận hành có thể lọc chính xác mọi request của một người dùng cụ thể (`user_id == "sv-test"`), hoặc tìm tất cả các truy vấn có chi phí bất thường (`cost_usd > 0.001`), mà không cần phải viết biểu thức chính quy (regex) phức tạp và dễ gãy vỡ.
2. **Tổng hợp dữ liệu theo thời gian thực và tạo cảnh báo chi phí (Metrics Aggregation & Alerting)**: Có thể dễ dàng tính toán các đại lượng thống kê như tổng chi phí tích lũy theo giờ (`SUM(cost_usd)`), trung bình lượng token trả về (`AVG(tokens_out)`), hoặc vẽ biểu đồ lưu lượng theo từng người dùng. Khi chi phí vượt ngưỡng an toàn trong ngày, hệ thống giám sát sẽ tự động kích hoạt cảnh báo (alert) gửi về Slack/PagerDuty để can thiệp kịp thời.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | 1.02 GB |
| Multi-stage | 271 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng chênh lệch (~750 MB) bao gồm:
1. **Các công cụ biên dịch và gói phát triển (Build Tools & Development Headers)**: Giai đoạn builder cần cài đặt các gói như `gcc`, `g++`, `make`, `python3-dev`, thư viện C/C++ headers để biên dịch các package native của Python (như psutil, pydantic-core, cryptography). Các công cụ này chiếm hàng trăm MB nhưng hoàn toàn không cần thiết khi chạy ứng dụng (runtime).
2. **Bộ nhớ đệm của pip và file trung gian (Pip cache & intermediate artifacts)**: Trong quá trình `pip install`, pip lưu lại các file wheels đã tải và các file đối tượng trung gian (`.o`, `.c`) trong `~/.cache/pip`.
3. **Các tiện ích hệ điều hành thừa**: Bản single-stage mang theo toàn bộ file hệ thống của môi trường build, trong khi bản multi-stage bắt đầu một stage mới tinh từ `python:3.11-slim` và chỉ sao chép đúng thư mục `/install` (các thư viện đã build xong) và mã nguồn `/app`, loại bỏ hoàn toàn các phần dư thừa giúp image siêu gọn nhẹ và bảo mật hơn.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- **Với Dockerfile hiện tại (đã tối ưu thứ tự)**:
  - Khi sửa một ký tự trong `app/main.py`, tất cả các layer trước đó gồm: base image, cài đặt gói phụ thuộc hệ thống, `COPY requirements.txt .`, và `RUN pip install ...` đều được **dùng lại hoàn toàn từ cache (`CACHED`)** vì file `requirements.txt` không hề thay đổi checksum.
  - Chỉ có layer `COPY . /app` (sao chép mã nguồn) và các layer phía sau nó mới bị vô hiệu hóa cache và phải chạy lại. Nhờ đó, thời gian build lại chỉ mất khoảng 1 - 2 giây.
- **Nếu đặt `COPY . .` lên trước `RUN pip install`**:
  - Khi ta chỉnh sửa code trong `app/main.py`, checksum của toàn bộ thư mục bị thay đổi, dẫn đến layer `COPY . .` bị mất cache.
  - Do Docker áp dụng cơ chế cache tuần tự (layer sau phụ thuộc layer trước), layer `RUN pip install` nằm phía sau buộc phải chạy lại từ đầu. Docker sẽ phải kết nối mạng, tải xuống và cài đặt lại toàn bộ thư viện dependencies mỗi khi ta sửa bất kỳ dòng code nào, khiến thời gian build tăng vọt từ vài giây lên vài phút, gây lãng phí tài nguyên và làm chậm nghiêm trọng quy trình CI/CD.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

- **Chuỗi sự kiện leo quyền và chiếm quyền máy host (Container Escape to Host Compromise)**:
  1. Kẻ tấn công phát hiện một lỗ hổng trong code ứng dụng Python (ví dụ: lỗi Deserialization qua `pickle`, lỗi Command Injection, hoặc Directory Traversal cho phép ghi file tùy ý).
  2. Kẻ tấn công thực thi mã độc và mở được một shell bên trong container. Do container chạy dưới quyền mặc định là `root` (UID 0), kẻ tấn công sở hữu toàn quyền cao nhất trong container: có thể đọc/ghi toàn bộ hệ thống file, chỉnh sửa cấu hình mạng, hoặc cài đặt thêm các công cụ tấn công.
  3. Kẻ tấn công tìm cách thoát khỏi ranh giới container (Container Escape) bằng cách khai thác các thư mục chia sẻ bị cấu hình ẩu (như mount `/var/run/docker.sock` hoặc các volume nhạy cảm trên host), hoặc khai thác lỗ hổng trong Linux kernel (như Dirty COW, runc CVE-2019-5736, v.v.).
  4. Vì tiến trình bên trong container chạy với UID 0 và được ánh xạ trực tiếp tới UID 0 của máy host (khi không bật user namespace remap), một khi đã breakout thành công, kẻ tấn công sẽ có ngay quyền `root` tối cao trên hệ điều hành của máy chủ vật lý, kiểm soát toàn bộ server và dữ liệu của các dịch vụ khác.
- **Lệnh `USER appuser` cắt đứt chuỗi tấn công ở đâu**:
  - Lệnh này cắt đứt ngay tại **Bước 2**: Bằng việc chỉ định `USER appuser` (UID 10001 phi đặc quyền), tiến trình ứng dụng chỉ có quyền đọc và thực thi tối thiểu trong thư mục ứng dụng, không có quyền sudo. Kẻ tấn công nếu có khai thác được code cũng chỉ là một user bình thường: không thể ghi đè file hệ thống, không thể can thiệp vào các tiến trình khác, và không đủ quyền hạn để khai thác các API nhạy cảm của kernel hay Docker socket, ngăn chặn hoàn toàn khả năng thoát container để tấn công máy host.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

- **Số request tối đa có thể gửi trong 2 giây liên tiếp**: **20 requests**.
- **Giải thích cách đạt được (Vấn đề bùng nổ biên - Boundary Burst của thuật toán Fixed Window)**:
  - Thuật toán Fixed Window Counter (cửa sổ cố định) gom các request theo từng phút đồng hồ và reset bộ đếm về 0 khi kim giây chạm `00`.
  - Một người dùng có thể cố tình gửi dồn dập 10 request vào giây cuối cùng của phút trước (từ `12:00:59` đến `12:00:59.999`). Cả 10 request này đều được hệ thống chấp nhận vì trong phút `12:00` người này chưa vượt quá hạn mức 10 request.
  - Ngay ở tích tắc tiếp theo khi đồng hồ chuyển sang `12:01:00`, bộ đếm được làm mới hoàn toàn về 0. Người dùng lập tức gửi tiếp 10 request nữa trong giây `12:01:00`. Cả 10 request mới này lại tiếp tục được chấp nhận vì thuộc về chu kỳ phút `12:01`.
  - Hậu quả: Chỉ trong khoảng thời gian vỏn vẹn **2 giây** (từ `12:00:59` đến `12:01:00`), hệ thống đã phải tiếp nhận tới **20 requests**, gấp đôi ngưỡng chịu tải thiết kế (10 req/phút).
  - Sliding Window (cửa sổ trượt) dùng Redis Sorted Set giải quyết triệt để vấn đề này vì nó luôn tính tổng số request trong đúng khoảng thời gian trôi qua thực tế: `[thời điểm hiện tại - 60 giây, thời điểm hiện tại]`.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

- **Điểm khác nhau cốt lõi**:
  - **Rate Limiter (Bảo vệ thông lượng & tài nguyên hệ thống)**: Giám sát **tần suất cuộc gọi trong khoảng thời gian rất ngắn** (đơn vị: số request / phút hoặc giây). Mục đích là chống nghẽn CPU, cạn kiệt connection pool, và phòng ngừa tấn công từ chối dịch vụ (DoS/DDoS).
  - **Cost Guard (Bảo vệ tài chính & ngân sách tích lũy)**: Giám sát **tổng số tiền chi tiêu thực tế tích lũy** (đơn vị: USD / tháng). Mục đích là ngăn chặn rủi ro thâm hụt tài chính khi ứng dụng sử dụng các dịch vụ tính tiền theo lượng tiêu thụ của bên thứ ba (như token của OpenAI hay Google Gemini).
- **Tình huống Rate Limit cho qua nhưng Cost Guard phải chặn**:
  - Một người dùng cả tháng chỉ gửi đúng **1 request** duy nhất (tần suất cực kỳ thưa, hoàn toàn nằm trong hạn mức 10 req/phút của Rate Limiter). Tuy nhiên, trước đó tài khoản này đã tiêu hết 10.0 USD ngân sách của tháng. Khi request này đến, Cost Guard kiểm tra thấy số dư ngân sách không đủ nên lập tức chặn lại và trả về mã lỗi HTTP `402 Payment Required`.
- **Tình huống Cost Guard cho qua nhưng Rate Limit phải chặn**:
  - Một tài khoản mới đăng ký chưa tiêu đồng nào (ngân sách 10.0 USD còn nguyên). Người dùng này chạy một script tự động gửi liên tục **15 request trong vòng 2 giây**. Cost Guard kiểm tra thấy ngân sách còn rất nhiều nên đồng ý, nhưng Rate Limiter phát hiện tần suất gọi vượt quá ngưỡng an toàn 10 req/phút nên lập tức chặn từ request thứ 11 trở đi và trả về mã lỗi HTTP `429 Too Many Requests`.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

- **Thứ tự sự kiện sụp đổ dây chuyền (Cascading Failure)**:
  1. **Redis gặp sự cố hoặc nghẽn mạng tạm thời trong 30 giây**: Các kết nối từ ứng dụng tới Redis đều bị timeout hoặc từ chối kết nối.
  2. **Endpoint `/health` kiểm tra kết nối Redis và trả về HTTP 503**: Liveness probe của orchestrator (Kubernetes, Docker Swarm hoặc Render) định kỳ gọi vào `/health` để xem container còn sống không. Khi nhận HTTP 503, orchestrator kết luận rằng tiến trình container đã bị lỗi nghiêm trọng hoặc deadlock.
  3. **Orchestrator cưỡng chế restart (kill và khởi động lại) toàn bộ 3 container**: Cả cụm 3 container đang phục vụ người dùng đều bị hạ xuống đồng loạt.
  4. **Kẹt trong vòng lặp chết chóc (CrashLoopBackOff)**: Các container sau khi khởi động lại tiếp tục gọi `/health`. Lúc này Redis vẫn đang trong thời gian gián đoạn 30 giây chưa hồi phục, nên `/health` lại trả về 503. Orchestrator lại tiếp tục kill và restart chúng liên tục.
  5. **Toàn bộ hệ thống mất khả năng phục vụ (Complete Downtime)**: Ngay cả những request tĩnh, các trang tài liệu, giao diện web, hoặc các endpoint không cần đụng đến Redis cũng không thể truy cập được.
  - *Ý nghĩa tách biệt*: Nếu tách riêng, khi Redis chết chỉ có `/ready` trả 503 để load balancer tạm thời không chuyển traffic mới vào, trong khi `/health` vẫn trả 200 để container tiếp tục sống và kiên nhẫn chờ Redis hồi phục mà không bị restart vô cớ.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

- **Khi lưu trữ trên Redis (Kiến trúc Stateless)**:
  - Dù request được Load Balancer phân phối ngẫu nhiên (Round-Robin) tới bất kỳ container nào (`agent-1`, `agent-2` hay `agent-3`), `history_length` luôn tăng đều đặn và chính xác: `0 -> 2 -> 4 -> 6 -> 8...`. Vì mọi container đều đọc và ghi dữ liệu trạng thái hội thoại vào cùng một cơ sở dữ liệu Redis tập trung.
- **Nếu lưu trong một `dict` Python trong RAM của từng container (Kiến trúc Stateful)**:
  - Giá trị `history_length` sẽ **tăng bất thường, nhảy lộn xộn hoặc liên tục bị reset về 0** qua các lần gọi tiếp theo.
  - Ví dụ minh họa:
    - Lần 1: Request vào `agent-1` $\rightarrow$ `history_length` = 0 (lưu vào RAM của agent-1).
    - Lần 2: Request được điều phối sang `agent-2` $\rightarrow$ `history_length` vẫn là 0 (vì RAM của agent-2 hoàn toàn chưa có thông tin gì về người dùng này!).
    - Lần 3: Request quay lại `agent-1` $\rightarrow$ `history_length` là 2.
    - Lần 4: Request được điều phối sang `agent-3` $\rightarrow$ `history_length` lại quay về 0.
  - Hậu quả: Ứng dụng bị "mất trí nhớ", trợ lý AI không thể nắm bắt ngữ cảnh câu hỏi trước đó của người dùng khi hệ thống mở rộng đa instance (horizontal scaling).

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- **Thông báo lỗi gặp phải**:
  - Khi chạy kiểm thử tự động `pytest tests/test_cp5.py`, bài test `test_ask_hoat_dong_voi_key_that` trả về lỗi HTTP `401 Unauthorized` kèm thông báo `{"detail": "invalid or missing API key"}` khi gọi vào endpoint `/ask` trên Render.
- **Cách tìm ra nguyên nhân**:
  - Mở xem log trực tiếp trên Render Dashboard và đọc kỹ file test `tests/test_cp5.py`.
  - Nhận thấy rằng bài test trên cloud đòi hỏi một biến môi trường bí mật thực tế `DEPLOY_API_KEY` (khóa có độ phức tạp cao, khác với khóa mock ở local `AGENT_API_KEY=khoa-bi-mat-cua-agent-123`). Trên dashboard của Render, biến `AGENT_API_KEY` đã được cấu hình với chuỗi bảo mật thật này, nhưng trong file `.env` ở máy phát triển lúc đầu chưa định nghĩa biến `DEPLOY_API_KEY` tương ứng, dẫn đến header `X-API-Key` gửi lên không khớp với cấu hình của server trên cloud.
- **Cách khắc phục**:
  - Khai báo bổ sung biến `DEPLOY_API_KEY` vào file `.env` ở local với giá trị trùng khớp với khóa bảo mật đã cấu hình trên Render.
  - Phân tách rõ ràng nguyên tắc 12-Factor App: `AGENT_API_KEY` dành cho môi trường local/test nội bộ, còn `DEPLOY_API_KEY` là bí mật môi trường Production.
  - Sau khi lưu file `.env`, chạy lại `pytest tests/test_cp5.py` và lệnh curl xác thực, toàn bộ request đều được Render chấp nhận với mã HTTP `200 OK` và trả về kết quả chính xác.
