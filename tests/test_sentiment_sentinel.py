import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patching LLM and NewsClient to avoid real API calls during import and init
with patch('sentiment_sentinel.ChatGoogleGenerativeAI'):
    with patch('sentiment_sentinel.NewsClient'):
        with patch('sentiment_sentinel.NewsDataStream'):
            from sentiment_sentinel import SentimentAnalyzer

class TestSentimentSentinel(unittest.TestCase):
    def setUp(self):
        # Patching during setup to ensure clean instances per test
        with patch('sentiment_sentinel.ChatGoogleGenerativeAI') as mock_llm:
            with patch('sentiment_sentinel.NewsClient'):
                with patch('sentiment_sentinel.NewsDataStream'):
                    self.analyzer = SentimentAnalyzer()
                    self.mock_llm_instance = mock_llm.return_value
                    self.analyzer.llm = self.mock_llm_instance

    def test_analyze_anonymous_votes_empty(self):
        votes = self.analyzer.analyze_anonymous_votes({})
        self.assertEqual(votes, [])

    def test_analyze_anonymous_votes_retail_contrarian_sell(self):
        data_sources = {
            "retail": {"status": "ONLINE", "long_pct": 0.80, "short_pct": 0.20}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources)
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["source"], "Retail_Contrarian")
        self.assertEqual(votes[0]["bias"], -1.0) # > 70% long -> contrarian sell
        self.assertEqual(votes[0]["weight"], 1.0)

    def test_analyze_anonymous_votes_retail_contrarian_buy(self):
        data_sources = {
            "retail": {"status": "ONLINE", "long_pct": 0.20, "short_pct": 0.80}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources)
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["source"], "Retail_Contrarian")
        self.assertEqual(votes[0]["bias"], 1.0) # > 70% short -> contrarian buy
        self.assertEqual(votes[0]["weight"], 1.0)

    def test_analyze_anonymous_votes_retail_neutral(self):
        data_sources = {
            "retail": {"status": "ONLINE", "long_pct": 0.50, "short_pct": 0.50}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources)
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["source"], "Retail_Contrarian")
        self.assertEqual(votes[0]["bias"], 0.0)
        self.assertEqual(votes[0]["weight"], 1.0)

    def test_analyze_anonymous_votes_retail_offline(self):
        data_sources = {
            "retail": {"status": "OFFLINE", "long_pct": 0.80, "short_pct": 0.20}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources)
        self.assertEqual(votes, [])

    def test_analyze_anonymous_votes_news_bullish(self):
        data_sources = {
            "news": {"status": "ONLINE", "headlines": ["Company reports record profits", "New product a huge success"]}
        }

        # Mock LLM response
        mock_res = MagicMock()
        mock_res.content = "0.8"
        # Mock usage_metadata to avoid token tracking errors if present
        mock_res.usage_metadata = MagicMock(input_token_count=10, output_token_count=1)
        self.mock_llm_instance.invoke.return_value = mock_res

        votes = self.analyzer.analyze_anonymous_votes(data_sources)

        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["source"], "News_Gemini_Flash")
        self.assertEqual(votes[0]["bias"], 0.8)
        self.assertEqual(votes[0]["weight"], 1.2)
        self.mock_llm_instance.invoke.assert_called_once()

    def test_analyze_anonymous_votes_news_bearish(self):
        data_sources = {
            "news": {"status": "ONLINE", "headlines": ["Company goes bankrupt", "Massive layoffs announced"]}
        }

        # Mock LLM response
        mock_res = MagicMock()
        mock_res.content = "-0.9"
        mock_res.usage_metadata = MagicMock(input_token_count=10, output_token_count=1)
        self.mock_llm_instance.invoke.return_value = mock_res

        votes = self.analyzer.analyze_anonymous_votes(data_sources)

        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["source"], "News_Gemini_Flash")
        self.assertEqual(votes[0]["bias"], -0.9)
        self.assertEqual(votes[0]["weight"], 1.2)

    def test_analyze_anonymous_votes_news_offline_or_empty(self):
        data_sources_offline = {
            "news": {"status": "OFFLINE", "headlines": ["Some headline"]}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources_offline)
        self.assertEqual(votes, [])

        data_sources_empty = {
            "news": {"status": "ONLINE", "headlines": []}
        }
        votes = self.analyzer.analyze_anonymous_votes(data_sources_empty)
        self.assertEqual(votes, [])

    def test_analyze_anonymous_votes_combined(self):
        data_sources = {
            "retail": {"status": "ONLINE", "long_pct": 0.80, "short_pct": 0.20}, # Sell (-1.0)
            "news": {"status": "ONLINE", "headlines": ["Good news!"]}
        }

        mock_res = MagicMock()
        mock_res.content = "0.5" # Buy (0.5)
        mock_res.usage_metadata = MagicMock(input_token_count=5, output_token_count=1)
        self.mock_llm_instance.invoke.return_value = mock_res

        votes = self.analyzer.analyze_anonymous_votes(data_sources)
        self.assertEqual(len(votes), 2)

        # Check retail
        retail_vote = next(v for v in votes if v["source"] == "Retail_Contrarian")
        self.assertEqual(retail_vote["bias"], -1.0)

        # Check news
        news_vote = next(v for v in votes if v["source"] == "News_Gemini_Flash")
        self.assertEqual(news_vote["bias"], 0.5)

if __name__ == '__main__':
    unittest.main()
