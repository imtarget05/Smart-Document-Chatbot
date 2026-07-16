# 📋 Phối Hợp Phòng Ban — Giả Lập Nhu Cầu & User Stories

> Mục đích: Minh họa quy trình phối hợp với các phòng ban để hiểu nhu cầu và đề xuất giải pháp AI phù hợp.

---

## 1. 🏭 Phòng Sản Xuất (Production)

### Interview
```
Interviewer: AI Intern
Interviewee: Anh Tuấn — Quản đốc phân xưởng
Date: 15/07/2026
```

**Q: Anh đang gặp khó khăn gì trong công việc hàng ngày?**

A: Mỗi sáng tôi phải tổng hợp báo cáo sản xuất từ 5 chuyền. Tôi copy số liệu từ Excel, tính OEE bằng tay, rồi viết email báo cáo cho giám đốc. Mất khoảng 2 tiếng mỗi ngày.

**Q: Anh mong muốn cải thiện điều gì?**

A: Tôi muốn số liệu tự động cập nhật, có cảnh báo khi OEE xuống thấp, và có thể xem dashboard mọi lúc mà không cần đợi báo cáo sáng.

**Q: Nếu có AI hỗ trợ, anh muốn nó làm gì?**

A: Tự động tính KPI, vẽ biểu đồ, và gợi ý nguyên nhân khi năng suất giảm. Đừng để tôi phải nhìn vào đống số liệu thô.

### User Stories
| ID | Với tư cách là | Tôi muốn | Để tôi có thể |
|----|---------------|---------|--------------|
| PROD-01 | Quản đốc | Xem OEE real-time theo chuyền | Phát hiện sớm vấn đề |
| PROD-02 | Quản đốc | Nhận cảnh báo khi reject rate > 5% | Xử lý kịp thời |
| PROD-03 | Quản đốc | Xem báo cáo AI tóm tắt cuối ca | Không cần viết báo cáo thủ công |

---

## 2. 💼 Phòng Kinh Doanh (Sales)

### Interview
```
Interviewer: AI Intern
Interviewee: Chị Mai — Trưởng phòng Kinh doanh
Date: 16/07/2026
```

**Q: Chị đang dùng công cụ gì để quản lý bán hàng?**

A: Tôi dùng Excel để theo dõi đơn hàng, Zalo để chat với khách, và email để gửi báo giá. Rất nhiều nơi, khó đồng bộ.

**Q: Khách hàng thường hỏi những gì?**

A: Hỏi về giá, size, màu sắc, và chính sách bảo hành. Nhân viên mới mất 2 tuần để thuộc hết danh mục sản phẩm.

**Q: Nếu có chatbot AI hỗ trợ, chị muốn nó làm gì?**

A: Tự động trả lời câu hỏi của khách về sản phẩm, gợi ý sản phẩm phù hợp, và nhắc lịch chăm sóc khách hàng.

### User Stories
| ID | Với tư cách là | Tôi muốn | Để tôi có thể |
|----|---------------|---------|--------------|
| SALE-01 | Nhân viên kinh doanh | Chatbot trả lời tự động câu hỏi về sản phẩm | Tiết kiệm thời gian tư vấn |
| SALE-02 | Trưởng phòng KD | AI gợi ý sản phẩm dựa trên nhu cầu khách | Tăng tỷ lệ chốt sale |
| SALE-03 | Nhân viên KD | Tra cứu nhanh chính sách giá, bảo hành | Trả lời khách ngay lập tức |

---

## 3. 🎯 Phòng Marketing

### Interview
```
Interviewer: AI Intern
Interviewee: Anh Hoàng — Content Marketing
Date: 16/07/2026
```

**Q: Một ngày làm việc của anh như thế nào?**

A: Sáng brainstorm ý tưởng, trưa viết bài, chiều chỉnh sửa. Mỗi ngày tôi phải ra 3-4 bài post cho Facebook, 1 email, và vài mô tả sản phẩm.

**Q: Anh thấy khó khăn nhất ở đâu?**

A: Viết content nhiều quá, bí ý tưởng. Nhất là khi có sản phẩm mới, phải nghĩ cách giới thiệu sao cho hấp dẫn.

**Q: Anh muốn AI giúp gì?**

A: Gợi ý ý tưởng bài viết, sinh draft content, và đề xuất hashtag. Tôi sẽ chỉnh sửa lại cho phù hợp, đỡ mất thời gian viết từ đầu.

### User Stories
| ID | Với tư cách là | Tôi muốn | Để tôi có thể |
|----|---------------|---------|--------------|
| MKT-01 | Content writer | AI sinh draft Facebook post từ thông tin sản phẩm | Tiết kiệm 70% thời gian viết |
| MKT-02 | Content writer | AI đề xuất email campaign | Không bị bí ý tưởng |
| MKT-03 | Marketer | AI tạo mô tả sản phẩm chuẩn SEO | Tăng hiển thị trên Google |

---

## 4. 📞 Phòng CSKH (Customer Service)

### Interview
```
Interviewer: AI Intern
Interviewee: Chị Lan — Nhân viên CSKH
Date: 16/07/2026
```

**Q: Một ngày chị nhận bao nhiêu cuộc gọi/tin nhắn?**

A: Khoảng 50-70. Hỏi đủ thứ: giá, size, địa chỉ shop, khiếu nại, đổi trả. Lặp đi lặp lại nhiều câu hỏi giống nhau.

**Q: Câu hỏi nào lặp lại nhiều nhất?**

A: "Shop ở đâu?", "Có size 42 không?", "Bao lâu giao hàng?", "Đổi trả thế nào?" — chiếm tới 60%.

**Q: Chị muốn AI hỗ trợ thế nào?**

A: Trả lời tự động các câu hỏi cơ bản, để tôi chỉ xử lý các vấn đề phức tạp hoặc khiếu nại.

### User Stories
| ID | Với tư cách là | Tôi muốn | Để tôi có thể |
|----|---------------|---------|--------------|
| CS-01 | Nhân viên CSKH | Chatbot trả lời tự động 60% câu hỏi phổ biến | Tập trung xử lý vấn đề phức tạp |
| CS-02 | Nhân viên CSKH | Tra cứu nhanh thông tin đơn hàng | Giảm thời gian chờ của khách |
| CS-03 | Quản lý CSKH | Dashboard thống kê câu hỏi phổ biến | Cải thiện quy trình |

---

## 5. 🏗️ Phòng Kỹ Thuật (Engineering / IT)

### Interview
```
Interviewer: AI Intern
Interviewee: Anh Khoa — IT Manager
Date: 16/07/2026
```

**Q: Hệ thống hiện tại có vấn đề gì?**

A: Tài liệu kỹ thuật nằm rải rác: một ít trong Confluence, một ít trong Google Drive, một ít trong email. Khi có nhân viên mới, mất 2-3 tuần để họ hiểu hệ thống.

**Q: Anh muốn AI giải quyết vấn đề gì?**

A: Một chatbot có thể trả lời câu hỏi về kiến trúc hệ thống, API endpoints, và quy trình vận hành. Tìm kiếm thông minh trên toàn bộ tài liệu kỹ thuật.

### User Stories
| ID | Với tư cách là | Tôi muốn | Để tôi có thể |
|----|---------------|---------|--------------|
| ENG-01 | Developer mới | Hỏi chatbot về kiến trúc hệ thống | Onboard nhanh hơn 80% |
| ENG-02 | IT Manager | AI tổng hợp tài liệu kỹ thuật | Dễ dàng cập nhật documentation |
| ENG-03 | DevOps | Tra cứu nhanh API endpoints | Giảm thời gian debug |

---

## 6. 📊 Tổng Hợp Requirements

### Priority Matrix

| Phòng ban | Pain level | AI Impact | Urgency | Priority |
|-----------|-----------|-----------|---------|----------|
| 🏭 Production | 🔴 Cao | 🟢 Cao | 🔴 Ngay | **1** |
| 📞 CSKH | 🔴 Cao | 🟢 Cao | 🟡 Tuần này | **2** |
| 💼 Sales | 🟡 Trung bình | 🟢 Cao | 🟡 Tuần này | **3** |
| 🏗️ Engineering | 🟡 Trung bình | 🟢 Cao | 🟢 Tháng này | **4** |
| 🎯 Marketing | 🟢 Thấp | 🟡 Trung bình | 🟢 Khi rảnh | **5** |

### Feature Roadmap (Đề xuất)

| Phase | Tính năng | Cho phòng ban | Thời gian |
|-------|----------|--------------|-----------|
| **Phase 1** | Dashboard tự động + Cảnh báo KPI | 🏭 Production | ✅ Đã xong |
| **Phase 2** | Chatbot CSKH tư vấn sản phẩm | 📞 CSKH, 💼 Sales | ✅ Đã POC |
| **Phase 3** | AI Content Generator | 🎯 Marketing | ✅ Đã POC |
| **Phase 4** | RAG Chatbot cho tài liệu kỹ thuật | 🏗️ Engineering | ✅ Đã xong |

---

## 📌 Kết Luận

Qua quá trình phỏng vấn giả định với 5 phòng ban, chúng tôi đã xác định được:
1. **6 pain points** chính có thể giải quyết bằng AI
2. **15 user stories** ưu tiên
3. **Lộ trình 4 phase** triển khai

File này minh họa khả năng phối hợp phòng ban, phân tích nhu cầu, và đề xuất giải pháp AI phù hợp — một kỹ năng quan trọng theo JD yêu cầu.