"""
main.py
-------
The API server. Compared to the first version, this one:
  - stores data in a real SQLite database instead of an in-memory dict
  - requires an API key on write operations (POST/PUT/DELETE)
  - can fetch LIVE prices from the market via yfinance
  - serves a small interactive web page at /app so a non-technical
    person can use this without knowing what an API even is
 
RUN IT:
    uvicorn main:app --reload
 
THEN OPEN:
    http://127.0.0.1:8000/docs   -> interactive API documentation
    http://127.0.0.1:8000/app    -> the human-friendly web dashboard
"""
 
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
 
from database import engine, get_db, Base
from db_models import StockDB
from models import Stock, StockCreate, StockUpdate, PortfolioSummary, RefreshResult
from auth import require_api_key
from price_service import fetch_live_price
 
# ------------------------------------------------------------------
# 1. Create the database tables (if they don't already exist).
#    This runs once, when the app starts up.
# ------------------------------------------------------------------
Base.metadata.create_all(bind=engine)
 
app = FastAPI(
    title="Stock Portfolio API",
    description="A REST API for tracking a stock portfolio, backed by a real database, "
                "live market prices, and API-key-protected writes.",
    version="2.0.0",
)
 
# ------------------------------------------------------------------
# 2. Serve the human-facing web page.
#    Anything in the ./static folder is now reachable in a browser
#    under /app (html=True also makes /app load index.html automatically).
# ------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="static", html=True), name="static")
 
 
def calculate_stock_view(row: StockDB) -> Stock:
    """
    Takes one database ROW (a StockDB object) and returns a fully
    computed Stock object for the API response, with market value
    and gain/loss worked out.
    """
    market_value = row.shares * row.current_price
    cost_basis = row.shares * row.buy_price
    gain_loss = market_value - cost_basis
    gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis else 0
 
    return Stock(
        ticker=row.ticker,
        shares=row.shares,
        buy_price=row.buy_price,
        current_price=row.current_price,
        market_value=round(market_value, 2),
        gain_loss=round(gain_loss, 2),
        gain_loss_pct=round(gain_loss_pct, 2),
    )
 
 
def get_stock_or_404(ticker: str, db: Session) -> StockDB:
    """Shared lookup logic used by several endpoints below."""
    row = db.get(StockDB, ticker)
    if row is None:
        raise HTTPException(status_code=404, detail=f"'{ticker}' not found in portfolio")
    return row
 
 
# ------------------------------------------------------------------
# 3. ENDPOINTS
#    Every function below that takes `db: Session = Depends(get_db)`
#    receives its own database session for that one request only.
# ------------------------------------------------------------------
 
@app.get("/")
def root():
    return {"message": "Stock Portfolio API is running. Visit /docs or /app."}
 
 
# ---- READ endpoints: public, no API key required ----
 
@app.get("/stocks", response_model=list[Stock])
def list_stocks(db: Session = Depends(get_db)):
    rows = db.query(StockDB).all()
    return [calculate_stock_view(r) for r in rows]
 
 
@app.get("/stocks/{ticker}", response_model=Stock)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    row = get_stock_or_404(ticker.upper(), db)
    return calculate_stock_view(row)
 
 
@app.get("/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)):
    rows = db.query(StockDB).all()
    if not rows:
        return PortfolioSummary(
            total_cost=0, total_market_value=0,
            total_gain_loss=0, total_gain_loss_pct=0,
            number_of_positions=0,
        )
 
    stocks = [calculate_stock_view(r) for r in rows]
    total_cost = sum(s.shares * s.buy_price for s in stocks)
    total_market_value = sum(s.market_value for s in stocks)
    total_gain_loss = total_market_value - total_cost
    total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost else 0
 
    return PortfolioSummary(
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_gain_loss=round(total_gain_loss, 2),
        total_gain_loss_pct=round(total_gain_loss_pct, 2),
        number_of_positions=len(stocks),
    )
 
 
# ---- WRITE endpoints: require a valid X-API-Key header ----
 
@app.post("/stocks", response_model=Stock, status_code=201, dependencies=[Depends(require_api_key)])
def add_stock(new_stock: StockCreate, db: Session = Depends(get_db)):
    ticker = new_stock.ticker.upper()
    if db.get(StockDB, ticker):
        raise HTTPException(status_code=400, detail=f"'{ticker}' already exists. Use PUT to update it.")
 
    row = StockDB(
        ticker=ticker,
        shares=new_stock.shares,
        buy_price=new_stock.buy_price,
        current_price=new_stock.buy_price,  # starting assumption until refreshed/updated
    )
    db.add(row)
    db.commit()
    db.refresh(row)  # reload from the DB so we know it actually saved
    return calculate_stock_view(row)
 
 
@app.put("/stocks/{ticker}", response_model=Stock, dependencies=[Depends(require_api_key)])
def update_stock(ticker: str, update: StockUpdate, db: Session = Depends(get_db)):
    row = get_stock_or_404(ticker.upper(), db)
 
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
 
    db.commit()
    db.refresh(row)
    return calculate_stock_view(row)
 
 
@app.delete("/stocks/{ticker}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_stock(ticker: str, db: Session = Depends(get_db)):
    row = get_stock_or_404(ticker.upper(), db)
    db.delete(row)
    db.commit()
    return None
 
 
# ---- LIVE PRICE endpoints: also require the API key, since they change data ----
 
@app.post("/stocks/{ticker}/refresh-price", response_model=RefreshResult, dependencies=[Depends(require_api_key)])
def refresh_price(ticker: str, db: Session = Depends(get_db)):
    """
    Fetches the current live market price for one holding (via
    yfinance) and updates the stored current_price with it.
    """
    row = get_stock_or_404(ticker.upper(), db)
    old_price = row.current_price
 
    try:
        new_price = fetch_live_price(row.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
    row.current_price = new_price
    db.commit()
 
    return RefreshResult(ticker=row.ticker, old_price=old_price, new_price=new_price, updated=True)
 
 
@app.post("/portfolio/refresh-all-prices", response_model=list[RefreshResult], dependencies=[Depends(require_api_key)])
def refresh_all_prices(db: Session = Depends(get_db)):
    """
    Same idea as above, but loops over every holding in the portfolio.
    A stock whose live price couldn't be fetched is skipped (not
    updated) rather than failing the whole request.
    """
    results = []
    for row in db.query(StockDB).all():
        old_price = row.current_price
        try:
            new_price = fetch_live_price(row.ticker)
            row.current_price = new_price
            results.append(RefreshResult(ticker=row.ticker, old_price=old_price, new_price=new_price, updated=True))
        except ValueError:
            results.append(RefreshResult(ticker=row.ticker, old_price=old_price, new_price=old_price, updated=False))
 
    db.commit()
    return results