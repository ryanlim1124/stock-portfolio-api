"""
models.py
---------
This file defines the SHAPE of the data our API works with.

We use Pydantic (the library FastAPI is built on top of) to describe
each piece of data as a Python class. FastAPI then uses these classes
to automatically:
  1. Validate incoming data (reject bad requests before our code even runs)
  2. Convert Python objects <-> JSON
  3. Generate interactive API documentation

Think of these as "contracts": a promise about exactly what fields
a piece of data will have, and what type each one is.
"""

from pydantic import BaseModel, Field
from typing import Optional


class StockCreate(BaseModel):
    """
    What the CLIENT must send us in the body of a POST request,
    when adding a new stock to the portfolio.
    """
    ticker: str = Field(..., examples=["AAPL"], description="Stock ticker symbol")
    shares: float = Field(..., gt=0, examples=[10], description="Number of shares owned")
    buy_price: float = Field(..., gt=0, examples=[150.00], description="Price paid per share (USD)")


class StockUpdate(BaseModel):
    """
    What the client sends when updating an existing stock.
    Every field is Optional, because a PUT request might only
    want to change ONE thing (e.g. just refresh current_price).
    """
    shares: Optional[float] = Field(None, gt=0)
    buy_price: Optional[float] = Field(None, gt=0)
    current_price: Optional[float] = Field(None, gt=0)


class Stock(BaseModel):
    """
    What the SERVER sends back to the client. Notice it has MORE
    fields than StockCreate — market_value, gain_loss, gain_loss_pct
    are calculated by our code, not supplied by the client.
    """
    ticker: str
    shares: float
    buy_price: float
    current_price: float
    market_value: float
    gain_loss: float
    gain_loss_pct: float


class PortfolioSummary(BaseModel):
    """
    A rolled-up view across the whole portfolio — one object built
    by combining every individual stock.
    """
    total_cost: float
    total_market_value: float
    total_gain_loss: float
    total_gain_loss_pct: float
    number_of_positions: int


class RefreshResult(BaseModel):
    """
    Returned after asking the API to pull a LIVE price from the
    market (via yfinance) for one or all holdings.
    """
    ticker: str
    old_price: float
    new_price: float
    updated: bool



