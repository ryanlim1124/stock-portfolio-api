"""
test_api.py
-----------
Automated checks for the v2 API: real database persistence, API-key
auth on write endpoints, and the live-price refresh endpoints.

Live prices come from the internet (yfinance -> Yahoo Finance), which
we don't want a test suite depending on — a flaky internet connection
shouldn't make your tests fail, and tests should run the same way every
time. So this file "monkeypatches" (temporarily replaces) the real
fetch_live_price function with a fake one that returns a fixed number,
purely for the duration of these tests. In your own environment, the
app itself still calls the REAL yfinance function — only this test file
fakes it.

Run with:
    python3 test_api.py
"""

import os

# Use a separate, disposable database file for tests so this never
# touches the real portfolio.db your app uses day-to-day.
if os.path.exists("test_portfolio.db"):
    os.remove("test_portfolio.db")

import database
database.DATABASE_URL = "sqlite:///./test_portfolio.db"
database.engine = database.create_engine(
    database.DATABASE_URL, connect_args={"check_same_thread": False}
)
database.SessionLocal = database.sessionmaker(
    autocommit=False, autoflush=False, bind=database.engine
)

import price_service
price_service.fetch_live_price = lambda ticker: 999.99  # fake live price for every ticker

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
AUTH = {"X-API-Key": "dev-secret-key"}  # matches the default in auth.py

# 1. Reads are public
r = client.get("/stocks")
print("GET /stocks (empty) ->", r.status_code, r.json())
assert r.status_code == 200 and r.json() == []

# 2. Writing WITHOUT the API key is rejected
r = client.post("/stocks", json={"ticker": "AAPL", "shares": 10, "buy_price": 150})
print("POST /stocks no key ->", r.status_code)
assert r.status_code == 401

# 3. Writing WITH the API key works
r = client.post("/stocks", json={"ticker": "aapl", "shares": 10, "buy_price": 150}, headers=AUTH)
print("POST /stocks with key ->", r.status_code, r.json())
assert r.status_code == 201

# 4. Data actually persisted to the database (not just in memory)
r = client.get("/stocks/AAPL")
assert r.status_code == 200
assert r.json()["shares"] == 10.0
print("GET /stocks/AAPL after add ->", r.status_code, r.json())

# 5. Invalid input still rejected (Pydantic validation, unrelated to DB)
r = client.post("/stocks", json={"ticker": "MSFT", "shares": -1, "buy_price": 10}, headers=AUTH)
print("POST /stocks invalid shares ->", r.status_code)
assert r.status_code == 422

# 6. Update via PUT
r = client.put("/stocks/AAPL", json={"current_price": 180}, headers=AUTH)
print("PUT /stocks/AAPL ->", r.status_code, r.json())
assert r.json()["gain_loss"] == 300.0

# 7. Live price refresh (using the faked price_service function)
r = client.post("/stocks/AAPL/refresh-price", headers=AUTH)
print("POST /stocks/AAPL/refresh-price ->", r.status_code, r.json())
assert r.status_code == 200
assert r.json()["new_price"] == 999.99

# 8. Refresh-all
r = client.post("/portfolio/refresh-all-prices", headers=AUTH)
print("POST /portfolio/refresh-all-prices ->", r.status_code, r.json())
assert r.status_code == 200
assert all(res["updated"] for res in r.json())

# 9. Summary reflects the refreshed price
r = client.get("/portfolio/summary")
print("GET /portfolio/summary ->", r.status_code, r.json())
assert r.json()["number_of_positions"] == 1

# 10. Delete requires auth too
r = client.delete("/stocks/AAPL")
assert r.status_code == 401
r = client.delete("/stocks/AAPL", headers=AUTH)
print("DELETE /stocks/AAPL ->", r.status_code)
assert r.status_code == 204

r = client.get("/stocks")
assert r.json() == []

print("\nALL CHECKS PASSED")

# Clean up the disposable test database
os.remove("test_portfolio.db")