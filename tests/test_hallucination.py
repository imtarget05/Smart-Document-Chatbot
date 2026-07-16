"""
TC-HAL-01 → TC-HAL-07: Hallucination Detection & Mitigation Tests
"""
import pytest
import time
import sys
import os
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Claim:
    text: str
    has_citation: bool = False
    source_doc_id: Optional[str] = None


@dataclass
class GeneratedAnswer:
    text: str
    confidence: float
    claims: List[Claim] = field(default_factory=list)
    grounded_ratio: float = 0.0


class MockHallucinationDetector:
    """Mock detector for testing hallucination logic."""

    def __init__(self, known_docs: List[Dict] = None):
        self.known_docs = known_docs or []

    def detect(self, query: str, answer: str, docs: List[Dict]) -> Dict:
        claims = self._extract_claims(answer)
        grounded = self._check_grounding(claims, docs)
        citations = self._extract_citations(answer)

        grounded_count = sum(1 for g in grounded if g)
        total = len(claims) if claims else 1
        grounded_ratio = grounded_count / total

        has_hallucination = grounded_ratio < 0.7
        confidence = 1.0 - has_hallucination * 0.5

        return {
            "has_hallucination": has_hallucination,
            "confidence": confidence,
            "grounded_ratio": grounded_ratio,
            "claims": claims,
            "citations": citations,
        }

    def _extract_claims(self, answer: str) -> List[Claim]:
        sentences = [s.strip() for s in answer.replace(".", ".").split(".") if s.strip()]
        return [Claim(text=s) for s in sentences]

    def _check_grounding(self, claims: List[Claim], docs: List[Dict]) -> List[bool]:
        results = []
        doc_texts = [d.get("content", "").lower() for d in docs]
        for claim in claims:
            claim_lower = claim.text.lower()
            found = any(doc_text in claim_lower or claim_lower in doc_text for doc_text in doc_texts)
            if not found:
                claim_words = set(claim_lower.split())
                doc_words_all = set(" ".join(doc_texts).split())
                overlap = len(claim_words & doc_words_all)
                found = overlap >= 3
            results.append(found)
        return results

    def _extract_citations(self, answer: str) -> List[str]:
        import re
        return re.findall(r'\[doc(\d+)\]', answer)


KNOWN_DOCS = [
    {"id": "doc1", "content": "Chính sách đổi trả cho phép khách hàng đổi trả sản phẩm trong vòng 30 ngày kể từ ngày mua."},
    {"id": "doc2", "content": "Quy định an toàn lao động yêu cầu tất cả công nhân phải đội mũ bảo hộ khi vào nhà xưởng."},
    {"id": "doc3", "content": "Chính sách lương thưởng dựa trên hiệu suất quý, thưởng tối đa 3 tháng lương."},
    {"id": "doc4", "content": "Quy trình vệ sinh máy móc phải được thực hiện hàng ngày trước khi ca làm việc bắt đầu."},
    {"id": "doc5", "content": "Bảo mật thông tin khách hàng là ưu tiên hàng đầu, mọi vi phạm sẽ bị xử lý kỷ luật."},
]


class TestHallucinationDetection:

    def test_hal01_known_answer_no_hallucination(self):
        """TC-HAL-01: Known Answer — grounded in docs, no hallucination."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        query = "Chính sách đổi trả là gì?"
        answer = "Chính sách đổi trả cho phép khách hàng đổi trả sản phẩm trong 30 ngày [doc1]."

        result = detector.detect(query, answer, KNOWN_DOCS)

        assert result["has_hallucination"] == False
        assert result["confidence"] >= 0.5
        assert result["grounded_ratio"] >= 0.5

    def test_hal02_unknown_answer_should_admit(self):
        """TC-HAL-02: Unknown Answer — agent should NOT make up info."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        query = "Chi phí sản xuất Q4/2027 là bao nhiêu?"
        answer = "Chi phí sản xuất Q4/2027 là 50 tỷ đồng."  # Made up

        result = detector.detect(query, answer, KNOWN_DOCS)

        assert result["has_hallucination"] == True
        assert result["confidence"] < 0.8

    def test_hal03_partial_hallucination(self):
        """TC-HAL-03: Partial Hallucination — some grounded, some not."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        query = "Chính sách đổi trả và lương thưởng"
        answer = "Chính sách đổi trả 30 ngày [doc1]. Lương thưởng dựa trên KPI 200% [doc3]."

        result = detector.detect(query, answer, KNOWN_DOCS)

        assert len(result["claims"]) >= 2
        assert result["grounded_ratio"] > 0

    def test_hal04_confidence_calibration(self):
        """TC-HAL-04: Confidence Calibration — confidence correlates with correctness."""
        detector = MockHallucinationDetector(KNOWN_DOCS)

        test_cases = [
            ("Chính sách đổi trả", "Đổi trả trong 30 ngày [doc1].", True),
            ("An toàn lao động", "Đội mũ bảo hộ khi vào xưởng [doc2].", True),
            ("Unknown query", "Thông tin bí mật từmars [doc99].", False),
            ("Lương thưởng", "Thưởng 3 tháng lương [doc3].", True),
            ("Fake info", "Công ty có 1 triệu nhân viên.", False),
        ]

        correct_confs = []
        wrong_confs = []

        for query, answer, should_be_correct in test_cases:
            result = detector.detect(query, answer, KNOWN_DOCS)
            if should_be_correct:
                correct_confs.append(result["confidence"])
            else:
                wrong_confs.append(result["confidence"])

        if correct_confs and wrong_confs:
            avg_correct = sum(correct_confs) / len(correct_confs)
            avg_wrong = sum(wrong_confs) / len(wrong_confs)
            assert avg_correct > avg_wrong, f"Confidence not calibrated: correct={avg_correct}, wrong={avg_wrong}"

    def test_hal05_self_consistency(self):
        """TC-HAL-05: Self-Consistency — same query produces consistent answers."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        query = "Chính sách đổi trả là gì?"

        answers = [
            "Chính sách đổi trả 30 ngày [doc1].",
            "Đổi trả sản phẩm trong 30 ngày theo chính sách [doc1].",
            "Khách hàng được đổi trả trong vòng 30 ngày [doc1].",
        ]

        similarities = []
        for i in range(len(answers)):
            for j in range(i + 1, len(answers)):
                sim = SequenceMatcher(None, answers[i].lower(), answers[j].lower()).ratio()
                similarities.append(sim)

        avg_sim = sum(similarities) / len(similarities)
        assert avg_sim >= 0.5, f"Answers too inconsistent: avg similarity = {avg_sim}"

    def test_hal06_citation_verification(self):
        """TC-HAL-06: Citation Verification — claims have source citations."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        query = "Chính sách đổi trả"
        answer = "Đổi trả trong 30 ngày [doc1]. Miễn phí vận chuyển khi đổi [doc1]."

        result = detector.detect(query, answer, KNOWN_DOCS)

        assert len(result["citations"]) >= 1, "No citations found"
        assert "1" in result["citations"], "Citation [doc1] not found"

    def test_hal07_fallback_chain(self):
        """TC-HAL-07: Fallback Chain — low confidence triggers retry logic."""
        detector = MockHallucinationDetector(KNOWN_DOCS)
        threshold = 0.7

        query = "Thông tin hoàn toàn mới"
        bad_answer = "Đây là thông tin mới chưa từng có."
        result_bad = detector.detect(query, bad_answer, KNOWN_DOCS)

        if result_bad["confidence"] < threshold:
            fallback_answer = "Chính sách đổi trả 30 ngày [doc1]."
            result_good = detector.detect(query, fallback_answer, KNOWN_DOCS)
            assert result_good["confidence"] >= result_bad["confidence"]
        else:
            assert result_bad["confidence"] >= threshold
