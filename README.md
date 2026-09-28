# Stock Portfolio API (v2) — database, live prices, auth, frontend

A REST API for tracking a stock portfolio, now with:
- a real **SQLite database** (data survives a restart)
- **live market prices** pulled via `yfinance`
- **API-key authentication** on every write
- a small **interactive web dashboard**, no terminal required
- a reusable **Python client**, ready to plug your `portfolio-analyzer`
  project into it

Every endpoint is verified by `test_api.py` before you even run it —
all checks pass.

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Run it

```bash
uvicorn main:app --reload
```

The first time you run this, a `portfolio.db` SQLite file is created
automatically in this folder — that's your entire database, as a
single file.

Open in a browser:
- **http://127.0.0.1:8000/app** — the interactive dashboard
- **http://127.0.0.1:8000/docs** — the interactive API reference

## 3. Using the dashboard

1. Open `/app`.
2. Paste `dev-secret-key` into the "API key" box (that's the default
   dev key set in `auth.py` — change it before deploying anywhere real).
3. Add a stock with the form. It appears in the table immediately.
4. Click **Refresh** on a row to pull that stock's real, live price
   from the market via `yfinance`. Click **Refresh all live prices**
   to do every holding at once.
5. Watch the summary cards update — total cost, market value, and
   gain/loss, recalculated from the database every time.

Reading data (the table, the summary) works without the key. Adding,
editing, deleting, or refreshing prices requires it — that split
mirrors how most real APIs separate public reads from protected writes.

## 4. What changed from v1, and why

### A real database (`database.py` + `db_models.py`)
Previously, all data lived in a plain Python dictionary — gone the
moment the server restarted. Now every stock is a row in a SQLite
table, managed through **SQLAlchemy** (an ORM: it lets you write
`db.query(StockDB).all()` instead of raw SQL). `database.py` sets up
the connection; `db_models.py` defines the table shape; every endpoint
in `main.py` now takes a `db: Session = Depends(get_db)` argument to
read/write it.

### API key authentication (`auth.py`)
Every `POST`, `PUT`, and `DELETE` endpoint now requires a header:
```
X-API-Key: dev-secret-key
```
This is enforced with `dependencies=[Depends(require_api_key)]` on
each route — FastAPI runs that check *before* your endpoint function,
and rejects the request with a `401` if the key's wrong or missing.
`GET` endpoints deliberately stay public, matching how most real APIs
split "anyone can look" from "only the owner can change."

### Live prices (`price_service.py`)
Two new endpoints:
- `POST /stocks/{ticker}/refresh-price` — updates one holding
- `POST /portfolio/refresh-all-prices` — updates every holding

Both call `fetch_live_price()`, which asks `yfinance` for the latest
close price — the same data source your `stock-screener` project
already uses, just called from the server side this time instead of
a script you run yourself.

### The dashboard (`static/index.html`)
A single HTML file with plain JavaScript `fetch()` calls — no
framework, no build step. FastAPI serves it directly via
`app.mount("/app", StaticFiles(...))` in `main.py`. This is what makes
the API usable by someone who's never touched a terminal — the exact
"interactive for other people" piece you asked for.

### The client (`api_client.py` + `sync_example.py`)
`PortfolioAPIClient` wraps every endpoint as a normal Python method
(`client.add_stock(...)`, `client.refresh_all_prices()`, etc.) using
the `requests` library. This is the piece that lets `portfolio-analyzer`
talk to this API instead of working on local data directly.

**I don't have your actual `portfolio-analyzer` source**, so
`sync_example.py` is a worked template: it hard-codes a `my_holdings`
list standing in for wherever your script currently keeps its
portfolio data. To actually connect the two projects:
1. Copy `api_client.py` into your `portfolio-analyzer` project folder.
2. Wherever that script currently reads or builds its holdings (a
   DataFrame, a CSV, a dict), replace that step — or add alongside it —
   a call like `client.sync_holdings(your_holdings_list)`.
3. Anywhere it currently prints or plots results, you can instead (or
   additionally) call `client.get_summary()` to pull the API's
   computed totals.

Run the example itself (with the server already running):
```bash
python3 sync_example.py
```

## 5. Testing

```bash
python3 test_api.py
```

This uses a separate, disposable `test_portfolio.db` (never your real
one), and **fakes** the live-price lookup so tests run instantly and
don't depend on internet access or market hours — the app itself still
uses real `yfinance` data when you run it normally.

## 6. Deploying it publicly

See **`DEPLOY.md`** for full step-by-step instructions (Render, plus
notes on Railway/Fly.io) — including the `Dockerfile` already included
here, and what to know about SQLite on free hosting tiers before you do.

## Files

| File                | Purpose                                                         |
|---------------------|------------------------------------------------------------------|
| `main.py`           | The API — all endpoints, now backed by the database             |
| `models.py`         | Pydantic schemas (API request/response shapes)                  |
| `database.py`       | SQLAlchemy engine/session setup                                 |
| `db_models.py`      | The database table definition                                   |
| `auth.py`           | API key authentication                                          |
| `price_service.py`  | Live price fetching via yfinance                                |
| `static/index.html` | The interactive web dashboard                                   |
| `api_client.py`     | Reusable Python client for calling this API from other scripts  |
| `sync_example.py`   | Worked example of syncing local holdings into the API           |
| `test_api.py`       | Automated tests (DB, auth, and mocked live prices)               |
| `Dockerfile`        | Container definition for deployment                             |
| `.env.example`      | Template for the `API_KEY` secret                                |
| `DEPLOY.md`         | Step-by-step deployment guide                                    |

## Endpoint reference

| Method | Path                          | Auth required | Purpose                          |
|--------|-------------------------------|:---:|-----------------------------------|
| GET    | `/`                            |    | Health check                      |
| GET    | `/stocks`                      |    | List every stock                  |
| GET    | `/stocks/{ticker}`             |    | Get one stock                     |
| POST   | `/stocks`                      | ✅  | Add a new stock                   |
| PUT    | `/stocks/{ticker}`             | ✅  | Update a stock                    |
| DELETE | `/stocks/{ticker}`             | ✅  | Remove a stock                    |
| POST   | `/stocks/{ticker}/refresh-price`| ✅ | Pull one live price               |
| POST   | `/portfolio/refresh-all-prices` | ✅ | Pull live prices for everything   |
| GET    | `/portfolio/summary`           |    | Totals across the whole portfolio |
| GET    | `/app`                         |    | The interactive dashboard         |
| GET    | `/docs`                        |    | Interactive API documentation     |

## Where to go from here

- Swap the API key for real multi-user login (accounts + passwords),
  so the app could support more than one person's portfolio.
- Move from SQLite to hosted Postgres for real, non-ephemeral storage.
- Add a scheduled background job that calls `refresh-all-prices`
  automatically every few minutes instead of needing a manual click.
