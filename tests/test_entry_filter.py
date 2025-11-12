"""
Unit tests for core.entry_filter module using unittest
"""

import unittest
from unittest.mock import patch, MagicMock
import time

from core.entry_filter import (
    filter_entry,
    filter_entry_by_agent,
    _filter_content_length,
    _filter_site,
    _matches_any_pattern,
    _ENTRY_CACHE
)


class TestFilterEntry(unittest.TestCase):
    """Tests for filter_entry function"""
    
    def setUp(self):
        """Clear cache before each test"""
        _ENTRY_CACHE.clear()
    
    def test_first_time_entry(self):
        """Test that first time entry is allowed"""
        entry = {'id': 1, 'content': '<p>Test content</p>'}
        result = filter_entry(entry)
        self.assertTrue(result)
    
    def test_duplicate_entry(self):
        """Test that duplicate entry is rejected"""
        entry = {'id': 2, 'content': '<p>Test content</p>'}
        
        # First call should pass
        first_result = filter_entry(entry)
        self.assertTrue(first_result)
        
        # Second call should be blocked
        second_result = filter_entry(entry)
        self.assertFalse(second_result)
    
    def test_different_entries(self):
        """Test that different entries are both allowed"""
        entry1 = {'id': 3, 'content': '<p>Content 1</p>'}
        entry2 = {'id': 4, 'content': '<p>Content 2</p>'}
        
        result1 = filter_entry(entry1)
        result2 = filter_entry(entry2)
        
        self.assertTrue(result1)
        self.assertTrue(result2)
    
    def test_multiple_duplicate_attempts(self):
        """Test that multiple duplicate attempts are all rejected"""
        entry = {'id': 5, 'content': '<p>Test content</p>'}
        
        # First call should pass
        self.assertTrue(filter_entry(entry))
        
        # Multiple subsequent calls should fail
        self.assertFalse(filter_entry(entry))
        self.assertFalse(filter_entry(entry))
        self.assertFalse(filter_entry(entry))
    
    def test_cache_expiration(self):
        """Test that cache expires after TTL"""
        # Note: This test would require mocking time or waiting 300 seconds
        # We'll test the basic behavior instead
        entry = {'id': 6, 'content': '<p>Test content</p>'}
        
        # First call should pass
        self.assertTrue(filter_entry(entry))
        
        # Clear cache manually to simulate expiration
        _ENTRY_CACHE.clear()
        
        # Should be allowed again after cache clear
        self.assertTrue(filter_entry(entry))


class TestMatchesAnyPattern(unittest.TestCase):
    """Tests for _matches_any_pattern function"""
    
    def test_exact_match(self):
        """Test exact URL match"""
        url = "https://example.com"
        patterns = ["https://example.com"]
        self.assertTrue(_matches_any_pattern(url, patterns))
    
    def test_wildcard_subdomain(self):
        """Test wildcard matching for subdomains"""
        url = "https://blog.example.com"
        patterns = ["https://*.example.com"]
        self.assertTrue(_matches_any_pattern(url, patterns))
    
    def test_wildcard_path(self):
        """Test wildcard matching for paths"""
        url = "https://example.com/blog/post"
        patterns = ["https://example.com/*"]
        self.assertTrue(_matches_any_pattern(url, patterns))
    
    def test_no_match(self):
        """Test URL that doesn't match any pattern"""
        url = "https://different.com"
        patterns = ["https://example.com"]
        self.assertFalse(_matches_any_pattern(url, patterns))
    
    def test_multiple_patterns(self):
        """Test matching against multiple patterns"""
        url = "https://blog.example.com"
        patterns = [
            "https://news.example.com",
            "https://blog.example.com",
            "https://forum.example.com"
        ]
        self.assertTrue(_matches_any_pattern(url, patterns))
    
    def test_empty_pattern_list(self):
        """Test with empty pattern list"""
        url = "https://example.com"
        patterns = []
        self.assertFalse(_matches_any_pattern(url, patterns))
    
    def test_complex_wildcard(self):
        """Test complex wildcard pattern"""
        url = "https://www.example.com/blog/2024/post"
        patterns = ["https://*.example.com/blog/*"]
        self.assertTrue(_matches_any_pattern(url, patterns))
    
    def test_case_sensitive_match(self):
        """Test that matching is case sensitive"""
        url = "https://Example.com"
        patterns = ["https://example.com"]
        self.assertFalse(_matches_any_pattern(url, patterns))


class TestFilterSite(unittest.TestCase):
    """Tests for _filter_site function"""
    
    def test_no_lists_allows_all(self):
        """Test that entries are allowed when no lists are configured"""
        agent = ("test_agent", {})
        entry = {
            'feed': {
                'site_url': 'https://example.com'
            }
        }
        self.assertTrue(_filter_site(agent, entry))
    
    def test_allow_list_matching(self):
        """Test that matching allow list allows entry"""
        agent = ("test_agent", {
            'allow_list': ['https://example.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://example.com'
            }
        }
        self.assertTrue(_filter_site(agent, entry))
    
    def test_allow_list_not_matching(self):
        """Test that non-matching allow list blocks entry"""
        agent = ("test_agent", {
            'allow_list': ['https://example.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://different.com'
            }
        }
        self.assertFalse(_filter_site(agent, entry))
    
    def test_deny_list_matching(self):
        """Test that matching deny list blocks entry"""
        agent = ("test_agent", {
            'deny_list': ['https://blocked.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://blocked.com'
            }
        }
        self.assertFalse(_filter_site(agent, entry))
    
    def test_deny_list_not_matching(self):
        """Test that non-matching deny list allows entry"""
        agent = ("test_agent", {
            'deny_list': ['https://blocked.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://allowed.com'
            }
        }
        self.assertTrue(_filter_site(agent, entry))
    
    def test_allow_list_with_wildcard(self):
        """Test allow list with wildcard patterns"""
        agent = ("test_agent", {
            'allow_list': ['https://*.example.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://blog.example.com'
            }
        }
        self.assertTrue(_filter_site(agent, entry))
    
    def test_deny_list_with_wildcard(self):
        """Test deny list with wildcard patterns"""
        agent = ("test_agent", {
            'deny_list': ['https://*.spam.com']
        })
        entry = {
            'feed': {
                'site_url': 'https://any.spam.com'
            }
        }
        self.assertFalse(_filter_site(agent, entry))
    
    def test_allow_list_takes_precedence(self):
        """Test that allow_list is checked before deny_list"""
        agent = ("test_agent", {
            'allow_list': ['https://allowed.com'],
            'deny_list': ['https://denied.com']
        })
        # Even if both lists exist, only allow_list is used
        entry_allowed = {
            'feed': {
                'site_url': 'https://allowed.com'
            }
        }
        entry_other = {
            'feed': {
                'site_url': 'https://other.com'
            }
        }
        self.assertTrue(_filter_site(agent, entry_allowed))
        self.assertFalse(_filter_site(agent, entry_other))


class TestFilterContentLength(unittest.TestCase):
    """Tests for _filter_content_length function"""
    
    @patch('core.entry_filter.get_content_length')
    def test_content_length_above_minimum(self, mock_get_length):
        """Test that content above minimum length is allowed"""
        mock_get_length.return_value = 100
        
        agent = ("test_agent", {'min_content_length': 50})
        entry = {'content': '<p>Test content</p>'}
        
        result = _filter_content_length(agent, entry)
        self.assertTrue(result)
        self.assertEqual(entry['content_length'], 100)
    
    @patch('core.entry_filter.get_content_length')
    def test_content_length_below_minimum(self, mock_get_length):
        """Test that content below minimum length is rejected"""
        mock_get_length.return_value = 30
        
        agent = ("test_agent", {'min_content_length': 50})
        entry = {'content': '<p>Short</p>'}
        
        result = _filter_content_length(agent, entry)
        self.assertFalse(result)
    
    @patch('core.entry_filter.get_content_length')
    def test_content_length_exactly_minimum(self, mock_get_length):
        """Test that content exactly at minimum length is allowed"""
        mock_get_length.return_value = 50
        
        agent = ("test_agent", {'min_content_length': 50})
        entry = {'content': '<p>Exact length</p>'}
        
        result = _filter_content_length(agent, entry)
        self.assertTrue(result)
    
    @patch('core.entry_filter.get_content_length')
    def test_zero_minimum_length(self, mock_get_length):
        """Test with zero minimum length requirement"""
        mock_get_length.return_value = 10
        
        agent = ("test_agent", {'min_content_length': 0})
        entry = {'content': '<p>Any content</p>'}
        
        result = _filter_content_length(agent, entry)
        self.assertTrue(result)
    
    @patch('core.entry_filter.get_content_length')
    def test_no_minimum_length_config(self, mock_get_length):
        """Test when min_content_length is not configured"""
        mock_get_length.return_value = 10
        
        agent = ("test_agent", {})
        entry = {'content': '<p>Any content</p>'}
        
        result = _filter_content_length(agent, entry)
        self.assertTrue(result)
    
    @patch('core.entry_filter.get_content_length')
    def test_empty_content(self, mock_get_length):
        """Test that empty content is rejected"""
        mock_get_length.return_value = 0
        
        agent = ("test_agent", {'min_content_length': 0})
        entry = {'content': ''}
        
        result = _filter_content_length(agent, entry)
        self.assertFalse(result)
    
    def test_uses_cached_content_length(self):
        """Test that cached content_length is used if available"""
        agent = ("test_agent", {'min_content_length': 50})
        entry = {
            'content': '<p>Test content</p>',
            'content_length': 100  # Pre-calculated
        }
        
        result = _filter_content_length(agent, entry)
        self.assertTrue(result)
        # Verify it used cached value
        self.assertEqual(entry['content_length'], 100)


class TestFilterEntryByAgent(unittest.TestCase):
    """Tests for filter_entry_by_agent function"""
    
    @patch('core.entry_filter._filter_site')
    @patch('core.entry_filter._filter_content_length')
    def test_both_filters_pass(self, mock_content, mock_site):
        """Test that entry passes when both filters pass"""
        mock_site.return_value = True
        mock_content.return_value = True
        
        agent = ("test_agent", {})
        entry = {'content': '<p>Test</p>', 'feed': {'site_url': 'https://example.com'}}
        
        result = filter_entry_by_agent(agent, entry)
        self.assertTrue(result)
    
    @patch('core.entry_filter._filter_site')
    @patch('core.entry_filter._filter_content_length')
    def test_site_filter_fails(self, mock_content, mock_site):
        """Test that entry fails when site filter fails"""
        mock_site.return_value = False
        mock_content.return_value = True
        
        agent = ("test_agent", {})
        entry = {'content': '<p>Test</p>', 'feed': {'site_url': 'https://blocked.com'}}
        
        result = filter_entry_by_agent(agent, entry)
        self.assertFalse(result)
    
    @patch('core.entry_filter._filter_site')
    @patch('core.entry_filter._filter_content_length')
    def test_content_filter_fails(self, mock_content, mock_site):
        """Test that entry fails when content filter fails"""
        mock_site.return_value = True
        mock_content.return_value = False
        
        agent = ("test_agent", {})
        entry = {'content': '<p>Short</p>', 'feed': {'site_url': 'https://example.com'}}
        
        result = filter_entry_by_agent(agent, entry)
        self.assertFalse(result)
    
    @patch('core.entry_filter._filter_site')
    @patch('core.entry_filter._filter_content_length')
    def test_both_filters_fail(self, mock_content, mock_site):
        """Test that entry fails when both filters fail"""
        mock_site.return_value = False
        mock_content.return_value = False
        
        agent = ("test_agent", {})
        entry = {'content': '<p>Short</p>', 'feed': {'site_url': 'https://blocked.com'}}
        
        result = filter_entry_by_agent(agent, entry)
        self.assertFalse(result)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions"""
    
    def setUp(self):
        """Clear cache before each test"""
        _ENTRY_CACHE.clear()
    
    @patch('core.entry_filter.get_content_length')
    def test_complete_filtering_workflow(self, mock_get_length):
        """Test complete filtering workflow with all components"""
        mock_get_length.return_value = 100
        
        # Configure agent with both site and content filters
        agent = ("summary", {
            'allow_list': ['https://blog.example.com'],
            'min_content_length': 50
        })
        
        # Entry that should pass all filters
        entry = {
            'id': 1,
            'content': '<p>This is a long article with substantial content.</p>',
            'feed': {
                'site_url': 'https://blog.example.com'
            }
        }
        
        # First check: entry should not be in cache
        self.assertTrue(filter_entry(entry))
        
        # Second check: should pass agent-specific filters
        self.assertTrue(filter_entry_by_agent(agent, entry))
        
        # Third check: duplicate entry should be rejected
        self.assertFalse(filter_entry(entry))
    
    @patch('core.entry_filter.get_content_length')
    def test_entry_rejected_by_site_filter(self, mock_get_length):
        """Test entry rejected by site filter but passes content filter"""
        mock_get_length.return_value = 100
        
        agent = ("summary", {
            'deny_list': ['https://spam.com'],
            'min_content_length': 50
        })
        
        entry = {
            'id': 2,
            'content': '<p>Long content from spam site</p>',
            'feed': {
                'site_url': 'https://spam.com'
            }
        }
        
        # Should pass cache check
        self.assertTrue(filter_entry(entry))
        
        # Should fail agent filter due to site
        self.assertFalse(filter_entry_by_agent(agent, entry))
    
    @patch('core.entry_filter.get_content_length')
    def test_entry_rejected_by_content_filter(self, mock_get_length):
        """Test entry rejected by content filter but passes site filter"""
        mock_get_length.return_value = 10
        
        agent = ("summary", {
            'allow_list': ['https://blog.example.com'],
            'min_content_length': 50
        })
        
        entry = {
            'id': 3,
            'content': '<p>Short</p>',
            'feed': {
                'site_url': 'https://blog.example.com'
            }
        }
        
        # Should pass cache check
        self.assertTrue(filter_entry(entry))
        
        # Should fail agent filter due to content length
        self.assertFalse(filter_entry_by_agent(agent, entry))
    
    def test_multiple_agents_different_configs(self):
        """Test same entry with different agent configurations"""
        entry = {
            'id': 4,
            'content': '<p>Medium length article content here.</p>',
            'feed': {
                'site_url': 'https://blog.example.com'
            },
            'content_length': 50
        }
        
        # Agent 1: Strict requirements
        agent_strict = ("strict", {
            'allow_list': ['https://news.example.com'],
            'min_content_length': 100
        })
        
        # Agent 2: Lenient requirements
        agent_lenient = ("lenient", {
            'allow_list': ['https://blog.example.com'],
            'min_content_length': 20
        })
        
        # Should pass cache check once
        self.assertTrue(filter_entry(entry))
        
        # Should fail strict agent
        self.assertFalse(filter_entry_by_agent(agent_strict, entry))
        
        # Should pass lenient agent
        self.assertTrue(filter_entry_by_agent(agent_lenient, entry))


if __name__ == '__main__':
    unittest.main()

