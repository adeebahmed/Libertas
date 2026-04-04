"""
Extract institution name and account hints from a filename.

Examples:
  "Fidelity_Roth_IRA_2024.csv"        -> ("Fidelity", "roth_ira")
  "Schwab-Brokerage-March2024.csv"     -> ("Schwab", "brokerage")
  "Coinbase-transactions.csv"          -> ("Coinbase", "crypto")
  "my_portfolio.csv"                   -> ("my portfolio", "brokerage")
  "Chase5678_Activity_20240301.csv"    -> ("Chase", "checking")
  "Vanguard_401k_Holdings.xlsx"        -> ("Vanguard", "401k")
"""
import os
import re

ACCOUNT_TYPE_KEYWORDS = {
    "roth_ira": ["roth", "roth_ira", "roth-ira", "rothira"],
    "401k": ["401k", "401(k)", "retirement"],
    "hsa": ["hsa", "health savings"],
    "crypto": ["crypto", "coinbase", "bitcoin", "ethereum", "defi", "wallet"],
    "savings": ["savings", "saving", "emergency"],
    "checking": ["checking", "bank", "debit"],
    "credit_card": ["credit card", "credit_card", "creditcard", "visa", "mastercard", "amex", "sapphire", "freedom"],
    "student_loan": ["student loan", "student_loan", "studentloan", "navient", "mohela", "sallie mae", "salliemae"],
    "auto_loan": ["auto loan", "auto_loan", "autoloan", "car loan", "carloan", "vehicle loan"],
    "personal_loan": ["personal loan", "personal_loan", "personalloan"],
    "brokerage": ["brokerage", "investment", "trading", "portfolio", "holdings",
                   "positions", "transactions", "activity"],
    "real_estate": ["real estate", "real_estate", "property", "mortgage"],
}

# Known financial institutions (case-insensitive match against filename)
KNOWN_INSTITUTIONS = [
    "fidelity", "schwab", "vanguard", "coinbase", "robinhood", "chase",
    "td ameritrade", "etrade", "e-trade", "merrill", "merrill lynch",
    "wealthfront", "betterment", "interactive brokers", "ibkr",
    "sofi", "webull", "ally", "marcus", "capital one", "wells fargo",
    "bank of america", "usaa", "navy federal", "charles schwab",
    "gemini", "kraken", "binance", "crypto.com",
]


def parse_filename(filename: str) -> tuple[str, str]:
    """
    Parse a filename to extract (institution_name, account_type).
    Returns best guesses; defaults to (stem_cleaned, "brokerage").
    """
    stem = os.path.splitext(filename)[0]

    # Normalize separators to spaces
    normalized = re.sub(r"[_\-\.]+", " ", stem)
    # Remove numbers that look like dates or account numbers
    cleaned = re.sub(r"\b\d{4,}\b", "", normalized)  # long numbers
    cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", cleaned)  # dates
    cleaned = cleaned.strip()
    lower = cleaned.lower()

    # Find institution
    institution = None
    for inst in KNOWN_INSTITUTIONS:
        if inst in lower:
            # Capitalize nicely
            institution = inst.title()
            break

    if not institution:
        # Use the first word(s) before any type keywords
        words = cleaned.split()
        if words:
            institution = words[0]

    # Find account type
    account_type = "brokerage"  # default
    for atype, keywords in ACCOUNT_TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            account_type = atype
            break

    return institution or "Unknown", account_type
