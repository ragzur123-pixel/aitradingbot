import logging
from config_loader import config
from market_feed import get_live_market_data

logger = logging.getLogger("hustle_fund_manager")

class HustleFundManager:
    """
    Manages the 'Treasury Fund' (Index Funds) and 'Total Capital' progress.
    Tracks 'Hustle' contributions and provides a unified dashboard for growth.
    """
    def __init__(self, trading_balance=1000.0):
        self.trading_balance = trading_balance
        self.hustle_cfg = config.get("hustle_fund", {})
        self.target = self.hustle_cfg.get("target_capital", 10000.0)

    def get_treasury_value(self):
        """Calculates current market value of index fund holdings."""
        holdings = self.hustle_cfg.get("index_fund_holdings", {})
        total_val = 0.0
        
        for ticker, units in holdings.items():
            if units <= 0: continue
            df = get_live_market_data(ticker, period="1d")
            if df is not None and not df.empty:
                price = df['Close'].iloc[-1]
                total_val += (price * units)
                
        return round(total_val, 2)

    def get_fund_dashboard(self):
        """Generates a summary of the total fund progress."""
        treasury = self.get_treasury_value()
        total_fund = self.trading_balance + treasury
        progress_pct = (total_fund / self.target) * 100
        
        return {
            "trading_balance": self.trading_balance,
            "treasury_value": treasury,
            "total_fund_value": total_fund,
            "target_capital": self.target,
            "progress_pct": round(progress_pct, 1),
            "hustle_momentum": self.hustle_cfg.get("total_hustle_contributions", 0.0)
        }

    def get_prop_firm_readiness(self):
        """Calculates readiness for a $50k Prop Firm challenge."""
        # Query Research Journal for shadow performance
        import sqlite3
        conn = sqlite3.connect(config.get("system.research_journal_path", "research_journal.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(slippage_adj_pnl) FROM shadow_trades")
        net_pnl = cursor.fetchone()[0] or 0.0
        conn.close()
        
        target = config.get("trading.prop_firm_target", 3000.0)
        drawdown_limit = config.get("trading.max_drawdown_limit", 1000.0)
        
        return {
            "net_pnl": round(net_pnl, 2),
            "target": target,
            "progress_pct": round((net_pnl / target) * 100, 1) if net_pnl > 0 else 0,
            "status": "READY" if net_pnl >= target else "RESEARCHING"
        }

    def get_time_value_audit(self, trading_profit_mtd):
        """
        Calculates the ROI of time spent on the bot vs. Hustle.
        Helps decide if we should code more or hustle more.
        """
        user_wage = self.hustle_cfg.get("user_hourly_wage_usd", 25.0)
        # Assume 10 hours a week spent on bot maintenance/dev
        hours_spent = 40.0 
        hustle_opportunity_cost = hours_spent * user_wage
        
        ratio = trading_profit_mtd / hustle_opportunity_cost if hustle_opportunity_cost > 0 else 0
        
        return {
            "opportunity_cost": round(hustle_opportunity_cost, 2),
            "trading_profit_mtd": round(trading_profit_mtd, 2),
            "bot_efficiency_ratio": round(ratio, 2),
            "recommendation": "HUSTLE_MORE" if ratio < 1.0 else "BOT_IS_SCALING"
        }

    def format_dashboard_text(self):
        """Formats the dashboard for Telegram/HITL notification."""
        db = self.get_fund_dashboard()
        prop = self.get_prop_firm_readiness()
        
        text = (
            f"🏛️ <b>STRATEGIC FUND DASHBOARD</b>\n"
            f"--------------------------------\n"
            f"💰 <b>Trading Base:</b> ${db['trading_balance']:.2f}\n"
            f"📈 <b>Treasury Base:</b> ${db['treasury_value']:.2f}\n"
            f"🚀 <b>Total Fund:</b> ${db['total_fund_value']:.2f}\n"
            f"🎯 <b>Launch Goal:</b> ${db['target_capital']:.2f} ({db['progress_pct']}%)\n"
            f"--------------------------------\n"
            f"🏆 <b>PROP FIRM READINESS ($50k)</b>\n"
            f"📊 <b>Shadow P&L:</b> ${prop['net_pnl']:.2f}\n"
            f"🎯 <b>Target:</b> ${prop['target']:.2f} ({prop['progress_pct']}%)\n"
            f"🛡️ <b>Status:</b> {prop['status']}\n"
        )
        return text
