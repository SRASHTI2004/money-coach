"""Guardrails enforced in code (in addition to the system prompt): the coach educates and models scenarios,
but never recommends specific securities, funds, or stocks."""
import re

DISCLAIMER = ("Educational information and scenario modelling only - not investment, tax or legal advice. "
              "This coach never recommends specific stocks, funds, or securities. Consider a SEBI-registered "
              "investment adviser for personalised advice.")

# Asking for / acting on a specific product pick.
_PRODUCT_WORDS = r"\b(stocks?|shares?|equit(?:y|ies)|mutual funds?|etfs?|index funds?|nifty|sensex|crypto(?:currency)?|" \
                 r"bitcoin|btc|ethereum|ipo|smallcase|bonds?|nfo|schemes?|securit(?:y|ies)|ticker|penny stocks?|gold etf|sgb|reit)\b"
_ASK = re.compile(
    r"(?is)\b(?:which|what|best|top|good|better|recommend|suggest|pick|name|tell me|should i|can i|where (?:to|should i)|"
    r"any)\b.{0,60}?\b(?:buy|invest|put (?:my )?money|park|purchase|sip|hold|sell|choose|go for|add)\b.{0,80}?"
    + _PRODUCT_WORDS +
    r"|(?:which|what|best|top|good|recommend|suggest)\b.{0,30}?\b" + _PRODUCT_WORDS +
    r"\b.{0,30}?\b(?:to|should|for|now|this|today|buy|invest|sip)\b"
    r"|\b(?:recommend|suggest|pick|name)\b.{0,40}?" + _PRODUCT_WORDS)
_NAMED = re.compile(r"(?i)\b(reliance|tcs|infosys|hdfc(?: bank)?|icici|sbi|adani|tata motors|zomato|paytm|itc|wipro|"
                    r"axis bluechip|parag parikh|quant|nippon|mirae|sbi small cap|bitcoin|ethereum|dogecoin|nifty ?bees|"
                    r"hdfc index|uti nifty|motilal|ppfas)\b")
_BUY_VERB = re.compile(r"(?i)\b(buy|sell|invest|sip|put money|hold|should i)\b")

EDUCATIONAL_REPLY = (
    "I can't recommend specific stocks, funds or other securities - that depends on your risk tolerance, time horizon "
    "and taxes, and picking products isn't something a budgeting coach should do. What I can do is explain how to "
    "think about it:\n\n"
    "- **Order of priorities:** a starter emergency fund (3-6 months of essentials) and clearing high-interest debt "
    "usually come before taking market risk.\n"
    "- **Risk vs. return:** equity-linked products can swing sharply in the short term; debt products are steadier but "
    "can lag inflation. Money you need within ~3 years generally shouldn't sit in volatile assets.\n"
    "- **Diversification & cost:** spreading across asset classes lowers the impact of any one bet, and fees compound "
    "just like returns do.\n"
    "- **Regular investing (SIPs)** is a *method* of investing a fixed amount periodically - it smooths the entry "
    "price but doesn't remove risk.\n\n"
    "I can model how much you could set aside each month for a goal and how that changes if your income or spending "
    "changes - want me to run that? For product selection, a SEBI-registered investment adviser is the right person.")

# Output scan: product names / tickers the model must not emit.
_OUT_BLOCK = re.compile(
    r"(?i)\b(parag parikh|axis bluechip|mirae asset|nippon india|quant (?:small|mid|active|flexi)|sbi (?:small cap|bluechip|"
    r"nifty)|hdfc (?:index|flexi|mid-?cap|top 100)|icici pru(?:dential)? (?:bluechip|value)|uti nifty|motilal oswal|"
    r"nifty ?bees|gold ?bees|bharat bond|reliance industries|tcs|infosys|adani (?:enterprises|power|ports)|tata motors|"
    r"bitcoin|ethereum|dogecoin|solana|zerodha coin)\b|"
    r"\b(?:buy|invest in|go for|pick|choose|allocate to)\s+(?:the\s+)?[A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+)*\s+"
    r"(?:Fund|ETF|Index Fund|Bluechip|Midcap|Smallcap|Flexi ?cap|stock|shares)\b")


def is_investment_pick_request(text: str) -> bool:
    t = text or ""
    if _ASK.search(t):
        return True
    if _NAMED.search(t) and _BUY_VERB.search(t):
        return True
    return False


def output_violates(text: str) -> bool:
    return bool(_OUT_BLOCK.search(text or ""))


def check_input(text: str):
    """-> educational reply string if the request asks for a specific product, else None."""
    return EDUCATIONAL_REPLY if is_investment_pick_request(text) else None


def sanitize_output(text: str) -> str:
    """Last line of defence: if the model slipped a specific product in, replace the whole answer."""
    return EDUCATIONAL_REPLY if output_violates(text) else text


SYSTEM_RULES = (
    "HARD RULES: You are an educational personal-finance coach for an Indian user. You may explain concepts, model "
    "scenarios with the provided tools, and discuss budgeting, saving, debt, insurance and goals in general terms. "
    "You must NEVER recommend, rank, or name specific stocks, mutual funds, ETFs, bonds, crypto assets, schemes, or "
    "any specific securities/products to buy, sell or hold - even if asked directly or hypothetically. If asked, "
    "explain the relevant concepts and risks and refer to a SEBI-registered adviser. All rupee figures must come "
    "from tool results; never invent numbers. Changes to budgets, goals or profile must be PROPOSED with the "
    "propose_change tool - never claim you applied one; the user must click Confirm."
)
