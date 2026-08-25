"""Offline deterministic tests for the eval.py grader (Decision 10).

Run:  cd <repo-root> && python3 -m pytest tests/test_grader.py -q
      (or: python3 -m unittest tests.test_grader -v)

No network, no LLM, no production access.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "eval"))

from eval import (  # noqa: E402
    evaluate_answer,
    grade_concepts,
    is_provider_error,
    load_concepts_overrides,
    normalize_text,
    resolve_concepts,
)


def make_result(answer, strategy="direct", confidence="medium", sources="evidence text"):
    return {
        "answer": answer,
        "status": "success",
        "latency_ms": 100,
        "confidence": confidence,
        "confidence_score": 0.8,
        "rag_strategy": strategy,
        "source_chunks": sources,
    }


LEGACY_Q = {
    "id": "legacy-001",
    "expected_answer_contains": ["Paris", "capital"],
    "expected_source_keywords": ["paris"],
}

CONCEPTS = [
    {
        "concept": "compares failure causes",
        "forms": ["similarities", "failure causes", "root cause"],
    },
    {
        "concept": "compares mitigation actions",
        "forms": ["differences", "mitigation actions", "corrective action"],
    },
]

CONCEPT_Q = {
    "id": "agent-003",
    "expected_answer_contains": ["similarities", "differences"],
    "expected_source_keywords": ["failure"],
}


class TestNormalizeText(unittest.TestCase):
    def test_lowercase_and_whitespace(self):
        self.assertEqual(normalize_text("  Hello   World  "), "hello world")

    def test_plural_normalization(self):
        self.assertEqual(normalize_text("risks"), "risk")
        self.assertEqual(normalize_text("causes"), "cause")
        self.assertEqual(normalize_text("actions"), "action")
        self.assertEqual(normalize_text("differences"), "difference")

    def test_ies_normalization(self):
        self.assertEqual(normalize_text("similarities"), "similarity")

    def test_punctuation_stripped(self):
        self.assertIn("failure causes", normalize_text("**Failure Causes:**"))

    def test_no_stemming_overreach(self):
        # words ending in ss/us/is must not lose their final s
        self.assertEqual(normalize_text("analysis"), "analysis")
        self.assertEqual(normalize_text("status"), "status")


class TestLegacyGrading(unittest.TestCase):
    def test_exact_keyword_pass(self):
        ev = evaluate_answer(make_result("The capital is Paris."), LEGACY_Q, {})
        self.assertTrue(ev["answer_correct"])

    def test_no_keyword_fail(self):
        ev = evaluate_answer(make_result("Completely unrelated."), LEGACY_Q, {})
        self.assertFalse(ev["answer_correct"])

    def test_empty_answer_fail(self):
        ev = evaluate_answer(make_result(""), LEGACY_Q, {})
        self.assertFalse(ev["answer_correct"])

    def test_legacy_mode_unchanged_when_no_concepts(self):
        ev = evaluate_answer(make_result("paris"), LEGACY_Q, {})
        self.assertNotIn("grading_mode", ev)
        self.assertIn("keywords_found", ev)

    def test_or_logic_preserved(self):
        # legacy: >=1 keyword is enough
        ev = evaluate_answer(make_result("the capital city"), LEGACY_Q, {})
        self.assertTrue(ev["answer_correct"])


class TestConceptGrading(unittest.TestCase):
    def test_exact_keyword_answer_pass(self):
        ans = "Similarities: both had root cause. Differences: corrective action varied."
        g = grade_concepts(ans, CONCEPTS)
        self.assertTrue(g["answer_correct"])
        self.assertEqual(g["concepts_covered"], 2)

    def test_correct_paraphrase_pass(self):
        # THE Decision-9 false negative: different headings, same meaning
        ans = "**Failure Causes:** process gap vs driver defect.\n**Mitigation Actions:** audit and retraining."
        ev = evaluate_answer(
            make_result(ans), CONCEPT_Q,
            {"agent-003": {"expected_concepts": CONCEPTS}},
        )
        self.assertTrue(ev["answer_correct"])
        self.assertEqual(ev["grading_mode"], "structured_concepts")

    def test_one_concept_only_fail(self):
        ans = "The failure causes were a process gap."
        g = grade_concepts(ans, CONCEPTS)
        self.assertFalse(g["answer_correct"])
        self.assertEqual(g["concepts_covered"], 1)

    def test_keyword_without_concept_fail(self):
        # mentions "differences" but never addresses the mitigation concept
        ans = "There are differences between the documents."
        g = grade_concepts(ans, CONCEPTS)
        self.assertFalse(g["answer_correct"])
        self.assertEqual(g["concepts_covered"], 1)

    def test_negation_limitation_documented(self):
        # KNOWN LIMITATION: deterministic matcher cannot detect negation.
        # "there are no differences" matches surface form "difference".
        # Documented honestly — grader is concept coverage, not semantics.
        ans = "there are no differences between them, and no root cause was found"
        g = grade_concepts(ans, CONCEPTS)
        self.assertTrue(g["answer_correct"])  # false positive by design limitation

    def test_empty_answer_fail(self):
        g = grade_concepts("", CONCEPTS)
        self.assertFalse(g["answer_correct"])
        self.assertEqual(g["concepts_covered"], 0)

    def test_concept_details_reported(self):
        g = grade_concepts("failure causes and mitigation actions", CONCEPTS)
        names = [d["concept"] for d in g["concept_details"]]
        self.assertEqual(names, ["compares failure causes", "compares mitigation actions"])
        self.assertTrue(all(d["covered"] for d in g["concept_details"]))

    def test_plural_forms_in_answer(self):
        ans = "Both root causes differ; the corrective actions taken were similar."
        g = grade_concepts(ans, CONCEPTS)
        self.assertTrue(g["answer_correct"])


class TestProviderErrorClassification(unittest.TestCase):
    """Decision 10.7 — HTTP 200 with a provider failure must NEVER count as success."""

    def test_genuine_answer_not_provider_error(self):
        r = make_result("The Eiffel Tower is in Paris, France.", strategy="direct")
        self.assertFalse(is_provider_error(r))
        ev = evaluate_answer(r, LEGACY_Q, {})
        self.assertFalse(ev["provider_error"])
        self.assertTrue(ev["answer_correct"])

    def test_temporarily_unavailable_is_provider_error(self):
        r = make_result(
            "Sorry, the language model is temporarily unavailable. Please try again.",
            strategy="no_evidence",
        )
        self.assertTrue(is_provider_error(r))
        ev = evaluate_answer(r, LEGACY_Q, {})
        self.assertTrue(ev["provider_error"])
        # answer_correct must NOT collapse to False solely because provider failed.
        self.assertIsNone(ev["answer_correct"])

    def test_cloudflare_error_is_provider_error(self):
        r = make_result("cloudflare_error:HTTPStatusError")
        self.assertTrue(is_provider_error(r))

    def test_provider_error_never_flags_hallucination(self):
        r = make_result(
            "Sorry, the language model is temporarily unavailable. Please try again.",
            strategy="direct", confidence="high",
        )
        ev = evaluate_answer(r, LEGACY_Q, {})
        self.assertTrue(ev["provider_error"])
        self.assertFalse(ev["is_hallucination"])

    def test_genuine_answer_with_error_words_not_provider_error(self):
        # Words like "unavailable"/"error" alone must NOT trigger the contract.
        r = make_result("No failure was reported; the system error logs were empty.")
        self.assertFalse(is_provider_error(r))
        ev = evaluate_answer(r, LEGACY_Q, {})
        self.assertFalse(ev["provider_error"])

    def test_http_errors_preserved_as_error_status(self):
        # ask_question() maps non-200 to status="error"; grader must keep that.
        r = {
            "status": "error",
            "http_status": 401,
            "latency_ms": 50,
            "answer": "",
            "source_chunks": "",
            "confidence": None,
            "confidence_score": None,
        }
        self.assertFalse(is_provider_error(r))
        ev = evaluate_answer(r, LEGACY_Q, {})
        self.assertEqual(ev["status"], "error")
        self.assertFalse(ev["provider_error"])


class TestProviderErrorMetrics(unittest.TestCase):
    """Opt-in summary-level checks that provider errors are excluded from grading."""

    @staticmethod
    def _run(details):
        questions = LEGACY_Q
        summary = {
            "total_questions": len(details),
            "details": details,
        }
        return summary

    def test_summary_denominator_uses_genuine_only(self):
        # Genuine + provider error: answer correctness denominator must be 1, not 2.
        genuine = evaluate_answer(make_result("the capital is Paris", "direct"), LEGACY_Q, {})
        provider = evaluate_answer(
            make_result("language model is temporarily unavailable", "no_evidence"),
            LEGACY_Q, {},
        )
        details = [genuine, provider]
        successful = [d for d in details if d["status"] == "success" and not d.get("provider_error")]
        provider_errors = [d for d in details if d.get("provider_error")]
        self.assertEqual(len(successful), 1)
        self.assertEqual(len(provider_errors), 1)
        correct = [d for d in successful if d["answer_correct"]]
        # answer correctness uses genuine-only denominator -> 1/1
        self.assertEqual(len(correct) / max(len(successful), 1), 1.0)

    def test_provider_error_excluded_from_retrieval_and_hallucination(self):
        provider = evaluate_answer(
            make_result("language model temporarily unavailable", "no_evidence", "high"),
            LEGACY_Q, {},
        )
        self.assertTrue(provider["provider_error"])
        self.assertFalse(provider["retrieval_accurate"])
        self.assertFalse(provider["is_hallucination"])

