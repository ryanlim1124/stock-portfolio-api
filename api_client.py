"""
api_client.py
-------------
A small, reusable client for talking to the Stock Portfolio API from
OTHER Python scripts — this is the piece that lets you plug your
`portfolio-analyzer` project into this API instead of it working on
local data directly.

I don't have your actual portfolio-analyzer source, so this file is a
drop-in TEMPLATE: import these functions from your analyzer script and
call them wherever it currently reads/writes its own local data
structures. Everywhere here uses the `requests` library, which just
makes HTTP calls from Python — the same kind of call `curl` makes,
or your browser makes when it loads a page.
"""

import requests

BASE_URL = "http://127.0.0.1:8000"


class PortfolioAPIClient:
    """
    Wraps every endpoint as a plain Python method, so calling code
    reads like `client.add_stock(...)` instead of constructing raw
    HTTP requests everywhere.
    """

    def __init__(self, base_url: str = BASE_URL, api_key: str | None = None):
        self.base_url = base_url
        self.api_key = api_key

    def _auth_headers(self) -> dict:
        # Only the write endpoints need this; GETs ignore it harmlessly.
        return {"X-API-Key": self.api_key} if self.api_key else {}

    def list_stocks(self) -> list[dict]:
        r = requests.get(f"{self.base_url}/stocks")
        r.raise_for_status()
        return r.json()

    def get_stock(self, ticker: str) -> dict | None:
        r = requests.get(f"{self.base_url}/stocks/{ticker}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def add_stock(self, ticker: str, shares: float, buy_price: float) -> dict:
        r = requests.post(
            f"{self.base_url}/stocks",
            json={"ticker": ticker, "shares": shares, "buy_price": buy_price},
            headers=self._auth_headers(),
        )
        r.raise_for_status()
        return r.json()

    def update_stock(self, ticker: str, **fields) -> dict:
        """
        Example: client.update_stock("AAPL", current_price=182.50)
        """
        r = requests.put(
            f"{self.base_url}/stocks/{ticker}",
            json=fields,
            headers=self._auth_headers(),
        )
        r.raise_for_status()
        return r.json()

    def delete_stock(self, ticker: str) -> None:
        r = requests.delete(f"{self.base_url}/stocks/{ticker}", headers=self._auth_headers())
        r.raise_for_status()

    def refresh_price(self, ticker: str) -> dict:
        r = requests.post(f"{self.base_url}/stocks/{ticker}/refresh-price", headers=self._auth_headers())
        r.raise_for_status()
        return r.json()

    def refresh_all_prices(self) -> list[dict]:
        r = requests.post(f"{self.base_url}/portfolio/refresh-all-prices", headers=self._auth_headers())
        r.raise_for_status()
        return r.json()

    def get_summary(self) -> dict:
        r = requests.get(f"{self.base_url}/portfolio/summary")
        r.raise_for_status()
        return r.json()

    def sync_holdings(self, holdings: list[dict]) -> None:
        """
        Convenience method: given a list like
            [{"ticker": "AAPL", "shares": 10, "buy_price": 150}, ...]
        (the kind of structure your portfolio-analyzer likely already
        builds), makes sure the API's portfolio matches it — adding
        anything missing and updating share counts for anything that
        already exists. This is the one method you'd most likely call
        directly from portfolio-analyzer.
        """
        existing = {s["ticker"] for s in self.list_stocks()}
        for h in holdings:
            ticker = h["ticker"].upper()
            if ticker in existing:
                self.update_stock(ticker, shares=h["shares"], buy_price=h["buy_price"])
            else:
                self.add_stock(ticker, h["shares"], h["buy_price"])