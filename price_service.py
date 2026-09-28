"""
price_service.py
-----------------
Fetches a real, live stock price using yfinance — the exact same
library your stock-screener project uses to pull market data.

This logic is deliberately kept in its OWN file, separate from
main.py. That way main.py only needs to know "there's a function
that returns a live price for a ticker" — not how that price is
actually obtained. If you ever swapped yfinance for a paid data
provider later, only this one file would need to change.
"""

import yfinance as yf


def fetch_live_price(ticker: str) -> float:
    """
    Returns the most recent closing price available for `ticker`.
    Raises ValueError if the ticker is invalid or has no data
    (e.g. a typo, or a delisted stock) — main.py turns that into a
    proper 400 error response.
    """
    stock = yf.Ticker(ticker)
    history = stock.history(period="1d")

    if history.empty:
        raise ValueError(f"No price data found for '{ticker}'. Check the ticker is correct.")

    latest_close = history["Close"].iloc[-1]
    return round(float(latest_close), 2)