# 🛍️ AI cho CSKH & Marketing — POC Demo

> 📅 Ngày: 16/07/2026
> 
> Mục đích: Chứng minh khả năng ứng dụng AI vào 2 business domain thực tế: **CSKH (Retail)** và **Marketing**

---

## 1. 🤖 CSKH Chatbot — Tư Vấn Sản Phẩm (Smart-Document-Chatbot)

### Mô tả
Agent tư vấn bán hàng cho thương hiệu giày thể thao **Smart Shoes Vietnam**, sử dụng product catalog JSON + LLM (local/cloud) để trả lời câu hỏi của khách hàng.

### Business Domain
**Retail / E-commerce** — Ngành bán lẻ giày dép

### Cách chạy
```bash
cd Smart-Document-Chatbot

# Test nhanh (Python)
python -c "
import asyncio
from agent.agents.cskh_agent import ask_cskh

async def test():
    response = await ask_cskh('Tôi muốn mua giày chạy bộ, giá dưới 1 triệu, có loại nào không?')
    print(response)

asyncio.run(test())
"
```

### Câu hỏi demo

| Câu hỏi | Loại | Kết quả mong đợi |
|---------|------|-----------------|
| *"Tôi muốn mua giày chạy bộ, giá dưới 1 triệu"* | Tư vấn sản phẩm | Gợi ý SmartPro Runner Lite (890,000đ) |
| *"Giày nào tốt nhất để tập gym?"* | Gợi ý | SmartGym Flex Pro (1,490,000đ) |
| *"Chính sách đổi trả thế nào?"* | Chính sách | 30 ngày, còn nguyên tem |
| *"Có màu trắng size 42 không?"* | Tồn kho | Kiểm tra và trả lời |
| *"So sánh giày RUN-001 và TRN-001"* | So sánh | So sánh tính năng, giá |
| *"Tôi muốn mua 2 đôi, có được free ship không?"* | CSKH | Miễn phí ship nếu >500k |

### Kiến trúc

```
User Query
    │
    ▼
CSKHAgent.run(state)
    │
    ├── Load Product Catalog (JSON)
    ├── Build System Prompt (products + policies context)
    ├── LLM.generate(system_prompt + user_query)
    │
    ▼
Response with product recommendations + policies
```

### File liên quan
- `agent/agents/cskh_agent.py` — Agent CSKH
- `data/products_catalog.json` — Danh mục sản phẩm (8 sản phẩm, 4 danh mục)

---

## 2. 📣 AI Marketing — Content Generator (Factory Data)

### Mô tả
Module tự động sinh nội dung marketing (Facebook post, email campaign, mô tả sản phẩm) sử dụng local LLM Qwen2.5.

### Business Domain
**Marketing / Content Creation** — Ngành tiếp thị nội dung số

### Cách chạy
```bash
# API
curl "http://localhost:8000/api/v1/marketing?product_name=Giày%20chạy%20bộ%20SmartPro%20X1&product_info=Giày%20cao%20cấp%2C%20đệm%20AirBoost"

# Python
cd "Factory Data Automation & AI Reporting Platform"
python -c "
from app.ai.marketing import generate_marketing_content
result = generate_marketing_content('Giày thể thao SmartPro X1', 'Giày chạy bộ cao cấp, đệm AirBoost')
print(result['facebook_post']['content'][:500])
print('---')
print(result['email']['subject'])
"
```

### Output mẫu (Facebook Post)
```
📢 **SIÊU PHẨM MỚI: SmartPro Runner X1 — Chinh Phục Mọi Đường Chạy!** 🏃‍♂️

Bạn đang tìm kiếm đôi giày chạy bộ hoàn hảo? SmartPro Runner X1 với công nghệ 
đệm AirBoost siêu nhẹ, giảm sốc 40% — chạy đường dài 42km không lo mỏi chân!

🔥 ĐẶC ĐIỂM NỔI BẬT:
• Upper lưới FlyKnit thoáng khí
• Đế cao su Continental chống trượt
• Chỉ nặng 220g — nhẹ như không!

🎉 GIÁ ĐẶC BIỆT: Chỉ 1,890,000đ (giá gốc 2,200,000đ)

👉 Đặt hàng ngay: 1900 1234

#SmartShoes #GiayChayBo #Sport #Fitness #ReviewGiay
```

### API Endpoint
```
GET /api/v1/marketing?product_name={name}&product_info={info}

Response: {
  "product_name": "...",
  "facebook_post": { "title": "...", "content": "...", "hashtags": [...], "cta": "..." },
  "email": { "subject": "...", "body": "...", "cta_button": "...", "signature": "..." },
  "product_description": { "name": "...", "short_description": "...", "features": [...], ... }
}
```

### File liên quan
- `app/ai/marketing.py` — Marketing Generator module
- `app/api/main.py` — API endpoint `/api/v1/marketing`

---

## 3. 📊 So sánh với JD Requirements

| JD Yêu cầu | Trước | Sau | Ghi chú |
|------------|-------|-----|---------|
| 1. Nghiên cứu ứng dụng AI vào HR/Marketing/Retail/CSKH | ❌ Chưa có | ✅ **CSKH (Retail)** + **Marketing (Content)** | 2 business domain mới |
| 3. Sử dụng ChatGPT/Copilot/GenAI tools | ⚠️ Web app | ✅ **README có AI Tools section** | Copilot, ChatGPT, Claude prompts |
| 6. Đánh giá hiệu quả AI — business metrics | ⚠️ Tech eval | ✅ **Business Impact docs** | 96-99% time savings |
| 7. Tài liệu hướng dẫn cho người dùng nghiệp vụ | ⚠️ README tech | ✅ **User Guide docs** | Business user-friendly |

### Gap còn lại (nice-to-have)
- [ ] Mobile app (PWA từ React frontend hiện tại)
- [ ] RF/XGBoost notebook demo
- [ ] Stakeholder interview docs