"""
db_models.py
------------
The actual DATABASE TABLE definition, written as a Python class
(SQLAlchemy's "ORM" — Object-Relational Mapper — lets you work with
rows as Python objects instead of writing SQL by hand).

This is intentionally a SEPARATE file/concept from models.py:
  - models.py    (Pydantic) = the shape of API requests/responses
  - db_models.py (SQLAlchemy) = the shape of a row in the database

They often look similar, but they don't have to match exactly, and
keeping them separate means you can change your database schema
without automatically changing your API's public contract, or vice
versa.
"""

from sqlalchemy import Column, String, Float
from database import Base


class StockDB(Base):
    __tablename__ = "stocks"

    # primary_key=True means SQLite guarantees this value is unique —
    # exactly what a ticker symbol naturally is here.
    ticker = Column(String, primary_key=True, index=True)
    shares = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)