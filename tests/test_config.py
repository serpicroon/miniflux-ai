"""
Unit tests for common.config module
"""

import contextlib
import os
import tempfile
import threading
import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from common.config import Config
from common.models import Agent, Duration


class TestDuration(unittest.TestCase):
    """Tests for Duration value object parsing"""

    def test_parse_valid(self):
        """Test parsing valid duration strings"""
        cases = {
            "5m": (5, "m", 300),
            "2h": (2, "h", 7200),
            "3d": (3, "d", 3 * 86400),
            "1w": (1, "w", 604800),
        }
        for value, (amount, unit, seconds) in cases.items():
            with self.subTest(value=value):
                duration = Duration.parse(value)
                self.assertEqual(duration.amount, amount)
                self.assertEqual(duration.unit, unit)
                self.assertEqual(duration.seconds, seconds)

    def test_parse_empty_or_none(self):
        """Test that empty/None values yield None"""
        self.assertIsNone(Duration.parse(None))
        self.assertIsNone(Duration.parse(""))
        self.assertIsNone(Duration.parse("   "))

    def test_parse_whitespace(self):
        """Test parsing with surrounding whitespace"""
        duration = Duration.parse("  5m  ")
        self.assertEqual(duration, Duration(amount=5, unit="m"))

    def test_parse_invalid_format(self):
        """Test that malformed values raise ValueError"""
        for value in ("5", "m", "5mm", "5-", "abc", "1.5h"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Duration.parse(value)

    def test_parse_unsupported_unit(self):
        """Test that unknown units raise ValueError"""
        with self.assertRaises(ValueError):
            Duration.parse("5x")

    def test_parse_allowed_units(self):
        """Test that forbidden units raise ValueError while allowed pass"""
        # Minutes are fine when allowed
        self.assertIsNotNone(Duration.parse("5m", allowed_units=("m", "h")))
        # Minutes are rejected when not in the whitelist
        with self.assertRaises(ValueError):
            Duration.parse("5m", allowed_units=("d", "w"))

    def test_negative_amount_rejected(self):
        """Test that negative amounts raise ValueError"""
        with self.assertRaises(ValueError):
            Duration(amount=-1, unit="m")

    def test_zero_amount_rejected(self):
        """Test that zero amounts raise ValueError"""
        with self.assertRaises(ValueError):
            Duration.parse("0m")
        with self.assertRaises(ValueError):
            Duration.parse("0d")
        with self.assertRaises(ValueError):
            Duration(amount=0, unit="m")

    def test_parse_non_string_rejected(self):
        """Test that non-string values raise ValueError, not AttributeError"""
        for value in (5, 0, True, ["5m"], {"amount": 5}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Duration.parse(value)

    def test_str_roundtrip(self):
        """Test the compact string representation"""
        duration = Duration(amount=3, unit="w")
        self.assertEqual(str(duration), "3w")


class TestConfigLoading(unittest.TestCase):
    """Tests for configuration loading"""

    def setUp(self):
        """Create temporary config file for testing"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            self.temp_file_path = f.name

    def tearDown(self):
        """Clean up temporary file"""
        with contextlib.suppress(BaseException):
            os.unlink(self.temp_file_path)

    def _create_config(self, config_content):
        """Helper to create a config file and return Config instance"""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        with patch(
            "builtins.open", return_value=open(self.temp_file_path, encoding="utf8")
        ):
            return Config()

    def test_load_basic_config(self):
        """Test loading basic configuration"""
        config_content = """
log_level: DEBUG
miniflux:
  base_url: http://miniflux.local
  api_key: test_key
  webhook_secret: test_secret
llm:
  base_url: http://llm.local
  api_key: llm_key
  model: gpt-4
  timeout: 30
  max_workers: 8
  RPM: 500
scheduler:
  interval: 5m
  entry_window: 3w
  entry_limit: 50
digest:
  name: Test Digest
  url: http://digest.local
  entry_url: http://entry.local
  schedule: "0 8 * * *"
  prompts:
    - test prompt
agents: {}
"""
        config = self._create_config(config_content)

        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.scheduler_interval.amount, 5)
        self.assertEqual(config.scheduler_interval.unit, "m")
        self.assertEqual(config.scheduler_interval.seconds, 300)
        self.assertEqual(config.scheduler_entry_window.amount, 3)
        self.assertEqual(config.scheduler_entry_window.unit, "w")
        self.assertEqual(config.scheduler_entry_window.seconds, 3 * 7 * 86400)
        self.assertEqual(config.scheduler_entry_limit, 50)
        self.assertEqual(config.miniflux_base_url, "http://miniflux.local")
        self.assertEqual(config.miniflux_api_key, "test_key")
        self.assertEqual(config.miniflux_webhook_secret, "test_secret")
        self.assertEqual(config.llm_base_url, "http://llm.local")
        self.assertEqual(config.llm_api_key, "llm_key")
        self.assertEqual(config.llm_model, "gpt-4")
        self.assertEqual(config.llm_timeout, 30)
        self.assertEqual(config.llm_max_workers, 8)
        self.assertEqual(config.llm_RPM, 500)
        self.assertEqual(config.digest_name, "Test Digest")
        self.assertEqual(config.digest_url, "http://digest.local")
        self.assertEqual(config.digest_entry_url, "http://entry.local")
        self.assertEqual(config.digest_schedule, "0 8 * * *")
        self.assertEqual(config.digest_prompts, ["test prompt"])

    def test_load_default_values(self):
        """Test that default values are used when not specified"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents: {}
"""
        config = self._create_config(config_content)

        self.assertEqual(config.log_level, "INFO")  # Default
        self.assertIsNone(config.scheduler_interval)  # Default: no interval override
        self.assertIsNone(config.scheduler_entry_window)  # Default: no window
        self.assertEqual(config.scheduler_entry_limit, 0)  # Default: unlimited
        self.assertEqual(config.llm_timeout, 60)  # Default
        self.assertEqual(config.llm_max_workers, 4)  # Default
        self.assertEqual(config.llm_RPM, 1000)  # Default
        self.assertEqual(config.llm_prompt_processing, "strict")  # Default

    def test_load_bare_scheduler_section(self):
        """Test that a bare 'scheduler:' key falls back to defaults"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
scheduler:
agents: {}
"""
        config = self._create_config(config_content)

        self.assertIsNone(config.scheduler_interval)
        self.assertIsNone(config.scheduler_entry_window)
        self.assertEqual(config.scheduler_entry_limit, 0)

    def test_load_invalid_entry_limit(self):
        """Test that non-integer or negative entry_limit raises ValueError"""
        for entry_limit in ("-1", "-5", "unlimited", "1.5", "true"):
            with self.subTest(entry_limit=entry_limit):
                config_content = f"""
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
scheduler:
  entry_limit: {entry_limit}
agents: {{}}
"""
                with self.assertRaises(ValueError):
                    self._create_config(config_content)

    def test_load_invalid_scheduler_durations(self):
        """Test that bad scheduler durations raise ValueError"""
        cases = [
            "interval: 5d",
            "entry_window: 5m",
            "interval: 5",
            "interval: 0m",
            "entry_window: 0d",
        ]
        for snippet in cases:
            with self.subTest(snippet=snippet):
                config_content = f"""
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
scheduler:
  {snippet}
agents: {{}}
"""
                with self.assertRaises(ValueError):
                    self._create_config(config_content)

    def test_load_prompt_processing_explicit(self):
        """Test explicit prompt_processing config values"""
        for mode in ("none", "strict", "single"):
            with self.subTest(mode=mode):
                config_content = f"""
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
  prompt_processing: {mode}
agents: {{}}
"""
                config = self._create_config(config_content)
                self.assertEqual(config.llm_prompt_processing, mode)

    def test_load_agents_basic(self):
        """Test loading basic agent configuration"""
        config_content = r"""
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize this article"
    template: '<div>{content}</div>'
    allow_rules:
      - EntryTitle=(?i)python
      - FeedSiteURL=.*github\.com.*
    deny_rules:
      - EntryTitle=(?i)spam
"""
        config = self._create_config(config_content)

        self.assertIn("summary", config.agents)
        agent = config.agents["summary"]

        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.prompt, "Summarize this article")
        self.assertEqual(agent.template, "<div>{content}</div>")
        self.assertEqual(len(agent.allow_rules), 2)
        self.assertEqual(agent.allow_rules[0], "EntryTitle=(?i)python")
        self.assertEqual(agent.allow_rules[1], "FeedSiteURL=.*github\\.com.*")
        self.assertEqual(len(agent.deny_rules), 1)
        self.assertEqual(agent.deny_rules[0], "EntryTitle=(?i)spam")

    def test_load_agents_empty_rules(self):
        """Test loading agent with empty rules"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
"""
        config = self._create_config(config_content)

        agent = config.agents["summary"]
        self.assertEqual(agent.allow_rules, [])
        self.assertEqual(agent.deny_rules, [])

    def test_load_multiple_agents(self):
        """Test loading multiple agents"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
  translate:
    prompt: "Translate to English"
    template: '<p>{content}</p>'
  analyze:
    prompt: "Analyze sentiment"
    template: '<span>{content}</span>'
"""
        config = self._create_config(config_content)

        self.assertEqual(len(config.agents), 3)
        self.assertIn("summary", config.agents)
        self.assertIn("translate", config.agents)
        self.assertIn("analyze", config.agents)

    def test_load_agents_skip_invalid(self):
        """Test that invalid agent configs are skipped"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
  invalid_agent: "not a dict"
  another: 123
"""
        config = self._create_config(config_content)

        # Only valid agent should be loaded
        self.assertEqual(len(config.agents), 1)
        self.assertIn("summary", config.agents)
        self.assertNotIn("invalid_agent", config.agents)
        self.assertNotIn("another", config.agents)


class TestHandleUnreadEntriesBudget(unittest.TestCase):
    """Tests for the per-run entry_limit budget in handle_unread_entries"""

    def _run_with_pool(self, entry_limit, pool_size, short_first_page=None):
        """Run handle_unread_entries against a fake pool; return (fetches, done)"""
        import core.entry_handler as handler

        pool = [{"id": i} for i in range(pool_size)]
        fetch_calls = []
        done = []

        def fake_fetch(offset, limit):
            fetch_calls.append((offset, limit))
            entries = pool[offset : offset + limit]
            if short_first_page is not None and len(fetch_calls) == 1:
                entries = entries[:short_first_page]
            return pool_size, entries

        with (
            patch.object(
                handler,
                "config",
                SimpleNamespace(scheduler_entry_limit=entry_limit),
            ),
            patch.object(handler, "_fetch_entries_page", side_effect=fake_fetch),
            patch.object(
                handler,
                "process_entries_concurrently",
                side_effect=lambda entries: done.extend(entries),
            ),
            patch.object(handler, "shutdown_event", threading.Event()),
        ):
            handler.handle_unread_entries()
        return fetch_calls, done

    def test_unlimited_paginates_to_total(self):
        """entry_limit=0 fetches full pages until offset reaches total"""
        fetch_calls, done = self._run_with_pool(0, 250)

        self.assertEqual([limit for _, limit in fetch_calls], [100, 100, 100])
        self.assertEqual([offset for offset, _ in fetch_calls], [0, 100, 200])
        self.assertEqual(len(done), 250)

    def test_limit_caps_fetches_and_processed(self):
        """entry_limit folds into each page size and stops the run at budget"""
        fetch_calls, done = self._run_with_pool(150, 1000)

        self.assertEqual(fetch_calls, [(0, 100), (100, 50)])
        self.assertEqual(len(done), 150)

    def test_limit_smaller_than_one_page(self):
        """entry_limit below PAGE_SIZE issues a single trimmed fetch"""
        fetch_calls, done = self._run_with_pool(50, 1000)

        self.assertEqual(fetch_calls, [(0, 50)])
        self.assertEqual(len(done), 50)

    def test_short_page_advances_by_actual_count(self):
        """offset advances by entries received, not by requested limit"""
        fetch_calls, done = self._run_with_pool(0, 250, short_first_page=30)

        self.assertEqual(fetch_calls[1][0], 30)
        self.assertEqual(len(done), 250)


class TestConfigCompatibilityValidation(unittest.TestCase):
    """Tests for configuration compatibility validation"""

    def setUp(self):
        """Create temporary config file for testing"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            self.temp_file_path = f.name

    def tearDown(self):
        """Clean up temporary file"""
        with contextlib.suppress(BaseException):
            os.unlink(self.temp_file_path)

    def _create_config_expect_exit(self, config_content, expected_output_contains):
        """Helper to test configs that should trigger sys.exit()"""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        # Capture stdout
        captured_output = StringIO()

        with (
            patch(
                "builtins.open", return_value=open(self.temp_file_path, encoding="utf8")
            ),
            patch("sys.stdout", captured_output),
            self.assertRaises(SystemExit) as cm,
        ):
            Config()

        self.assertEqual(cm.exception.code, 1)
        output = captured_output.getvalue()

        # Check that all expected strings are in output
        for expected in expected_output_contains:
            self.assertIn(
                expected, output, f"Expected '{expected}' in output:\n{output}"
            )

        return output

    def test_detect_deprecated_allow_list(self):
        """Test detection of deprecated allow_list field"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    allow_list:
      - "*github.com*"
"""
        self._create_config_expect_exit(
            config_content,
            [
                "Config Incompatibility Detected",
                "deprecated fields",
                "summary",
                "allow_list",
                "github.com/serpicroon/miniflux-ai",
            ],
        )

    def test_detect_deprecated_deny_list(self):
        """Test detection of deprecated deny_list field"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    deny_list:
      - "*spam*"
"""
        self._create_config_expect_exit(
            config_content, ["Config Incompatibility Detected", "summary", "deny_list"]
        )

    def test_detect_deprecated_min_content_length(self):
        """Test detection of deprecated min_content_length field"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    min_content_length: 50
"""
        self._create_config_expect_exit(
            config_content,
            ["Config Incompatibility Detected", "summary", "min_content_length"],
        )

    def test_detect_deprecated_title_style_block(self):
        """Test detection of deprecated title and style_block fields"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    title: "Summary"
    style_block: "<style>...</style>"
"""
        self._create_config_expect_exit(
            config_content,
            ["Config Incompatibility Detected", "summary", "title", "style_block"],
        )

    def test_detect_multiple_deprecated_fields_single_agent(self):
        """Test detection of multiple deprecated fields in single agent"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    allow_list:
      - "*github.com*"
    deny_list:
      - "*spam*"
    min_content_length: 50
"""
        output = self._create_config_expect_exit(
            config_content,
            [
                "Config Incompatibility Detected",
                "summary",
                "allow_list",
                "deny_list",
                "min_content_length",
            ],
        )

        # Verify all three are listed together
        self.assertIn("allow_list, deny_list, min_content_length", output)

    def test_detect_multiple_agents_with_deprecated_fields(self):
        """Test detection of deprecated fields across multiple agents"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    allow_list:
      - "*github.com*"
  translate:
    prompt: "Translate"
    template: '<div>{content}</div>'
    deny_list:
      - "*spam*"
    min_content_length: 100
"""
        output = self._create_config_expect_exit(
            config_content,
            [
                "Config Incompatibility Detected",
                "summary",
                "allow_list",
                "translate",
                "deny_list",
                "min_content_length",
            ],
        )

        # Check proper formatting with newlines
        self.assertIn("  - summary (allow_list)", output)
        self.assertIn("  - translate (deny_list, min_content_length)", output)

    def test_valid_config_no_exit(self):
        """Test that valid config does not trigger exit"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  summary:
    prompt: "Summarize"
    template: '<div>{content}</div>'
    allow_rules:
      - EntryTitle=(?i)python
    deny_rules:
      - EntryTitle=(?i)spam
"""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        with patch(
            "builtins.open", return_value=open(self.temp_file_path, encoding="utf8")
        ):
            # Should not raise SystemExit
            config = Config()
            self.assertIsNotNone(config)
            self.assertIn("summary", config.agents)

    def test_empty_agents_no_validation_error(self):
        """Test that empty agents section doesn't trigger validation"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents: {}
"""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        with patch(
            "builtins.open", return_value=open(self.temp_file_path, encoding="utf8")
        ):
            config = Config()
            self.assertIsNotNone(config)
            self.assertEqual(len(config.agents), 0)

    def test_no_agents_section_no_validation_error(self):
        """Test that missing agents section doesn't trigger validation"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
"""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        with patch(
            "builtins.open", return_value=open(self.temp_file_path, encoding="utf8")
        ):
            config = Config()
            self.assertIsNotNone(config)
            self.assertEqual(len(config.agents), 0)

    def test_error_message_formatting(self):
        """Test that error message is properly formatted without extra indentation"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents:
  agent1:
    prompt: "Test"
    template: '<div>{content}</div>'
    allow_list:
      - "*test*"
  agent2:
    prompt: "Test2"
    template: '<div>{content}</div>'
    deny_list:
      - "*spam*"
"""
        output = self._create_config_expect_exit(
            config_content,
            [
                "⚠️  Config Incompatibility Detected",
            ],
        )

        # Verify no excessive indentation on main message
        lines = output.split("\n")
        # First line should not start with whitespace
        self.assertFalse(
            lines[0].startswith(" "),
            f"First line should not have leading spaces: '{lines[0]}'",
        )

        # Agent list items should have exactly 2 spaces
        agent_lines = [line for line in lines if line.strip().startswith("- agent")]
        for line in agent_lines:
            # Should start with exactly 2 spaces
            self.assertTrue(
                line.startswith("  - "),
                f"Agent line should start with '  - ': '{line}'",
            )


if __name__ == "__main__":
    unittest.main()
