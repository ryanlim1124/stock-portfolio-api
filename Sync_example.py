"""
sync_example.py
----------------
A worked example of using api_client.py the way your portfolio-analyzer
script would. Since I don't have your analyzer's actual source, the
`my_holdings` list below stands in for wherever your script currently
keeps its portfolio data (a DataFrame, a dict, a CSV you load) — swap
that part out and the API calls stay the same.

Run this AFTER `uvicorn main:app --reload` is already running in
another terminal:
    python3 sync_example.py
"""

from api_client import PortfolioAPIClient

# --- Stand-in for your analyzer's real data source ---------------
# In your actual project, this list would come from wherever
# portfolio-analyzer currently stores holdings (a DataFrame row loop,
# a CSV read, etc.) instead of being hard-coded here.
my_holdings = [
    {"ticker": "AAPL", "shares": 10, "buy_price": 150.00},
    {"ticker": "MSFT", "shares": 5, "buy_price": 310.00},
]
# -------------------------------------------------------------------

API_KEY = "dev-secret-key"  # must match the API_KEY the server is running with

client = PortfolioAPIClient(api_key=API_KEY)

print("Syncing local holdings into the API...")
client.sync_holdings(my_holdings)

print("Refreshing live prices for everything...")
results = client.refresh_all_prices()
for r in results:
    status = "updated" if r["updated"] else "skipped (no data)"
    print(f"  {r['ticker']}: ${r['old_price']} -> ${r['new_price']} ({status})")

print("\nCurrent portfolio summary:")
summary = client.get_summary()
for key, value in summary.items():
    print(f"  {key}: {value}")