"""
Unit tests for core.prompt_schema module using unittest
"""

import unittest

from core.prompt_schema import ACTION_PROMPT_SCHEMA, ENTRY_PROMPT_SCHEMA


class TestEntryPromptSchema(unittest.TestCase):
    """Tests for ENTRY_PROMPT_SCHEMA"""

    def test_render_substitutes_title_and_content(self):
        """Test that render substitutes title and content"""
        rendered = ENTRY_PROMPT_SCHEMA.render(title="Hello", content="<p>Body</p>")

        self.assertIn("Hello", rendered)
        self.assertIn("<p>Body</p>", rendered)
        self.assertIn("<entry>", rendered)
        self.assertIn("<title>", rendered)
        self.assertIn("<content>", rendered)

    def test_render_keeps_braces_in_content(self):
        """Test that content braces survive rendering (safe_substitute)"""
        rendered = ENTRY_PROMPT_SCHEMA.render(title="T", content="{not_a_var}")

        self.assertIn("{not_a_var}", rendered)


class TestActionPromptSchema(unittest.TestCase):
    """Tests for ACTION_PROMPT_SCHEMA.render"""

    def test_single_action(self):
        """Test rendering with a single allowed action"""
        rendered = ACTION_PROMPT_SCHEMA.render(["read"])

        self.assertIn("<action_instructions>", rendered)
        self.assertIn("</action_instructions>", rendered)
        self.assertIn("<action>ACTION</action>", rendered)
        self.assertIn("- read: mark the entry as read", rendered)
        self.assertNotIn("- star:", rendered)
        self.assertNotIn("- save:", rendered)

    def test_multiple_actions(self):
        """Test rendering with multiple allowed actions"""
        rendered = ACTION_PROMPT_SCHEMA.render(["star", "save"])

        self.assertIn("- star: bookmark the entry (star or favorite)", rendered)
        self.assertIn("- save: send the entry to configured third-party services", rendered)
        self.assertNotIn("- read:", rendered)

    def test_contains_no_action_guidance(self):
        """Test that the block tells the model to omit the tag when no action applies"""
        rendered = ACTION_PROMPT_SCHEMA.render(["read"])

        self.assertIn(
            "If you do not take an action, do not append any action tag.", rendered
        )


if __name__ == "__main__":
    unittest.main()
