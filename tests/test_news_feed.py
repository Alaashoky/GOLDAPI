from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from goldbot.data.news_feed import NewsFeed


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class NewsFeedTests(unittest.TestCase):
    def test_returns_empty_without_api_key(self) -> None:
        feed = NewsFeed(api_key="")
        self.assertEqual(feed.fetch(), [])

    @patch("goldbot.data.news_feed.requests.get")
    def test_filters_gold_relevant_news(self, mock_get) -> None:
        mock_get.return_value = FakeResponse(
            [
                {"headline": "Fed signals rate path", "summary": "USD and inflation focus", "source": "x", "datetime": 1},
                {"headline": "Tech earnings", "summary": "Nothing macro", "source": "x", "datetime": 2},
            ]
        )
        feed = NewsFeed(api_key="token")
        items = feed.fetch()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["impact"], "high")


if __name__ == "__main__":
    unittest.main()
