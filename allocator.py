import logging
from config_loader import config

logger = logging.getLogger("hedged_sizer")

class HedgedPositionSizer:
    """
    Calculates Beta-Neutral quantities for Paired Arbitrage.
    Ensures that for every $1 of Asset A, we have -$Beta of Asset B.
    """
    @staticmethod
    def get_borrow_fee_veto(ticker, side):
        """
        Vetoes trades if the asset is Hard-To-Borrow (HTB) with fees > limit.
        On Alpaca, HTB stocks can have 20-50% APR fees.
        """
        if side != "SHORT": return True, 0.0
        
        # In a professional setup, use Alpaca's Asset API to check 'easy_to_borrow'
        # For this 'Zero-Cost' researcher, we use a conservative limit.
        max_fee = config.get("trading.max_borrow_fee_apr", 5.0)
        
        # Placeholder for real-time borrow fee check
        # High-Beta Russell stocks are usually HTB. Large-Caps are usually ETB (Easy).
        is_htb = False 
        estimated_fee = 0.5 if not is_htb else 25.0
        
        if estimated_fee > max_fee:
            return False, estimated_fee
        return True, estimated_fee

    @staticmethod
    def get_hedged_quantities(risk_usd, price_a, price_b, beta, direction_a):
        """
        Returns (qty_a, qty_b) to achieve a beta-neutral position.
        direction_a: "LONG" or "SHORT" for Asset A. 
        Asset B will always be the opposite.
        """
        # Small Account Floor check
        if risk_usd < 5.0: risk_usd = 5.0 
        
        # We risk the 'risk_usd' amount on the PRIMARY asset (Asset A)
        # Quantity A is simple
        qty_a = risk_usd / price_a
        
        # Quantity B must neutralize the Beta of A
        # Notional A * Beta = Notional B
        # (qty_a * price_a) * beta = (qty_b * price_b)
        notional_a = qty_a * price_a
        notional_b = notional_a * abs(beta)
        qty_b = notional_b / price_b
        
        # Determine Sides
        side_a = "LONG" if direction_a == "LONG" else "SHORT"
        side_b = "SHORT" if direction_a == "LONG" else "LONG"
        
        return {
            "asset_a": {"qty": round(qty_a, 4), "side": side_a},
            "asset_b": {"qty": round(qty_b, 4), "side": side_b},
            "total_notional": round(notional_a + notional_b, 2)
        }
