import logging
from geometry import detect_liquidity_sweeps, detect_absorption, calculate_volume_delta
from utils import setup_logging

logger = setup_logging("contrarian_hunter")

class ContrarianTrapHunter:
    """
    Identifies 'Retail Crowds' and 'Institutional Traps'.
    The core Alpha generator of 2026.
    Trades AGAINST textbook SMC patterns when Absorption is detected.
    """
    
    def identify_trap_scenarios(self, df):
        """
        Analyzes for 'The Fade':
        1. Retail Signal: A textbook liquidity sweep occurred.
        2. Institutional Reality: Price was 'Absorbed' rather than rejected.
        3. Contrarian Trigger: Enter against the sweep direction.
        """
        if df is None or len(df) < 50: return []

        sweeps = detect_liquidity_sweeps(df)
        absorption = detect_absorption(df)
        
        traps = []
        
        # Scenario: BEARISH_LIQUIDITY_SWEEP (Retail sees a sell signal)
        # BUT BULLISH_ABSORPTION occurred (Institutions bought the retail sell orders)
        bear_sweeps = [s for s in sweeps if s['type'] == "BEARISH_LIQUIDITY_SWEEP"]
        bull_abs = [a for a in absorption if a['type'] == "BULLISH_ABSORPTION"]
        
        if bear_sweeps and bull_abs:
            traps.append({
                "type": "TRAP_THE_BEARS",
                "retail_bias": "SHORT",
                "institutional_intent": "LONG",
                "rationale": "Retail Short Sweep confirmed, but institutions absorbed the supply. Expect a squeeze to the upside."
            })

        # Scenario: BULLISH_LIQUIDITY_SWEEP (Retail buys the 'spring')
        # BUT BEARISH_ABSORPTION occurred (Institutions dumped into the retail demand)
        bull_sweeps = [s for s in sweeps if s['type'] == "BULLISH_LIQUIDITY_SWEEP"]
        bear_abs = [a for a in absorption if a['type'] == "BEARISH_ABSORPTION"]
        
        if bull_sweeps and bear_abs:
            traps.append({
                "type": "TRAP_THE_BULLS",
                "retail_bias": "LONG",
                "institutional_intent": "SHORT",
                "rationale": "Retail Long Spring confirmed, but institutions absorbed the demand. Expect a wash to the downside."
            })
            
        return traps

if __name__ == "__main__":
    from market_feed import get_live_market_data
    df = get_live_market_data("EURUSD=X")
    hunter = ContrarianTrapHunter()
    print(hunter.identify_trap_scenarios(df))
