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
        
        try:
            from cro_risk import AlpacaExecutor
            executor = AlpacaExecutor()
            if executor.client:
                asset = executor.client.get_asset(ticker)
                if not asset.shortable:
                    return False, 99.0
                if not asset.easy_to_borrow:
                    # Hard-to-borrow assets often carry high fees
                    estimated_fee = 20.0
                else:
                    estimated_fee = 1.0
            else:
                # Simulation fallback
                estimated_fee = 2.0
        except Exception as e:
            logger.error(f"Failed to fetch borrow info for {ticker}: {e}")
            return False, 10.0

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
        if price_a == 0.0 or price_b == 0.0:
            raise ZeroDivisionError("Asset prices cannot be zero during quantity calculation.")
            
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
