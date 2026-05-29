import json
import os
import urllib.error
import urllib.request


_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

_KNOWN_DOMAINS = {"marketing", "sales", "finance", "hr", "generic"}

_KEYWORD_MAP = {
    "marketing": {
        "clicks", "impressions", "displays", "ctr", "cpc", "cpm", "roas",
        "spend", "cost", "conversions", "revenue", "campaign", "ad_group",
        "keyword", "creative", "post_click", "view_through", "reach",
        "frequency", "engagement", "bounce_rate", "sessions", "pageviews",
    },
    "sales": {
        "invoice", "order", "customer", "client", "salesperson", "sales_rep",
        "unit_price", "quantity", "discount", "tax", "subtotal", "total",
        "net_revenue", "gross_revenue", "product", "sku", "payment_status",
    },
    "finance": {
        "debit", "credit", "balance", "account", "ledger", "journal",
        "transaction", "amount", "currency", "exchange_rate", "budget",
        "forecast", "actual", "variance", "gl_code",
    },
    "hr": {
        "employee", "department", "salary", "hire_date", "termination",
        "headcount", "position", "manager", "performance", "leave",
    },
}


def detect_domain(columns: list[str]) -> str:
    """
    Detect the business domain for a given list of column names.
    Returns one of: marketing, sales, finance, hr, generic.

    Strategy:
        1. Try Gemini API for smart detection.
        2. Fall back to keyword matching.
        3. Fall back to 'generic'.
    """
    return _detect_via_gemini(columns) or _detect_via_keywords(columns) or "generic"


def _detect_via_gemini(columns: list[str]) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = (
        "You are a data analyst. Given the following column names from a dataset, "
        "identify the business domain. Reply with exactly one word from this list: "
        "marketing, sales, finance, hr, generic.\n\n"
        f"Columns: {', '.join(columns)}\n\nDomain:"
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_GEMINI_URL}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result  = json.loads(resp.read().decode("utf-8"))
            text    = result["candidates"][0]["content"]["parts"][0]["text"]
            domain  = text.strip().lower().split()[0]
            return domain if domain in _KNOWN_DOMAINS else None
    except Exception:
        return None


def _detect_via_keywords(columns: list[str]) -> str | None:
    normalized = {col.strip().lower().replace(" ", "_") for col in columns}
    scores = {
        domain: len(normalized & keywords)
        for domain, keywords in _KEYWORD_MAP.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda x: x[1])
    return best_domain if best_score >= 2 else None
