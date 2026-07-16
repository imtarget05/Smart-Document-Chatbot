# 📘 Hướng Dẫn Sử Dụng — Smart Document Chatbot

> Dành cho người dùng nghiệp vụ (Business Users) — không yêu cầu kiến thức lập trình

---

## 🎯 Giới Thiệu

**Smart Document Chatbot** giúp bạn hỏi đáp thông minh trên tài liệu của mình. Thay vì đọc hàng trăm trang PDF/Word để tìm thông tin, bạn chỉ cần upload tài liệu và đặt câu hỏi — AI sẽ trả lời kèm trích dẫn nguồn.

---

## 🚀 Bắt Đầu Nhanh (5 phút)

### Bước 1: Mở Ứng Dụng

1. Mở trình duyệt Chrome/Edge
2. Truy cập: **http://localhost:3000**
3. Đăng ký tài khoản mới hoặc đăng nhập

### Bước 2: Upload Tài Liệu

1. Click nút **"📄 Upload Document"** ở góc phải trên cùng
2. Chọn file (hỗ trợ: **PDF, DOCX, TXT**)
3. Đợi vài giây để hệ thống xử lý và index tài liệu
4. Tài liệu sẽ xuất hiện trong danh sách bên trái

### Bước 3: Đặt Câu Hỏi

1. Click vào tài liệu bạn muốn hỏi (hoặc chọn **Multi-File Mode** để hỏi nhiều tài liệu cùng lúc)
2. Gõ câu hỏi vào ô chat ở cuối màn hình
3. Nhấn Enter — AI sẽ trả lời **real-time**, hiển thị từng chữ một như đang gõ

```
┌─────────────────────────────────────────────────────┐
│  🔍 [Tìm kiếm tài liệu...]    [📄 Upload Document]  │
│                                                     │
│  📁 Tài liệu của tôi                                │
│  ┌─────────────────────────────────────────────────┐│
│  │ 📄 Báo cáo tài chính Q1.pdf                    ││
│  │ 📄 Hợp đồng mẫu.docx                           ││
│  │ 📄 Quy trình vận hành.txt                      ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │ 💬 **Bạn:** Lợi nhuận quý 1 là bao nhiêu?      ││
│  │                                                 ││
│  │ 🤖 **AI:** Theo báo cáo tài chính Q1,           ││
│  │ lợi nhuận sau thuế là **12.5 tỷ đồng**,         ││
│  │ tăng 15% so với cùng kỳ năm trước.               ││
│  │                                                 ││
│  │ 📎 [Báo cáo tài chính Q1.pdf - Trang 5]        ││  ← Citation
│  │                                                 ││
│  │ 📝 Nhập câu hỏi...                    [📤 Gửi]  ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Các Tính Năng Chính

### 1. Hỏi Đáp Thông Minh (RAG)

| Tính năng | Mô tả |
|-----------|-------|
| ✅ Trả lời dựa trên tài liệu | AI chỉ trả lời từ nội dung tài liệu bạn upload |
| ✅ Trích dẫn nguồn | Mỗi câu trả lời đều kèm nguồn (tên file + nội dung gốc) |
| ✅ Real-time streaming | Chữ hiện dần như người đang gõ |
| ✅ Multi-file chat | Hỏi trên nhiều tài liệu cùng lúc |

### 2. Tự Động Sửa Truy Vấn (CRAG)

Khi câu hỏi không tìm thấy thông tin trong tài liệu, hệ thống sẽ:
1. Tự động viết lại câu hỏi theo nhiều cách khác nhau
2. Tìm kiếm lại với các câu hỏi mới
3. Nếu vẫn không tìm thấy → tìm kiếm trên web (nếu được cấu hình)
4. Cuối cùng → dùng kiến thức nội bộ của AI

### 3. Bản Đồ Khái Niệm (Concept Map)

1. Sau khi upload tài liệu, AI tự động trích xuất các khái niệm chính
2. Click **"🗺️ Xem Concept Map"** để xem bản đồ tư duy trực quan
3. Click vào một khái niệm để hỏi chatbot sâu hơn về khái niệm đó

### 4. Lịch Sử Hội Thoại

- Tất cả câu hỏi và câu trả lời được lưu tự động
- Xem lại lịch sử bằng cách click vào session chat
- Xóa lịch sử khi không cần nữa

---

## 📖 Ví Dụ Câu Hỏi

### Với tài liệu "Báo cáo tài chính Q1.pdf"

| Câu hỏi | Kết quả |
|---------|---------|
| *"Doanh thu quý 1 là bao nhiêu?"* | ✅ Trả lời + trích dẫn |
| *"So sánh lợi nhuận với quý trước?"* | ✅ Trả lời + trích dẫn |
| *"Các rủi ro chính là gì?"* | ✅ Trả lời + trích dẫn |
| *"Ai là tác giả của báo cáo?"* | ✅ Trả lời từ metadata |

### Với nhiều tài liệu (Multi-File Mode)

| Câu hỏi | Kết quả |
|---------|---------|
| *"Tổng hợp các điểm chính từ 3 tài liệu này?"* | ✅ Tổng hợp chéo |
| *"Tìm điểm khác biệt giữa hợp đồng A và B?"* | ✅ So sánh |

---

## 🤔 Mẹo Sử Dụng Hiệu Quả

1. **Upload tài liệu chất lượng**: Tài liệu rõ ràng, không bị mờ (scan) sẽ cho kết quả tốt hơn
2. **Đặt câu hỏi cụ thể**: "Lợi nhuận Q1?" tốt hơn "Kể về công ty"
3. **Dùng Multi-File Mode**: Khi cần so sánh hoặc tổng hợp nhiều tài liệu
4. **Kiểm tra citation**: Luôn xem nguồn trích dẫn để kiểm chứng thông tin
5. **Xóa + tải lại**: Nếu tài liệu thay đổi, xóa cũ và upload lại

---

## 📱 Yêu Cầu Hệ Thống

| Yêu cầu | Tối thiểu | Khuyến nghị |
|---------|-----------|-------------|
| Trình duyệt | Chrome 90+, Edge 90+, Firefox 90+ | Chrome mới nhất |
| Kết nối | Internet (lần đầu) | 10 Mbps+ |
| RAM (server) | 8GB | 16GB |

---

## ❓ Câu Hỏi Thường Gặp

**Q: Có thể upload file bao nhiêu trang?**
A: Hỗ trợ tối đa 200 trang/file. Với tài liệu lớn hơn, nên chia nhỏ.

**Q: Dữ liệu có an toàn không?**
A: Có. Dữ liệu được lưu trên server nội bộ, AI chạy local (Ollama), không gửi lên cloud.

**Q: Có hỗ trợ tiếng Việt không?**
A: Có. Hỗ trợ cả tiếng Việt và tiếng Anh.

**Q: Làm sao để xóa tài liệu?**
A: Click icon 🗑️ bên cạnh tên tài liệu trong danh sách.

---

## 📞 Hỗ Trợ

- Báo cáo lỗi hoặc góp ý: Liên hệ qua email
- Tài liệu kỹ thuật: Xem `README.md` và `docs/API.md`