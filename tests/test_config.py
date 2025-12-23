"""
Unit tests for common.config module
"""

import unittest
import sys
import tempfile
import os
from unittest.mock import patch, MagicMock
from io import StringIO

from common.config import Config
from common.models import Agent


class TestConfigLoading(unittest.TestCase):
    """Tests for configuration loading"""
    
    def setUp(self):
        """Create temporary config file for testing"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False,
            encoding='utf-8'
        )
        
    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except:
            pass
    
    def _create_config(self, config_content):
        """Helper to create a config file and return Config instance"""
        self.temp_file.write(config_content)
        self.temp_file.flush()
        
        # Mock the open call to use our temp file
        with patch('builtins.open', return_value=open(self.temp_file.name, encoding='utf8')):
            return Config()
    
    def test_load_basic_config(self):
        """Test loading basic configuration"""
        config_content = """
log_level: DEBUG
entry_since: 100
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
        
        self.assertEqual(config.log_level, 'DEBUG')
        self.assertEqual(config.entry_since, 100)
        self.assertEqual(config.miniflux_base_url, 'http://miniflux.local')
        self.assertEqual(config.miniflux_api_key, 'test_key')
        self.assertEqual(config.miniflux_webhook_secret, 'test_secret')
        self.assertEqual(config.llm_base_url, 'http://llm.local')
        self.assertEqual(config.llm_api_key, 'llm_key')
        self.assertEqual(config.llm_model, 'gpt-4')
        self.assertEqual(config.llm_timeout, 30)
        self.assertEqual(config.llm_max_workers, 8)
        self.assertEqual(config.llm_RPM, 500)
        self.assertEqual(config.digest_name, 'Test Digest')
        self.assertEqual(config.digest_url, 'http://digest.local')
        self.assertEqual(config.digest_entry_url, 'http://entry.local')
        self.assertEqual(config.digest_schedule, '0 8 * * *')
        self.assertEqual(config.digest_prompts, ['test prompt'])
    
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
        
        self.assertEqual(config.log_level, 'INFO')  # Default
        self.assertEqual(config.entry_since, 0)     # Default
        self.assertEqual(config.llm_timeout, 60)    # Default
        self.assertEqual(config.llm_max_workers, 4) # Default
        self.assertEqual(config.llm_RPM, 1000)      # Default
    
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
        
        self.assertIn('summary', config.agents)
        agent = config.agents['summary']
        
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.prompt, "Summarize this article")
        self.assertEqual(agent.template, '<div>{content}</div>')
        self.assertEqual(len(agent.allow_rules), 2)
        self.assertEqual(agent.allow_rules[0], 'EntryTitle=(?i)python')
        self.assertEqual(agent.allow_rules[1], 'FeedSiteURL=.*github\\.com.*')
        self.assertEqual(len(agent.deny_rules), 1)
        self.assertEqual(agent.deny_rules[0], 'EntryTitle=(?i)spam')
    
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
        
        agent = config.agents['summary']
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
        self.assertIn('summary', config.agents)
        self.assertIn('translate', config.agents)
        self.assertIn('analyze', config.agents)
    
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
        self.assertIn('summary', config.agents)
        self.assertNotIn('invalid_agent', config.agents)
        self.assertNotIn('another', config.agents)


class TestConfigCompatibilityValidation(unittest.TestCase):
    """Tests for configuration compatibility validation"""
    
    def setUp(self):
        """Create temporary config file for testing"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yml',
            delete=False,
            encoding='utf-8'
        )
        
    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except:
            pass
    
    def _create_config_expect_exit(self, config_content, expected_output_contains):
        """Helper to test configs that should trigger sys.exit()"""
        self.temp_file.write(config_content)
        self.temp_file.flush()
        
        # Capture stdout
        captured_output = StringIO()
        
        with patch('builtins.open', return_value=open(self.temp_file.name, encoding='utf8')):
            with patch('sys.stdout', captured_output):
                with self.assertRaises(SystemExit) as cm:
                    Config()
        
        self.assertEqual(cm.exception.code, 1)
        output = captured_output.getvalue()
        
        # Check that all expected strings are in output
        for expected in expected_output_contains:
            self.assertIn(expected, output, f"Expected '{expected}' in output:\n{output}")
        
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "deprecated fields",
            "summary",
            "allow_list",
            "github.com/serpicroon/miniflux-ai"
        ])
    
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "summary",
            "deny_list"
        ])
    
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "summary",
            "min_content_length"
        ])
    
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "summary",
            "title",
            "style_block"
        ])
    
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "summary",
            "allow_list",
            "deny_list",
            "min_content_length"
        ])
        
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
        output = self._create_config_expect_exit(config_content, [
            "Config Incompatibility Detected",
            "summary",
            "allow_list",
            "translate",
            "deny_list",
            "min_content_length"
        ])
        
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
        self.temp_file.write(config_content)
        self.temp_file.flush()
        
        with patch('builtins.open', return_value=open(self.temp_file.name, encoding='utf8')):
            # Should not raise SystemExit
            config = Config()
            self.assertIsNotNone(config)
            self.assertIn('summary', config.agents)
    
    def test_empty_agents_no_validation_error(self):
        """Test that empty agents section doesn't trigger validation"""
        config_content = """
miniflux:
  base_url: http://miniflux.local
llm:
  base_url: http://llm.local
agents: {}
"""
        self.temp_file.write(config_content)
        self.temp_file.flush()
        
        with patch('builtins.open', return_value=open(self.temp_file.name, encoding='utf8')):
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
        self.temp_file.write(config_content)
        self.temp_file.flush()
        
        with patch('builtins.open', return_value=open(self.temp_file.name, encoding='utf8')):
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
        output = self._create_config_expect_exit(config_content, [
            "⚠️  Config Incompatibility Detected",
        ])
        
        # Verify no excessive indentation on main message
        lines = output.split('\n')
        # First line should not start with whitespace
        self.assertFalse(lines[0].startswith(' '), 
                        f"First line should not have leading spaces: '{lines[0]}'")
        
        # Agent list items should have exactly 2 spaces
        agent_lines = [l for l in lines if l.strip().startswith('- agent')]
        for line in agent_lines:
            # Should start with exactly 2 spaces
            self.assertTrue(line.startswith('  - '), 
                          f"Agent line should start with '  - ': '{line}'")


if __name__ == '__main__':
    unittest.main()

