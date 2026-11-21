"""Merchant normalisation, built-in keyword categories, learned user rules, Gemini for unknown merchants."""
import hashlib
import re

from . import db, gemini

CATEGORIES = ["Income", "Rent", "Groceries", "Dining", "Transport", "Utilities", "Subscriptions", "Shopping",
              "Health", "Entertainment", "Travel", "EMI & Loans", "Insurance", "Savings & Investments",
              "Education", "Transfers", "Cash", "Other"]
# Categories that are not "spending" for budget/surplus maths.
NON_SPEND = {"Income", "Savings & Investments", "Transfers"}
ESSENTIAL = {"Rent", "Groceries", "Utilities", "Health", "EMI & Loans", "Insurance", "Transport", "Education"}

BUILTIN = [
    ("Income", r"salary|payroll|stipend|interest paid|int\.?pd|dividend|cashback|refund|reversal|freelance|bonus"),
    ("Rent", r"\brent\b|landlord|nobroker|housing society|maintenance charges"),
    ("Groceries", r"bigbasket|blinkit|zepto|grofers|dmart|d-?mart|reliance fresh|more retail|jiomart|instamart|"
                  r"grocer|supermarket|vegetable|kirana|milk|spencer"),
    ("Dining", r"swiggy|zomato|restaurant|cafe|coffee|starbucks|mcdonald|dominos|domino|kfc|pizza|burger|biryani|"
               r"barbeque|eatery|dhaba|bakery|chaayos|haldiram|food|dineout"),
    ("Transport", r"uber|ola\b|olacabs|rapido|metro|irctc|petrol|fuel|hp pay|indian oil|iocl|bharat petroleum|bpcl|"
                  r"fastag|parking|toll|redbus|namma"),
    ("Utilities", r"electricity|bescom|msedcl|tata power|adani elec|bses|water bill|gas|piped|airtel|jio|vodafone|"
                  r"\bvi\b|bsnl|broadband|act fibernet|recharge|dth|tatasky|postpaid|mobile bill|wifi"),
    ("Subscriptions", r"netflix|spotify|hotstar|prime video|amazon prime|youtube premium|apple\.com|icloud|google one|"
                      r"gym|cult\.?fit|cultfit|sonyliv|zee5|jiocinema|audible|adobe|microsoft|chatgpt|openai|notion|"
                      r"linkedin|canva|dropbox|membership|wynk|gaana"),
    ("Entertainment", r"bookmyshow|pvr|inox|movie|steam|playstation|gaming|concert|event"),
    ("Health", r"pharmacy|apollo|medplus|1mg|netmeds|hospital|clinic|diagnostic|lab\b|pathology|doctor|dental|"
               r"practo|medical"),
    ("Shopping", r"amazon|flipkart|myntra|ajio|nykaa|meesho|zudio|westside|lifestyle|croma|decathlon|ikea|"
                 r"pantaloons|shoppers stop|reliance digital|tatacliq|lenskart"),
    ("Travel", r"makemytrip|goibibo|cleartrip|airlines|indigo|vistara|air india|oyo|airbnb|hotel|booking\.com|"
               r"yatra|resort"),
    ("EMI & Loans", r"\bemi\b|loan|bajaj fin|hdfc ltd|home loan|car loan|personal loan|nach.*(?:loan|emi)|"
                    r"credit card payment|cc payment|cred\b|repayment"),
    ("Insurance", r"insurance|lic\b|premium|policybazaar|acko|digit|star health|icici pru|max life"),
    ("Savings & Investments", r"\bsip\b|mutual fund|groww|zerodha|upstox|coin\b|kuvera|ppf|nps|fixed deposit|\bfd\b|"
                              r"recurring deposit|\brd\b|investment|demat|smallcase|indmoney"),
    ("Education", r"school|college|tuition|udemy|coursera|byju|unacademy|fees|upgrad|course|exam"),
    ("Cash", r"\batm\b|cash wdl|cash withdrawal|nwd|self withdrawal"),
    ("Transfers", r"neft|imps|rtgs|transfer|self transfer|own account|sent to|trf"),
]
_COMPILED = [(c, re.compile(p, re.I)) for c, p in BUILTIN]


BRANDS = ["swiggy", "zomato", "netflix", "spotify", "hotstar", "prime video", "youtube", "icloud", "cult fit",
          "cultfit", "amazon", "flipkart", "myntra", "bigbasket", "blinkit", "zepto", "dmart", "uber", "ola", "rapido",
          "airtel", "jio", "bescom", "apollo", "bajaj", "groww", "lic", "starbucks", "bookmyshow", "irctc", "nykaa",
          "linkedin", "chatgpt", "audible", "gym"]


def merchant_key(desc: str) -> str:
    """Stable merchant identity: 'UPI-SWIGGY-412345@okhdfc-ORDER' -> 'swiggy'."""
    s = desc.lower()
    for b in BRANDS:
        if re.search(r"(?<![a-z])" + b.replace(" ", "[ ._-]?") + r"(?![a-z])", s):
            return b.replace(" ", "")
    s = re.sub(r"^sms:\s*", "", s)
    s = re.sub(r"\(upi\)", " ", s)
    s = re.sub(r"\b(upi|neft|imps|rtgs|pos|ach|nach|ecs|ref|txn|trf|cr|dr|debit|credit|payment|paid|to|from|towards|"
               r"order|bill|by|via|vpa|info|card|xx\d+)\b", " ", s)
    s = re.sub(r"@[a-z0-9]+", " ", s)               # upi handle suffix
    s = re.sub(r"\b\d{4,}\b|\b[a-z]*\d{5,}[a-z\d]*\b", " ", s)  # long numeric refs
    s = re.sub(r"[^a-z& ]+", " ", s)
    parts = [p for p in s.split() if len(p) > 1]
    return " ".join(parts[:2]) if parts else "unknown"


def builtin_category(desc: str, amount: float):
    for cat, rx in _COMPILED:
        if rx.search(desc):
            if cat == "Income" and amount < 0 and not re.search("interest|dividend", desc, re.I):
                continue
            return cat
    if amount > 0:
        return "Income"
    return None


def get_rules(uid):
    return db.rows("SELECT * FROM rules WHERE uid=?", (uid,))


def rule_category(rules, key, desc):
    low = desc.lower()
    for r in rules:
        if r["pattern"] == key or (len(r["pattern"]) > 4 and r["pattern"] in low):
            return r["category"], r["id"]
    return None, None


def ai_categorize(merchants: list[dict]):
    """merchants: [{key, sample, amount}] -> {key: category} using Gemini, cached by content hash."""
    if not merchants:
        return {}
    listing = "\n".join(f"- {m['key']} | e.g. \"{m['sample']}\" | Rs {abs(m['amount']):.0f} "
                        f"{'in' if m['amount'] > 0 else 'out'}" for m in merchants)
    prompt = (f"Categorise these Indian bank-statement merchants. Allowed categories: {', '.join(CATEGORIES)}.\n"
              f"Return JSON object mapping each merchant key to exactly one allowed category.\n{listing}")
    res = gemini.generate(prompt, system="You label Indian personal-finance transactions. JSON only.",
                          json_mode=True,
                          cache_key=hashlib.sha256(listing.encode()).hexdigest())
    if not isinstance(res, dict):
        return {}
    return {k: v for k, v in res.items() if v in CATEGORIES}


def merchant_history(uid):
    """Majority category per merchant among already-labelled transactions (so 'SMS: ramesh kumar' inherits 'Rent')."""
    votes = {}
    for r in db.rows("SELECT merchant, category, COUNT(*) c FROM transactions WHERE uid=? AND category<>'Other' "
                     "GROUP BY merchant, category", (uid,)):
        votes.setdefault(r["merchant"], []).append((r["c"], r["category"]))
    return {m: max(v)[1] for m, v in votes.items()}


def categorize_batch(uid, items: list[dict], use_ai=True):
    """Fills merchant/category/cat_source on each item. Order: user rules > built-in keywords > Gemini > Other."""
    rules = get_rules(uid)
    unknown = {}
    hist = merchant_history(uid)
    for it in items:
        key = merchant_key(it["description"])
        it["merchant"] = key
        cat, rid = rule_category(rules, key, it["description"])
        if cat:
            it["category"], it["cat_source"] = cat, "rule"
            db.run("UPDATE rules SET hits=hits+1 WHERE id=?", (rid,))
            continue
        cat = builtin_category(it["description"], it["amount"])
        if cat:
            it["category"], it["cat_source"] = cat, "keyword"
        elif key in hist and key != "unknown":
            it["category"], it["cat_source"] = hist[key], "history"
        else:
            unknown.setdefault(key, {"key": key, "sample": it["description"], "amount": it["amount"]})
            it["category"], it["cat_source"] = "Other", "none"
    if unknown and use_ai:
        ai = ai_categorize(list(unknown.values())[:60])
        for it in items:
            if it["cat_source"] == "none" and it["merchant"] in ai:
                it["category"], it["cat_source"] = ai[it["merchant"]], "ai"
    return items


def learn_rule(uid, tx_id, category):
    """User corrected a category: store a rule on the merchant and re-apply to existing, non-user-set rows."""
    tx = db.one("SELECT * FROM transactions WHERE id=? AND uid=?", (tx_id, uid))
    if not tx:
        return None
    key = tx["merchant"]
    db.run("UPDATE transactions SET category=?, cat_source='user' WHERE id=? AND uid=?", (category, tx_id, uid))
    if key and key != "unknown":
        db.run("INSERT INTO rules(uid,pattern,category) VALUES(?,?,?) "
               "ON CONFLICT(uid,pattern) DO UPDATE SET category=excluded.category", (uid, key, category))
        n = db.rows("SELECT COUNT(*) c FROM transactions WHERE uid=? AND merchant=? AND id<>? AND cat_source<>'user' "
                    "AND category<>?", (uid, key, tx_id, category))[0]["c"]
        db.run("UPDATE transactions SET category=?, cat_source='rule' WHERE uid=? AND merchant=? AND id<>? "
               "AND cat_source<>'user'", (category, uid, key, tx_id))
        return {"merchant": key, "rule_created": True, "also_updated": n}
    return {"merchant": key, "rule_created": False, "also_updated": 0}
