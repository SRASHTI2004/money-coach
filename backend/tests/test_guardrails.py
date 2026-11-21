import pytest

from app import coach, guardrails


@pytest.mark.parametrize("q", [
    "Which mutual fund should I buy?", "What is the best stock to invest in right now?",
    "Should I buy Reliance shares?", "suggest a good ETF for me", "which stocks to buy this month",
    "Which mutual fund should I put my money in?", "Is bitcoin a good buy, should I invest in it?",
    "Recommend an index fund scheme"])
def test_product_requests_blocked(q):
    assert guardrails.check_input(q) == guardrails.EDUCATIONAL_REPLY


@pytest.mark.parametrize("q", [
    "What if I cut dining out by 30%?", "What if my rent goes up by 3000?", "How big should my emergency fund be?",
    "Show my subscriptions", "Should I put my money toward my emergency fund first?", "What is a SIP?",
    "Why am I over budget on dining?"])
def test_normal_questions_pass(q):
    assert guardrails.check_input(q) is None


def test_output_filter_replaces_product_names():
    assert guardrails.sanitize_output("You could try Parag Parikh Flexi Cap.") == guardrails.EDUCATIONAL_REPLY
    assert guardrails.sanitize_output("Buy the HDFC Midcap Fund now") == guardrails.EDUCATIONAL_REPLY
    ok = "Index funds are a general category with low costs; risk varies."
    assert guardrails.sanitize_output(ok) == ok


def test_educational_reply_is_clean_and_disclaimer_present():
    assert not guardrails.output_violates(guardrails.EDUCATIONAL_REPLY)
    assert "SEBI" in guardrails.DISCLAIMER


def test_chat_blocks_and_never_calls_tools():
    r = coach.chat("t", "Which stock should I buy for the best returns?")
    assert r["guardrail"] and r["tools"] == [] and r["reply"] == guardrails.EDUCATIONAL_REPLY
