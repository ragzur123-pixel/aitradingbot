import json
import logging
from datetime import datetime, timezone
from utils import setup_logging

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

logger = setup_logging("database_manager")

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String)
    asset = Column(String)
    direction = Column(String)
    status = Column(String)
    entry_price = Column(Float)
    qty = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    order_id = Column(String)
    confidence_level = Column(Integer)
    outcome = Column(String)
    profit_loss = Column(Float)
    exit_reason = Column(String)
    full_decision = Column(String)

class SystemState(Base):
    __tablename__ = 'system_state'
    
    key = Column(String, primary_key=True)
    value = Column(String)

class TradingDatabase:
    """ACID-compliant database manager for trade state management using SQLAlchemy."""
    def __init__(self, db_path="trading_state.db"):
        self.db_path = db_path
        # Using SQLite, but connection string can be modified for Postgres/MySQL
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self._init_db()
        self.Session = sessionmaker(bind=self.engine)

    def _init_db(self):
        # Creates tables if they don't exist
        Base.metadata.create_all(self.engine)

    def _to_dict(self, obj):
        if not obj: return None
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    def add_trade(self, trade_data):
        with self.Session() as session:
            new_trade = Trade(
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                asset=trade_data.get("asset"),
                direction=trade_data.get("direction"),
                status="OPEN",
                confidence_level=trade_data.get("confidence_level"),
                full_decision=trade_data.get("full_decision")
            )
            session.add(new_trade)
            session.commit()
            return new_trade.id

    def update_trade(self, ticker, direction, update_dict):
        with self.Session() as session:
            # Update the latest open trade for this asset/direction
            trade = session.query(Trade).filter(
                Trade.asset == ticker,
                Trade.direction == direction,
                Trade.status == "OPEN"
            ).order_by(Trade.id.desc()).first()
            
            if trade:
                for key, value in update_dict.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                session.commit()
            else:
                logger.warning(f"Failed to update trade: No OPEN trade found for {ticker} ({direction})")

    def get_open_trades(self):
        with self.Session() as session:
            trades = session.query(Trade).filter(Trade.status == "OPEN").all()
            return [self._to_dict(t) for t in trades]

    def get_recent_history(self, ticker, limit=5):
        with self.Session() as session:
            trades = session.query(Trade).filter(Trade.asset == ticker).order_by(Trade.id.desc()).limit(limit).all()
            return [self._to_dict(t) for t in trades]

    def set_state(self, key, value):
        with self.Session() as session:
            state = session.query(SystemState).filter(SystemState.key == key).first()
            if state:
                state.value = str(value)
            else:
                new_state = SystemState(key=key, value=str(value))
                session.add(new_state)
            session.commit()

    def get_state(self, key, default=None):
        with self.Session() as session:
            state = session.query(SystemState).filter(SystemState.key == key).first()
            return state.value if state else default

if __name__ == "__main__":
    db = TradingDatabase()
    db.set_state("bot_status", "ACTIVE")
    print(f"Bot Status: {db.get_state('bot_status')}")
