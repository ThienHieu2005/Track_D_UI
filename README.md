# TRACK D — WEB TỐI GIẢN (DEMO THỦ CÔNG)

Yêu cầu: Python 3.10+ và trình duyệt. Không cần Flask, npm, thư viện ngoài.

## Chạy nhanh trên 1 máy tính

Mở Terminal tại thư mục chứa `web_main.py`. **Khi chưa bật Node**, đặt lại dữ liệu nếu muốn:

```powershell
python reset_board.py
python reset_counter.py
```

Mở **4 Terminal riêng**, chạy mỗi lệnh trong một Terminal:

```powershell
python web_main.py --id 1
python web_main.py --id 2
python web_main.py --id 3
python web_main.py --id 4
```

Mở 4 tab trình duyệt: http://127.0.0.1:8001, http://127.0.0.1:8002, http://127.0.0.1:8003, http://127.0.0.1:8004.

**Demo đúng thứ tự:** Sinh viên 1 (chat/causal ordering) → Sinh viên 3 (xin CS, ghi whiteboard) → Sinh viên 2 (xem Leader, dừng Node 4 và quan sát bầu lại). Cần 4 Node còn chạy để thao tác Mutex thành công.

- **SV1:** Trên Node 1, tạo delay cho Node 3 khoảng 5 giây, sau đó gửi `A`. Chờ Node 2 nhận A rồi gửi `B` từ Node 2. Quan sát Node 3 giữ B trước khi hiển thị A rồi B.
- **SV3:** Trên Node 1 xin CS khoảng 8 giây; khi Node 1 đang trong CS, Node 2 xin CS và chờ. Sau đó ghi các ghi chú từ nhiều Node qua khung Shared File; xem chúng xuất hiện trong `shared_whiteboard.txt`.
- **SV2:** Kiểm tra Leader ban đầu là Node 4. Dừng tiến trình Node 4 bằng Ctrl+C ở Terminal 4, chờ hệ thống bầu lại Node 3. Chat có thể tiếp tục giữa các Node sống; CS/ghi file mới sẽ không hoàn thành do thiếu REPLY của Node 4.

## Cấu trúc

- `web_main.py`: khởi động từng Node có Web.
- `web/index.html`: giao diện HTML/CSS/JS.
- `app/peer_node.py`, `app/web_ui.py`, `app/shared_file.py`: tích hợp Node, HTTP và file chung.
- `modules/student1/`: Causal Multicast / Chat.
- `modules/student2/`: Heartbeat / Bully Election.
- `modules/student3/`: Ricart–Agrawala.
- `shared_whiteboard.txt`, `shared_counter.txt`: dữ liệu minh họa.
- `reset_board.py`, `reset_counter.py`: đặt lại dữ liệu trước buổi demo.

## Giới hạn

Đây là 4 tiến trình P2P TCP chạy trên cùng một máy qua localhost; file chung không được sao chép giữa máy khác nhau. Các thao tác đọc trên Web chỉ hiển thị dữ liệu, còn thao tác ghi yêu cầu quyền Mutex. Web chỉ bind 127.0.0.1 và không phù hợp public Internet. Khi một Node chết, thuật toán Mutex vẫn yêu cầu đủ REPLY theo danh sách 4 Node cố định.

Thư mục `tests/`, các log, tài liệu trùng lặp và `__pycache__/` **đã được loại bỏ để dễ demo**; thuật toán vẫn được giữ nguyên. Để kiểm thử tự động, sử dụng bản đầy đủ trước đó.
