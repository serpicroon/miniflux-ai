"""
Unit tests for digest lookback (previous digests pulled back from Miniflux)
"""

import unittest
from unittest.mock import MagicMock, patch

import tiktoken

from core import digest_generator, digest_handler
from core.content_helper import to_html
from core.prompt_schema import DIGEST_PROMPT_SCHEMA

_ENCODER = tiktoken.get_encoding("cl100k_base")

FEED_URL = "http://digest.local/rss/digest"
DIGEST_URL = "http://digest.local"


def _entry(title, url, content):
    return {"id": 1, "title": title, "url": url, "content": content}


def _digest_entry(day, point):
    return {
        "id": 1,
        "title": f"Evening Digest for you - 2026-09-{day:02d}",
        "url": f"{DIGEST_URL}/2026-09-{day:02d}-18-00",
        "content": f"<h4>Theme</h4><p>{point}</p>",
        "published_at": f"2026-09-{day:02d}T18:00:00+08:00",
    }


class TestLoadLookbackDigests(unittest.TestCase):
    """Tests for digest_handler._load_lookback_digests"""

    def setUp(self):
        patcher = patch.object(digest_handler.config, "digest_url", DIGEST_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(digest_handler, "FEED_URL", FEED_URL)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _client(self, entries):
        client = MagicMock()
        client.get_feeds.return_value = [{"id": 7, "feed_url": FEED_URL}]
        client.get_feed_entries.return_value = {"entries": entries}
        return client

    def test_disabled_lookback_skips_api(self):
        """lookback=0 returns [] without calling Miniflux"""
        client = self._client([])
        with (
            patch.object(digest_handler.config, "digest_lookback", 0),
            patch.object(digest_handler, "get_miniflux_client", return_value=client),
        ):
            self.assertEqual(digest_handler._load_lookback_digests(), [])
        client.get_feed_entries.assert_not_called()

    def test_missing_feed_returns_empty(self):
        """No digest feed in Miniflux returns []"""
        client = MagicMock()
        client.get_feeds.return_value = [{"id": 1, "feed_url": "http://other/rss"}]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(digest_handler, "get_miniflux_client", return_value=client),
        ):
            self.assertEqual(digest_handler._load_lookback_digests(), [])

    def test_contentless_entries_skipped_and_capped_to_lookback(self):
        """Entries without content (e.g. welcome) excluded, newest N kept"""
        entries = [
            _digest_entry(8, "Newest point"),
            _digest_entry(7, "Middle point"),
            _digest_entry(6, "Oldest point"),
            _entry("Welcome to Test Digest", DIGEST_URL, ""),
        ]
        with (
            patch.object(digest_handler.config, "digest_lookback", 2),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 2)
        labels = [label for label, _ in result]
        self.assertIn("2026-09-08T18:00:00+08:00", labels)
        self.assertIn("2026-09-07T18:00:00+08:00", labels)
        for _, content in result:
            self.assertNotIn("<h4>", content)
            self.assertNotIn("Welcome", content)
        self.assertIn("Newest point", result[0][1])

    def test_entry_with_digest_url_kept_when_it_has_content(self):
        """URL alone never excludes; only empty content skips"""
        entries = [
            _entry(
                "Evening Digest for you - 2026-09-08",
                DIGEST_URL,
                "<h4>Theme</h4><p>Kept point</p>",
            )
        ]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertIn("Kept point", result[0][1])

    def test_label_falls_back_to_title(self):
        """Entries without published_at are labeled by title"""
        entries = [
            _entry("Evening Digest for you - 2026-09-08", f"{DIGEST_URL}/x", "<p>P</p>")
        ]
        with (
            patch.object(digest_handler.config, "digest_lookback", 3),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "Evening Digest for you - 2026-09-08")

    def test_api_failure_degrades_to_empty(self):
        """Miniflux errors never block digest generation"""
        client = MagicMock()
        client.get_feeds.side_effect = RuntimeError("connection refused")
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(digest_handler, "get_miniflux_client", return_value=client),
        ):
            self.assertEqual(digest_handler._load_lookback_digests(), [])

    def test_long_content_truncated(self):
        """Content over the token limit is truncated with a marker"""
        long_point = " ".join(f"word{i}" for i in range(100))
        entries = [_digest_entry(8, long_point)]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(digest_handler.config, "digest_lookback_tokens", 10),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0][1].endswith("…[truncated]"))
        body = result[0][1][: -len("…[truncated]")]
        self.assertLessEqual(len(_ENCODER.encode(body)), 10)

    def test_zero_limit_disables_truncation(self):
        """lookback_tokens=0 keeps full content"""
        long_point = " ".join(f"word{i}" for i in range(100))
        entries = [_digest_entry(8, long_point)]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(digest_handler.config, "digest_lookback_tokens", 0),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0][1].endswith("…[truncated]"))
        self.assertIn("word99", result[0][1])

    def test_greeting_stripped_via_roundtrip(self):
        """Greeting essay is dropped using the shared body marker"""
        full_markdown = (
            "Good morning essay\n\n" f"{digest_generator.DIGEST_HEADING}\n\n" "Body point here"
        )
        entries = [
            {
                "id": 1,
                "title": "Evening Digest",
                "url": f"{DIGEST_URL}/2026-09-08-18-00",
                "content": to_html(full_markdown),
                "published_at": "2026-09-08T18:00:00+08:00",
            }
        ]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertIn("Body point here", result[0][1])
        self.assertNotIn("Good morning essay", result[0][1])

    def test_legacy_content_without_marker_kept_whole(self):
        """Content without the body marker falls back to full text"""
        entries = [_digest_entry(8, "Legacy point")]
        with (
            patch.object(digest_handler.config, "digest_lookback", 1),
            patch.object(
                digest_handler,
                "get_miniflux_client",
                return_value=self._client(entries),
            ),
        ):
            result = digest_handler._load_lookback_digests()

        self.assertEqual(len(result), 1)
        self.assertIn("Legacy point", result[0][1])


class TestGenerateSummaryLookback(unittest.TestCase):
    """Tests for lookback injection in digest_generator._generate_summary"""

    def setUp(self):
        patcher = patch.object(
            digest_generator.config, "digest_prompts", {"summary": "Summarize."}
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(digest_generator.config, "digest_entry_url", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _summaries(self):
        return [{"id": 101, "content": "Entry summary"}]

    def test_lookback_injected_after_summary_prompt(self):
        """Lookback data is appended after the user summary prompt"""
        lookback = [("2026-09-07T18:00:00+08:00", "Old point")]
        with patch.object(
            digest_generator, "chat_completion", return_value="digest"
        ) as chat:
            digest_generator._generate_summary(self._summaries(), lookback)

        prompts = chat.call_args[0][0]
        roles_contents = [content for _, content in prompts]
        self.assertEqual(len(prompts), 6)
        self.assertEqual(roles_contents[2], "Summarize.")
        self.assertTrue(roles_contents[3].startswith("<lookback>"))
        self.assertIn("provided as context", roles_contents[3])
        self.assertIn("Old point", roles_contents[3])

    def test_no_lookback_no_injection(self):
        """Empty/None lookback keeps the original 5-message prompt"""
        for lookback in (None, []):
            with (
                self.subTest(lookback=lookback),
                patch.object(
                    digest_generator, "chat_completion", return_value="digest"
                ) as chat,
            ):
                digest_generator._generate_summary(self._summaries(), lookback)

            prompts = chat.call_args[0][0]
            self.assertEqual(len(prompts), 5)
            combined = "\n".join(content for _, content in prompts)
            self.assertNotIn("<lookback>", combined)


class TestRenderLookback(unittest.TestCase):
    """Tests for DigestPromptSchema.render_lookback"""

    def test_renders_dated_block(self):
        """Renders intro plus one tagged section per digest in the block"""
        rendered = DIGEST_PROMPT_SCHEMA.render_lookback(
            [("2026-09-07", "First"), ("2026-09-06", "Second")]
        )
        self.assertTrue(rendered.startswith("<lookback>"))
        self.assertTrue(rendered.endswith("</lookback>"))
        self.assertIn("provided as context", rendered)
        self.assertIn(
            '<lookback_digest date="2026-09-07">\nFirst\n</lookback_digest>',
            rendered,
        )
        self.assertIn(
            '<lookback_digest date="2026-09-06">\nSecond\n</lookback_digest>',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
