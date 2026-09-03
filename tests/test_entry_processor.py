"""
Unit tests for core.entry_processor module using unittest
"""

import unittest
from unittest.mock import Mock, patch

from common.exceptions import LLMResponseError
from common.models import Agent
from core import entry_processor
from core.entry_processor import (
    _apply_agent_template,
    _apply_entry_action,
    _execute_agent,
    _process_with_single_agent,
    process_entry,
)


def make_agent(**kwargs) -> Agent:
    defaults = dict(
        prompt="Summarize the entry",
        template="<div>{content}</div>",
        allow_rules=[],
        deny_rules=[],
        allow_actions=[],
    )
    defaults.update(kwargs)
    return Agent(**defaults)


def make_entry(**kwargs) -> dict:
    entry = {
        "id": 12345,
        "title": "Test Title",
        "url": "https://example.com/test",
        "author": "Tester",
        "content": "<p>Original body</p>",
    }
    entry.update(kwargs)
    return entry


class TestExecuteAgent(unittest.TestCase):
    """Tests for _execute_agent function"""

    @patch("core.entry_processor.chat_completion")
    def test_returns_chat_response(self, mock_chat):
        mock_chat.return_value = "<p>Summary</p>"
        agent = make_agent()
        entry = make_entry()

        result = _execute_agent("summary", agent, entry)

        self.assertEqual(result, "<p>Summary</p>")
        mock_chat.assert_called_once()

    @patch("core.entry_processor.chat_completion")
    def test_prompt_structure_without_actions(self, mock_chat):
        mock_chat.return_value = "ok"
        agent = make_agent(prompt="Do the thing")
        entry = make_entry()

        _execute_agent("summary", agent, entry)
        prompts = mock_chat.call_args[0][0]

        self.assertEqual(len(prompts), 3)
        roles = [r for r, _ in prompts]
        self.assertEqual(roles, ["user", "user", "user"])
        # Second prompt is the rendered entry data
        self.assertIn(entry["title"], prompts[1][1])
        self.assertIn("Original body", prompts[1][1])
        # Third prompt is the agent's task instruction
        self.assertEqual(prompts[2][1], "Do the thing")

    @patch("core.entry_processor.chat_completion")
    def test_prompt_structure_with_actions(self, mock_chat):
        mock_chat.return_value = "ok"
        agent = make_agent(allow_actions=["read"])
        entry = make_entry()

        _execute_agent("summary", agent, entry)
        prompts = mock_chat.call_args[0][0]

        self.assertEqual(len(prompts), 4)
        self.assertIn("<action_instructions>", prompts[3][1])
        self.assertIn("- read: mark the entry as read", prompts[3][1])

    @patch("core.entry_processor.chat_completion")
    def test_no_action_block_without_allow_actions(self, mock_chat):
        mock_chat.return_value = "ok"
        _execute_agent("summary", make_agent(), make_entry())
        prompts = mock_chat.call_args[0][0]

        self.assertEqual(len(prompts), 3)
        self.assertNotIn("<action_instructions>", prompts[-1][1])


class TestProcessWithSingleAgent(unittest.TestCase):
    """Tests for _process_with_single_agent function"""

    def setUp(self):
        cfg = patch("core.entry_processor.config")
        self.mock_config = cfg.start()
        self.mock_config.digest_schedule = None
        self.addCleanup(cfg.stop)

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_filtered_by_rules(self, mock_rules, mock_chat):
        mock_rules.return_value = False

        result = _process_with_single_agent("summary", make_agent(), make_entry())

        self.assertTrue(result.is_filtered)
        mock_chat.assert_not_called()

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_success_with_action(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.return_value = "**Summary text**\n<action>read</action>"
        agent = make_agent(allow_actions=["read"])

        result = _process_with_single_agent("summary", agent, make_entry())

        self.assertTrue(result.is_success)
        self.assertEqual(result.action, "read")
        self.assertNotIn("<action>", result.content)
        self.assertIn("<div>", result.content)
        self.assertIn("<strong>Summary text</strong>", result.content)

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_invalid_action_ignored(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.return_value = "**Summary text**\n<action>save</action>"
        agent = make_agent(allow_actions=["read"])

        result = _process_with_single_agent("summary", agent, make_entry())

        self.assertTrue(result.is_success)
        self.assertIsNone(result.action)
        self.assertNotIn("<action>", result.content)

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_no_action_tag(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.return_value = "**Summary text**"
        agent = make_agent(allow_actions=["read"])

        result = _process_with_single_agent("summary", agent, make_entry())

        self.assertTrue(result.is_success)
        self.assertIsNone(result.action)

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_action_only_response(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.return_value = "<action>read</action>"
        agent = make_agent(allow_actions=["read"])

        result = _process_with_single_agent("summary", agent, make_entry())

        self.assertTrue(result.is_success)
        self.assertEqual(result.action, "read")
        self.assertEqual(result.content, "")

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_action_agent_empty_response_is_not_error(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.return_value = ""
        agent = make_agent(allow_actions=["read"])

        result = _process_with_single_agent("summary", agent, make_entry())

        self.assertTrue(result.is_success)
        self.assertIsNone(result.action)
        self.assertEqual(result.content, "")

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_llm_error(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.side_effect = LLMResponseError("boom")

        result = _process_with_single_agent("summary", make_agent(), make_entry())

        self.assertTrue(result.is_error)
        self.assertIn("boom", result.error_message)

    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    def test_generic_error(self, mock_rules, mock_chat):
        mock_rules.return_value = True
        mock_chat.side_effect = RuntimeError("unexpected")

        result = _process_with_single_agent("summary", make_agent(), make_entry())

        self.assertTrue(result.is_error)


class TestApplyAgentTemplate(unittest.TestCase):
    """Tests for _apply_agent_template function"""

    def test_with_template(self):
        agent = make_agent(template="<article>{content}</article>")
        result = _apply_agent_template(agent, "**Summary text**")

        self.assertIn("<article>", result)
        self.assertIn("</article>", result)
        self.assertIn("<strong>Summary text</strong>", result)

    def test_without_template(self):
        agent = make_agent(template="")
        result = _apply_agent_template(agent, "**Summary text**")

        self.assertIn("<strong>Summary text</strong>", result)

    def test_empty_content_unwrapped(self):
        agent = make_agent(template="<article>{content}</article>")
        result = _apply_agent_template(agent, "")

        self.assertEqual(result, "")


class TestApplyEntryAction(unittest.TestCase):
    """Tests for _apply_entry_action function"""

    @staticmethod
    def _success(action):
        from common.models import AgentResult

        return AgentResult.success("content", action=action)

    def test_read_action(self):
        mock_client = Mock()
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            _apply_entry_action(make_entry(), {"summary": self._success("read")})

        mock_client.update_entries.assert_called_once_with([12345], "read")
        mock_client.toggle_bookmark.assert_not_called()

    def test_star_action(self):
        mock_client = Mock()
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            _apply_entry_action(make_entry(), {"summary": self._success("star")})

        mock_client.toggle_bookmark.assert_called_once_with(12345)
        mock_client.save_entry.assert_not_called()

    def test_save_action(self):
        mock_client = Mock()
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            _apply_entry_action(make_entry(), {"summary": self._success("save")})

        mock_client.save_entry.assert_called_once_with(12345)

    def test_first_action_wins(self):
        mock_client = Mock()
        results = {
            "summary": self._success("read"),
            "translate": self._success("star"),
        }
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            _apply_entry_action(make_entry(), results)

        mock_client.update_entries.assert_called_once_with([12345], "read")
        mock_client.toggle_bookmark.assert_not_called()

    def test_no_action_no_client_call(self):
        mock_client = Mock()
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            _apply_entry_action(make_entry(), {"summary": self._success(None)})

        mock_client.update_entries.assert_not_called()
        mock_client.toggle_bookmark.assert_not_called()
        mock_client.save_entry.assert_not_called()

    def test_action_failure_degrades_to_warning(self):
        mock_client = Mock()
        mock_client.update_entries.side_effect = RuntimeError("api down")
        with patch(
            "core.entry_processor.get_miniflux_client", return_value=mock_client
        ):
            # Should not raise despite the failure
            _apply_entry_action(make_entry(), {"summary": self._success("read")})


class TestProcessEntry(unittest.TestCase):
    """Tests for process_entry function (action integration)"""

    def setUp(self):
        entry_processor._ENTRY_CACHE.clear()

    @patch("core.entry_processor.get_miniflux_client")
    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    @patch("core.entry_processor.config")
    def test_content_update_before_action(
        self, mock_config, mock_rules, mock_chat, mock_client_factory
    ):
        mock_config.agents = {"summary": make_agent(allow_actions=["read"])}
        mock_config.digest_schedule = None
        mock_rules.return_value = True
        mock_chat.return_value = "**Summary text**\n<action>read</action>"
        mock_client = Mock()
        mock_client_factory.return_value = mock_client

        results = process_entry(make_entry())

        self.assertEqual(results["summary"].action, "read")
        # Content updated first: entry content contains summary + marker
        args = mock_client.update_entry.call_args
        self.assertEqual(
            args.kwargs["content"].strip().endswith("<p>Original body</p>"), True
        )
        self.assertIn("Summary text", args.kwargs["content"])
        # Action applied after content update
        mock_client.update_entries.assert_called_once_with([12345], "read")

    @patch("core.entry_processor.get_miniflux_client")
    @patch("core.entry_processor.chat_completion")
    @patch("core.entry_processor.match_rules")
    @patch("core.entry_processor.config")
    def test_no_action_applied_for_plain_response(
        self, mock_config, mock_rules, mock_chat, mock_client_factory
    ):
        mock_config.agents = {"summary": make_agent(allow_actions=["read"])}
        mock_config.digest_schedule = None
        mock_rules.return_value = True
        mock_chat.return_value = "**Summary text**"
        mock_client = Mock()
        mock_client_factory.return_value = mock_client

        results = process_entry(make_entry())

        self.assertIsNone(results["summary"].action)
        mock_client.update_entries.assert_not_called()


if __name__ == "__main__":
    unittest.main()
