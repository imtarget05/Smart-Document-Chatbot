"""
CSKH Agent — AI Customer Service Agent for Product Consultation.

This agent demonstrates applying AI to a real business domain (Retail / Customer Service).
It uses a product catalog to answer customer inquiries about products,
provide recommendations, and handle pre-sales questions.

Business domain: Retail - Footwear e-commerce (Smart Shoes Vietnam)
"""

import json
import logging
import os
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import LLMFactory
from graph.state import AgentState

logger = logging.getLogger(__name__)

# Load product catalog
CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "products_catalog.json",
)

with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    PRODUCT_CATALOG = json.load(f)

# ---- System Prompt ----

SYSTEM_PROMPT = """Bạn là nhân viên CSKH chuyên nghiệp của Smart Shoes Vietnam — 
một thương hiệu giày thể thao hàng đầu Việt Nam.

NHIỆM VỤ:
- Tư vấn sản phẩm giày cho khách hàng
- Gợi ý sản phẩm phù hợp với nhu cầu
- Giải thích chính sách bảo hành, đổi trả, vận chuyển
- Hỗ trợ khách hàng chọn size, màu sắc

QUY TẮC:
1. Luôn tư vấn DỰA TRÊN danh mục sản phẩm có sẵn (không tự ý thêm sản phẩm không có)
2. Nếu khách hỏi sản phẩm không có trong danh mục, báo lịch sự và gợi ý sản phẩm tương tự
3. Khi gợi ý, nêu rõ TÊN SẢN PHẨM, GIÁ, ĐẶC ĐIỂM NỔI BẬT
4. Giọng văn thân thiện, chuyên nghiệp, xưng hô "em - anh/chị"
5. Nếu khách muốn mua, hướng dẫn liên hệ hotline 1900 1234
6. Giới thiệu chính sách: Miễn phí vận chuyển đơn >500k, đổi trả 30 ngày

DANH MỤC SẢN PHẨM (dùng để tra cứu):
{products_context}

CHÍNH SÁCH:
- Vận chuyển: {shipping_policy}
- Đổi trả: {return_policy}
- Bảo hành: {warranty_policy}
"""


class CSKHAgent:
    """AI Customer Service Agent for product consultation and recommendations."""

    def __init__(self):
        self._llm = LLMFactory.get_reasoning_model(temperature=0.5)
        self._catalog = PRODUCT_CATALOG

    def _build_context(self) -> Dict[str, str]:
        """Build product context for the system prompt."""
        products_text = ""
        for cat in self._catalog["categories"]:
            products_text += f"\n--- {cat['name']} ---\n"
            for p in self._catalog["products"]:
                if p["category"] == cat["id"]:
                    products_text += (
                        f"- {p['name']} ({p['id']}): {p['price']:,}đ "
                        f"(giá gốc {p['original_price']:,}đ) - {p['description']}\n"
                        f"  Đánh giá: {p['rating']}/5 ({p['reviews']} reviews)\n"
                        f"  Màu: {', '.join(p['colors'])}\n"
                        f"  Nổi bật: {'; '.join(p['features'][:2])}\n"
                    )

        pol = self._catalog["policies"]
        shipping = "; ".join(f"{k}: {v}" for k, v in pol["shipping"].items())
        return_policy = f"{pol['return']['days']} ngày - {pol['return']['condition']}"
        warranty = pol["warranty"]

        return {
            "products_context": products_text,
            "shipping_policy": shipping,
            "return_policy": return_policy,
            "warranty_policy": warranty,
        }

    async def run(self, state: AgentState) -> AgentState:
        """Run CSKH agent — consult, recommend, answer policy questions."""
        query = state["query"]
        ctx = self._build_context()
        system_prompt = SYSTEM_PROMPT.format(**ctx)

        logger.info("CSKH Agent: query=%s", query[:100])

        try:
            response = await self._llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=query),
                ]
            )
            answer = response.content.strip()
        except Exception as exc:
            logger.error("CSKH Agent error: %s", exc)
            answer = "Xin lỗi anh/chị, hiện tại em đang gặp sự cố kỹ thuật. Anh/chị vui lòng gọi hotline 1900 1234 để được hỗ trợ trực tiếp ạ."

        state["final_answer"] = answer
        state["sources"] = [
            {
                "source_type": "products_catalog",
                "document_name": "Smart Shoes Vietnam Product Catalog",
            }
        ]
        state["agent_type"] = "cskh"
        return state


# ---- Convenience function for direct usage ----


async def ask_cskh(query: str) -> str:
    """Ask the CSKH agent a question (for testing/API usage)."""
    from graph.state import AgentState

    agent = CSKHAgent()
    state = AgentState(query=query, session_id="cskh-test")
    result = await agent.run(state)
    return result["final_answer"]
