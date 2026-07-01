import logging
from geometry import detect_liquidity_sweeps, detect_absorption, calculate_volume_profile
from pairs_trading_scanner import PairsScanner

logger = logging.getLogger("strategy_library")

class AlphaStrategy:
    def __init__(self, name):
        self.name = name

class ContrarianHunter(AlphaStrategy):
    """Fades retail crowds by identifying traps."""
    def get_signal(self, df):
        from contrarian_module import ContrarianTrapHunter
        hunter = ContrarianTrapHunter()
        traps = hunter.identify_trap_scenarios(df)
        if traps:
            return {"direction": traps[0]['institutional_intent'], "confidence": 0.8}
        return None

class StatArbSpecialist(AlphaStrategy):
    """Trades mean reversion of cointegrated pairs."""
    def get_signal(self, df, pair_df=None):
        if pair_df is None: return None
        scanner = PairsScanner()
        z = scanner.calculate_zscore(df['Close'], pair_df['Close'])
        if z > 2.0: return {"direction": "SHORT_SPREAD", "confidence": 0.75}
        if z < -2.0: return {"direction": "LONG_SPREAD", "confidence": 0.75}
        return None

class TrendFollower(AlphaStrategy):
    """Simple momentum continuity strategy."""
    def get_signal(self, df):
        latest = df.iloc[-1]
        if latest['ADX_14'] > 25:
            if latest['Close'] > latest['EMA_20']:
                return {"direction": "LONG", "confidence": 0.6}
            if latest['Close'] < latest['EMA_20']:
                return {"direction": "SHORT", "confidence": 0.6}
        return None

STRATEGY_MAP = {
    "CONTRARIAN_TRAP": ContrarianHunter("CONTRARIAN_TRAP"),
    "STAT_ARB": StatArbSpecialist("STAT_ARB"),
    "TREND_FOLLOW": TrendFollower("TREND_FOLLOW")
}
