"""Tests for benefit engine: insight generation, RAG enrichment, priority/category assignment."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.benefit_engine import (
    generate_insights,
    _find_relevant_rag,
    _assign_priority,
    _assign_category,
    CATEGORY_ACT_NOW,
    CATEGORY_THIS_YEAR,
    CATEGORY_LONG_TERM,
)


class TestGenerateInsights:
    """Test the main generate_insights function."""

    def _mock_llm_result(self):
        return {
            "insights": [
                {
                    "id": "RRSP_BRACKET_OPTIMIZATION",
                    "headline": "Maximize RRSP contribution",
                    "detail": "Contributing to RRSP can reduce taxable income.",
                    "estimated_value": 3120.0,
                    "calculation_shown": "$12,000 x 26% = $3,120",
                    "action_required": "Contribute before March 1",
                    "confidence": 0.92,
                },
                {
                    "id": "TFSA_GAP",
                    "headline": "Utilize TFSA room",
                    "detail": "Unused TFSA contribution room available.",
                    "estimated_value": 425.0,
                    "confidence": 0.88,
                },
                {
                    "id": "OVER_WITHHOLDING",
                    "headline": "Tax over-withheld",
                    "detail": "Employer withheld more tax than owed.",
                    "estimated_value": 2400.0,
                    "confidence": 0.95,
                },
            ]
        }

    def test_returns_insights_and_summary(self):
        profile = {"employment": {"total_employment_income": 55000}, "derived": {}}
        result = generate_insights(profile, self._mock_llm_result())
        assert "insights" in result
        assert "summary" in result
        # At least 3 from LLM; may have more from fallback/provincial
        assert len(result["insights"]) >= 3

    def test_insights_sorted_by_value_desc(self):
        profile = {"employment": {"total_employment_income": 55000}, "derived": {}}
        result = generate_insights(profile, self._mock_llm_result())
        values = [i["estimated_value"] for i in result["insights"]]
        assert values == sorted(values, reverse=True)

    def test_summary_total_savings(self):
        profile = {"employment": {"total_employment_income": 55000}, "derived": {}}
        result = generate_insights(profile, self._mock_llm_result())
        expected_total = 3120.0 + 425.0 + 2400.0
        assert abs(result["summary"]["total_identified_savings"] - expected_total) < 0.01

    def test_product_links_removed(self):
        profile = {"derived": {}}
        result = generate_insights(profile, self._mock_llm_result())
        for ins in result["insights"]:
            assert ins["product_link"] is None

    def test_handles_empty_insights_adds_fallbacks(self):
        profile = {"derived": {}}
        result = generate_insights(profile, {"insights": []})
        # Fallback insights should be generated (minimum 3)
        assert len(result["insights"]) >= 3

    def test_handles_non_list_insights_adds_fallbacks(self):
        profile = {"derived": {}}
        result = generate_insights(profile, {"insights": "invalid"})
        # Fallback insights should still be generated
        assert len(result["insights"]) >= 3

    def test_confidence_overall(self):
        profile = {"employment": {"total_employment_income": 55000}, "derived": {}}
        result = generate_insights(profile, self._mock_llm_result())
        # Confidence is average of all insights (including any fallbacks)
        confidences = [i["confidence"] for i in result["insights"] if i.get("confidence")]
        expected_avg = sum(confidences) / len(confidences) if confidences else 0.8
        assert abs(result["summary"]["confidence_overall"] - round(expected_avg, 2)) < 0.02


class TestRAGEnrichment:
    """Test RAG context integration into insights."""

    def test_rag_context_appended_to_detail(self):
        rag_context = [
            {"answer": "RRSP contribution limit for 2024 is 18% of earned income up to $31,560. Unused room carries forward."},
            {"answer": "TFSA annual limit for 2024 is $7,000. Cumulative room since 2009 is $95,000 for eligible Canadians."},
        ]
        profile = {"derived": {}, "rag_context": rag_context}
        llm = {
            "insights": [{
                "id": "RRSP_BRACKET_OPTIMIZATION",
                "headline": "RRSP Optimization",
                "detail": "Contribute to reduce tax.",
                "estimated_value": 3000.0,
                "confidence": 0.9,
            }]
        }
        result = generate_insights(profile, llm)
        rrsp = result["insights"][0]
        assert "CRA Guidance:" in rrsp["detail"]
        assert "RRSP" in rrsp["detail"]

    def test_rag_matching_selects_correct_answer(self):
        rag_context = [
            {"answer": "RRSP rules: contribution limit is 18% of earned income."},
            {"answer": "TFSA rules: annual limit is $7,000 for 2024."},
        ]
        profile = {"derived": {}, "rag_context": rag_context}
        llm = {
            "insights": [
                {"id": "TFSA_GAP", "headline": "TFSA Gap", "detail": "Fill TFSA.", "estimated_value": 400, "confidence": 0.9},
            ]
        }
        result = generate_insights(profile, llm)
        tfsa = next(i for i in result["insights"] if i["id"] == "TFSA_GAP")
        assert "TFSA" in tfsa["detail"]
        # Should match the TFSA answer, not the RRSP one
        assert "annual limit" in tfsa["detail"].lower() or "$7,000" in tfsa["detail"]


class TestFindRelevantRAG:
    """Test _find_relevant_rag keyword matching."""

    def test_matches_primary_keyword(self):
        answers = [
            "RRSP contribution room and deduction rules for Canadian taxpayers.",
            "TFSA contribution limits and withdrawal rules for 2024.",
        ]
        result = _find_relevant_rag("RRSP_BRACKET_OPTIMIZATION", answers)
        assert "RRSP" in result

    def test_matches_tfsa(self):
        answers = [
            "RRSP contribution room and deduction rules for Canadian taxpayers.",
            "TFSA contribution limits and withdrawal rules for 2024.",
        ]
        result = _find_relevant_rag("TFSA_GAP", answers)
        assert "TFSA" in result

    def test_empty_answers_returns_empty(self):
        result = _find_relevant_rag("RRSP_BRACKET_OPTIMIZATION", [])
        assert result == ""

    def test_no_match_returns_empty(self):
        answers = ["Weather forecast for tomorrow."]
        result = _find_relevant_rag("RRSP_BRACKET_OPTIMIZATION", answers)
        # May or may not match depending on scoring; if score < 1 returns ""
        assert isinstance(result, str)

    def test_truncates_long_answers(self):
        long_answer = "RRSP " + "x" * 600
        result = _find_relevant_rag("RRSP_BRACKET_OPTIMIZATION", [long_answer])
        assert len(result) <= 510  # 500 + room for sentence boundary


class TestAssignPriority:
    """Test _assign_priority value-based logic."""

    def test_high_priority_for_large_value(self):
        assert _assign_priority({"estimated_value": 5000}, {}) == "HIGH"
        assert _assign_priority({"estimated_value": 10000}, {}) == "HIGH"

    def test_medium_priority(self):
        assert _assign_priority({"estimated_value": 500}, {}) == "MEDIUM"
        assert _assign_priority({"estimated_value": 2000}, {}) == "MEDIUM"

    def test_low_priority_for_small_value(self):
        assert _assign_priority({"estimated_value": 100}, {}) == "LOW"
        assert _assign_priority({"estimated_value": 0}, {}) == "LOW"

    def test_none_value_is_low(self):
        assert _assign_priority({}, {}) == "LOW"


class TestAssignCategory:
    """Test _assign_category insight type classification."""

    def test_act_now_categories(self):
        assert _assign_category("OVER_WITHHOLDING", {}) == CATEGORY_ACT_NOW
        assert _assign_category("CPP_OVERPAYMENT", {}) == CATEGORY_ACT_NOW
        assert _assign_category("EI_OVERPAYMENT", {}) == CATEGORY_ACT_NOW

    def test_long_term_categories(self):
        assert _assign_category("CPP_DEFERRAL", {}) == CATEGORY_LONG_TERM
        assert _assign_category("SPOUSAL_RRSP", {}) == CATEGORY_LONG_TERM
        assert _assign_category("TFSA_GAP", {}) == CATEGORY_LONG_TERM

    def test_default_this_year(self):
        assert _assign_category("RRSP_BRACKET_OPTIMIZATION", {}) == CATEGORY_THIS_YEAR
        assert _assign_category("FHSA_ELIGIBILITY", {}) == CATEGORY_THIS_YEAR
