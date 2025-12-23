"""
Unit tests for core.rule_matcher module
"""

import unittest
from unittest.mock import patch

from core.rule_matcher import (
    parse_rule,
    get_entry_field_value,
    _match_numeric_operator,
    _match_any_rule,
    match_rules,
    FIELD_ENTRY_TITLE,
    FIELD_ENTRY_URL,
    FIELD_ENTRY_CONTENT,
    FIELD_ENTRY_AUTHOR,
    FIELD_ENTRY_TAG,
    FIELD_ENTRY_CONTENT_LENGTH,
    FIELD_FEED_SITE_URL,
    FIELD_FEED_TITLE,
    FIELD_FEED_CATEGORY_TITLE,
    FIELD_NEVER_MATCH,
    SUPPORTED_FIELDS,
)


class TestFieldConstants(unittest.TestCase):
    """Test field name constants"""
    
    def test_constants_defined(self):
        """Test that all field constants are properly defined"""
        self.assertEqual(FIELD_ENTRY_TITLE, 'EntryTitle')
        self.assertEqual(FIELD_ENTRY_URL, 'EntryURL')
        self.assertEqual(FIELD_ENTRY_CONTENT, 'EntryContent')
        self.assertEqual(FIELD_ENTRY_AUTHOR, 'EntryAuthor')
        self.assertEqual(FIELD_ENTRY_TAG, 'EntryTag')
        self.assertEqual(FIELD_ENTRY_CONTENT_LENGTH, 'EntryContentLength')
        self.assertEqual(FIELD_FEED_SITE_URL, 'FeedSiteURL')
        self.assertEqual(FIELD_FEED_TITLE, 'FeedTitle')
        self.assertEqual(FIELD_FEED_CATEGORY_TITLE, 'FeedCategoryTitle')
        self.assertEqual(FIELD_NEVER_MATCH, 'NeverMatch')
    
    def test_supported_fields_contains_all_constants(self):
        """Test that SUPPORTED_FIELDS contains all field constants"""
        self.assertIn(FIELD_ENTRY_TITLE, SUPPORTED_FIELDS)
        self.assertIn(FIELD_ENTRY_URL, SUPPORTED_FIELDS)
        self.assertIn(FIELD_ENTRY_CONTENT, SUPPORTED_FIELDS)
        self.assertIn(FIELD_ENTRY_AUTHOR, SUPPORTED_FIELDS)
        self.assertIn(FIELD_ENTRY_TAG, SUPPORTED_FIELDS)
        self.assertIn(FIELD_ENTRY_CONTENT_LENGTH, SUPPORTED_FIELDS)
        self.assertIn(FIELD_FEED_SITE_URL, SUPPORTED_FIELDS)
        self.assertIn(FIELD_FEED_TITLE, SUPPORTED_FIELDS)
        self.assertIn(FIELD_FEED_CATEGORY_TITLE, SUPPORTED_FIELDS)
        self.assertIn(FIELD_NEVER_MATCH, SUPPORTED_FIELDS)


class TestParseRule(unittest.TestCase):
    """Tests for parse_rule function"""
    
    def test_valid_rule_with_pattern(self):
        """Test parsing valid rule with pattern"""
        result = parse_rule("EntryTitle=(?i)python")
        self.assertEqual(result, ("EntryTitle", "(?i)python"))
    
    def test_valid_rule_with_complex_pattern(self):
        """Test parsing rule with complex regex pattern"""
        result = parse_rule("FeedSiteURL=https://example\\.com/.*")
        self.assertEqual(result, ("FeedSiteURL", "https://example\\.com/.*"))
    
    def test_valid_rule_with_equals_in_pattern(self):
        """Test parsing rule with '=' in the pattern"""
        result = parse_rule("EntryContent=value=test")
        self.assertEqual(result, ("EntryContent", "value=test"))
    
    def test_nevermatch_with_empty_pattern(self):
        """Test NeverMatch can have empty pattern"""
        result = parse_rule("NeverMatch=")
        self.assertEqual(result, ("NeverMatch", ""))
    
    def test_nevermatch_with_pattern(self):
        """Test NeverMatch with description text"""
        result = parse_rule("NeverMatch=保留此项")
        self.assertEqual(result, ("NeverMatch", "保留此项"))
    
    def test_invalid_rule_no_equals(self):
        """Test invalid rule without '=' returns None"""
        result = parse_rule("InvalidRule")
        self.assertIsNone(result)
    
    def test_invalid_rule_empty_string(self):
        """Test empty string returns None"""
        result = parse_rule("")
        self.assertIsNone(result)
    
    def test_invalid_field_name(self):
        """Test unsupported field name returns None"""
        result = parse_rule("InvalidField=pattern")
        self.assertIsNone(result)
    
    def test_empty_pattern_for_regular_field(self):
        """Test empty pattern for non-NeverMatch field returns None"""
        result = parse_rule("EntryTitle=")
        self.assertIsNone(result)
    
    def test_whitespace_handling(self):
        """Test that whitespace in field name and pattern is stripped"""
        result = parse_rule("  EntryTitle  =  (?i)test  ")
        self.assertEqual(result, ("EntryTitle", "(?i)test"))


class TestGetEntryFieldValue(unittest.TestCase):
    """Tests for get_entry_field_value function"""
    
    def setUp(self):
        """Set up test entry data"""
        self.entry = {
            'title': 'Test Article Title',
            'url': 'https://example.com/article',
            'content': '<p>This is <strong>HTML</strong> content with <em>tags</em>.</p>',
            'author': 'John Doe',
            'tags': ['python', 'programming', 'tutorial'],
            'feed': {
                'site_url': 'https://example.com',
                'title': 'Example Blog',
                'category': {
                    'title': 'Technology'
                }
            }
        }
    
    def test_get_entry_title(self):
        """Test extracting entry title"""
        result = get_entry_field_value(self.entry, FIELD_ENTRY_TITLE)
        self.assertEqual(result, 'Test Article Title')
    
    def test_get_entry_url(self):
        """Test extracting entry URL"""
        result = get_entry_field_value(self.entry, FIELD_ENTRY_URL)
        self.assertEqual(result, 'https://example.com/article')
    
    def test_get_entry_content_strips_html(self):
        """Test that entry content has HTML tags stripped"""
        result = get_entry_field_value(self.entry, FIELD_ENTRY_CONTENT)
        # Should not contain HTML tags
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertNotIn('</p>', result)
        # Should contain text content
        self.assertIn('This is', result)
        self.assertIn('HTML', result)
        self.assertIn('content', result)
    
    def test_get_entry_author(self):
        """Test extracting entry author"""
        result = get_entry_field_value(self.entry, FIELD_ENTRY_AUTHOR)
        self.assertEqual(result, 'John Doe')
    
    def test_get_entry_tag(self):
        """Test extracting entry tags as comma-separated string"""
        result = get_entry_field_value(self.entry, FIELD_ENTRY_TAG)
        self.assertEqual(result, 'python,programming,tutorial')
    
    def test_get_feed_site_url(self):
        """Test extracting feed site URL"""
        result = get_entry_field_value(self.entry, FIELD_FEED_SITE_URL)
        self.assertEqual(result, 'https://example.com')
    
    def test_get_feed_title(self):
        """Test extracting feed title"""
        result = get_entry_field_value(self.entry, FIELD_FEED_TITLE)
        self.assertEqual(result, 'Example Blog')
    
    def test_get_feed_category_title(self):
        """Test extracting feed category title"""
        result = get_entry_field_value(self.entry, FIELD_FEED_CATEGORY_TITLE)
        self.assertEqual(result, 'Technology')
    
    def test_missing_optional_field_returns_empty_string(self):
        """Test that missing optional fields return empty string"""
        entry_without_author = {'title': 'Test'}
        result = get_entry_field_value(entry_without_author, FIELD_ENTRY_AUTHOR)
        self.assertEqual(result, '')
    
    def test_empty_tags_returns_empty_string(self):
        """Test that empty tags list returns empty string"""
        entry_no_tags = {'tags': []}
        result = get_entry_field_value(entry_no_tags, FIELD_ENTRY_TAG)
        self.assertEqual(result, '')
    
    def test_missing_feed_info_returns_empty_string(self):
        """Test that missing feed info returns empty string"""
        entry_no_feed = {'title': 'Test'}
        result = get_entry_field_value(entry_no_feed, FIELD_FEED_SITE_URL)
        self.assertEqual(result, '')
    
    def test_missing_category_returns_empty_string(self):
        """Test that missing category returns empty string"""
        entry_no_category = {'feed': {'title': 'Blog'}}
        result = get_entry_field_value(entry_no_category, FIELD_FEED_CATEGORY_TITLE)
        self.assertEqual(result, '')


class TestMatchNumericOperator(unittest.TestCase):
    """Tests for _match_numeric_operator function - generic numeric comparison"""
    
    def test_gt_operator_true(self):
        """Test gt: operator when value > threshold"""
        result = _match_numeric_operator(100, "gt:50")
        self.assertTrue(result)
    
    def test_gt_operator_false(self):
        """Test gt: operator when value <= threshold"""
        result = _match_numeric_operator(50, "gt:100")
        self.assertFalse(result)
    
    def test_gt_operator_equal(self):
        """Test gt: operator when value == threshold (should be false)"""
        result = _match_numeric_operator(100, "gt:100")
        self.assertFalse(result)
    
    def test_ge_operator_true(self):
        """Test ge: operator when value >= threshold"""
        result = _match_numeric_operator(100, "ge:100")
        self.assertTrue(result)
    
    def test_ge_operator_greater(self):
        """Test ge: operator when value > threshold"""
        result = _match_numeric_operator(150, "ge:100")
        self.assertTrue(result)
    
    def test_ge_operator_false(self):
        """Test ge: operator when value < threshold"""
        result = _match_numeric_operator(50, "ge:100")
        self.assertFalse(result)
    
    def test_lt_operator_true(self):
        """Test lt: operator when value < threshold"""
        result = _match_numeric_operator(50, "lt:100")
        self.assertTrue(result)
    
    def test_lt_operator_false(self):
        """Test lt: operator when value >= threshold"""
        result = _match_numeric_operator(100, "lt:50")
        self.assertFalse(result)
    
    def test_lt_operator_equal(self):
        """Test lt: operator when value == threshold (should be false)"""
        result = _match_numeric_operator(100, "lt:100")
        self.assertFalse(result)
    
    def test_le_operator_true(self):
        """Test le: operator when value <= threshold"""
        result = _match_numeric_operator(100, "le:100")
        self.assertTrue(result)
    
    def test_le_operator_less(self):
        """Test le: operator when value < threshold"""
        result = _match_numeric_operator(50, "le:100")
        self.assertTrue(result)
    
    def test_le_operator_false(self):
        """Test le: operator when value > threshold"""
        result = _match_numeric_operator(150, "le:100")
        self.assertFalse(result)
    
    def test_eq_operator_true(self):
        """Test eq: operator when value == threshold"""
        result = _match_numeric_operator(100, "eq:100")
        self.assertTrue(result)
    
    def test_eq_operator_false_greater(self):
        """Test eq: operator when value > threshold"""
        result = _match_numeric_operator(150, "eq:100")
        self.assertFalse(result)
    
    def test_eq_operator_false_less(self):
        """Test eq: operator when value < threshold"""
        result = _match_numeric_operator(50, "eq:100")
        self.assertFalse(result)
    
    def test_between_operator_true(self):
        """Test between: operator when value is in range"""
        result = _match_numeric_operator(75, "between:50,100")
        self.assertTrue(result)
    
    def test_between_operator_lower_bound(self):
        """Test between: operator at lower bound (inclusive)"""
        result = _match_numeric_operator(50, "between:50,100")
        self.assertTrue(result)
    
    def test_between_operator_upper_bound(self):
        """Test between: operator at upper bound (inclusive)"""
        result = _match_numeric_operator(100, "between:50,100")
        self.assertTrue(result)
    
    def test_between_operator_below_range(self):
        """Test between: operator when value is below range"""
        result = _match_numeric_operator(30, "between:50,100")
        self.assertFalse(result)
    
    def test_between_operator_above_range(self):
        """Test between: operator when value is above range"""
        result = _match_numeric_operator(150, "between:50,100")
        self.assertFalse(result)
    
    def test_between_with_spaces(self):
        """Test between: operator handles spaces around numbers"""
        result = _match_numeric_operator(75, "between: 50 , 100 ")
        self.assertTrue(result)
    
    def test_invalid_operator(self):
        """Test invalid operator returns False"""
        result = _match_numeric_operator(100, "invalid:100")
        self.assertFalse(result)
    
    def test_invalid_number_format(self):
        """Test invalid number format returns False"""
        result = _match_numeric_operator(100, "gt:not_a_number")
        self.assertFalse(result)
    
    def test_between_missing_comma(self):
        """Test between: without comma returns False"""
        result = _match_numeric_operator(75, "between:50")
        self.assertFalse(result)


class TestMatchAnyRule(unittest.TestCase):
    """Tests for _match_any_rule function"""
    
    def setUp(self):
        """Set up test entry data"""
        self.entry = {
            'title': 'Python Programming Tutorial',
            'url': 'https://example.com/python',
            'content': '<p>' + 'test content ' * 20 + '</p>',
            'author': 'Jane Smith',
            'tags': ['python', 'tutorial'],
            'feed': {
                'site_url': 'https://example.com',
                'title': 'Tech Blog',
                'category': {'title': 'Development'}
            }
        }
    
    def test_matches_entry_title(self):
        """Test matching against entry title"""
        rules = ["EntryTitle=(?i)python"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_does_not_match_entry_title(self):
        """Test non-matching entry title"""
        rules = ["EntryTitle=(?i)java"]
        result = _match_any_rule(self.entry, rules)
        self.assertFalse(result)
    
    def test_case_sensitive_matching(self):
        """Test case-sensitive regex matching"""
        rules = ["EntryTitle=python"]  # lowercase
        result = _match_any_rule(self.entry, rules)
        self.assertFalse(result)  # Title has "Python" with capital P
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive matching with (?i)"""
        rules = ["EntryTitle=(?i)python"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_matches_feed_site_url(self):
        """Test matching against feed site URL"""
        rules = ["FeedSiteURL=.*example\\.com.*"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_matches_first_rule_in_list(self):
        """Test that matching stops on first match"""
        rules = ["EntryTitle=(?i)python", "EntryTitle=(?i)java"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_nevermatch_never_matches(self):
        """Test that NeverMatch field never matches"""
        rules = ["NeverMatch=anything"]
        result = _match_any_rule(self.entry, rules)
        self.assertFalse(result)
    
    def test_nevermatch_does_not_affect_other_rules(self):
        """Test that NeverMatch is skipped but other rules work"""
        rules = ["NeverMatch=placeholder", "EntryTitle=(?i)python"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_content_length_matching(self):
        """Test EntryContentLength matching"""
        with patch('core.rule_matcher.get_content_length', return_value=100):
            rules = ["EntryContentLength=gt:50"]
            result = _match_any_rule(self.entry, rules)
            self.assertTrue(result)
    
    def test_invalid_rules_are_skipped(self):
        """Test that invalid rules are skipped"""
        rules = ["InvalidField=test", "EntryTitle=(?i)python"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_invalid_regex_is_skipped(self):
        """Test that rules with invalid regex are skipped"""
        rules = ["EntryTitle=[invalid(regex", "FeedSiteURL=.*example.*"]
        result = _match_any_rule(self.entry, rules)
        self.assertTrue(result)
    
    def test_empty_rules_list(self):
        """Test empty rules list returns False"""
        rules = []
        result = _match_any_rule(self.entry, rules)
        self.assertFalse(result)
    
    def test_all_rules_invalid(self):
        """Test all invalid rules returns False"""
        rules = ["InvalidField=test", "NeverMatch=skip"]
        result = _match_any_rule(self.entry, rules)
        self.assertFalse(result)


class TestMatchRules(unittest.TestCase):
    """Tests for match_rules function (main entry point)"""
    
    def setUp(self):
        """Set up test entry data"""
        self.entry = {
            'title': 'Python Programming Tutorial',
            'url': 'https://example.com/python',
            'content': '<p>' + 'test content ' * 20 + '</p>',
            'author': 'Jane Smith',
            'tags': ['python', 'tutorial'],
            'feed': {
                'site_url': 'https://example.com',
                'title': 'Tech Blog',
                'category': {'title': 'Development'}
            }
        }
    
    def test_no_rules_returns_true(self):
        """Test that no rules means process all entries"""
        result = match_rules(self.entry, [], [])
        self.assertTrue(result)
    
    def test_allow_rules_matching(self):
        """Test allow_rules: entry must match at least one"""
        allow_rules = ["EntryTitle=(?i)python"]
        result = match_rules(self.entry, allow_rules, [])
        self.assertTrue(result)
    
    def test_allow_rules_not_matching(self):
        """Test allow_rules: entry not matching is blocked"""
        allow_rules = ["EntryTitle=(?i)java"]
        result = match_rules(self.entry, allow_rules, [])
        self.assertFalse(result)
    
    def test_allow_rules_multiple_or_logic(self):
        """Test multiple allow_rules work with OR logic"""
        allow_rules = ["EntryTitle=(?i)java", "EntryTitle=(?i)python"]
        result = match_rules(self.entry, allow_rules, [])
        self.assertTrue(result)
    
    def test_deny_rules_matching(self):
        """Test deny_rules: matching entry is blocked"""
        deny_rules = ["EntryTitle=(?i)python"]
        result = match_rules(self.entry, [], deny_rules)
        self.assertFalse(result)
    
    def test_deny_rules_not_matching(self):
        """Test deny_rules: non-matching entry is allowed"""
        deny_rules = ["EntryTitle=(?i)java"]
        result = match_rules(self.entry, [], deny_rules)
        self.assertTrue(result)
    
    def test_deny_rules_take_precedence(self):
        """Test that deny_rules are checked before allow_rules (Miniflux behavior)"""
        allow_rules = ["EntryTitle=(?i)python"]  # Would match
        deny_rules = ["FeedSiteURL=.*example.*"]  # Also matches
        result = match_rules(self.entry, allow_rules, deny_rules)
        # Deny rule checked first and matches, so entry is blocked
        # even though it would match allow_rules
        self.assertFalse(result)
    
    def test_combined_rules_allow_after_deny(self):
        """Test combined mode: deny first, then allow"""
        # Entry doesn't match deny_rules but matches allow_rules
        allow_rules = ["EntryTitle=(?i)python"]
        deny_rules = ["EntryTitle=(?i)spam"]  # Doesn't match
        result = match_rules(self.entry, allow_rules, deny_rules)
        # Not blocked by deny, matches allow → keep
        self.assertTrue(result)
    
    def test_combined_rules_neither_match(self):
        """Test combined mode: neither deny nor allow match"""
        allow_rules = ["EntryTitle=(?i)javascript"]  # Doesn't match
        deny_rules = ["EntryTitle=(?i)spam"]  # Doesn't match
        result = match_rules(self.entry, allow_rules, deny_rules)
        # Not blocked by deny, but allow_rules exist and don't match → block
        self.assertFalse(result)
    
    def test_allow_rules_with_nevermatch_placeholder(self):
        """Test real-world pattern: NeverMatch as placeholder"""
        allow_rules = ["NeverMatch=保留此项", "EntryTitle=(?i)python"]
        result = match_rules(self.entry, allow_rules, [])
        self.assertTrue(result)
    
    def test_deny_rules_with_content_length(self):
        """Test deny_rules with EntryContentLength"""
        with patch('core.rule_matcher.get_content_length', return_value=100):
            deny_rules = ["EntryContentLength=gt:50"]
            result = match_rules(self.entry, [], deny_rules)
            self.assertFalse(result)  # Content > 50, so denied
    
    def test_multiple_field_matching(self):
        """Test matching against multiple different fields"""
        allow_rules = [
            "FeedSiteURL=.*example\\.com.*",
            "FeedCategoryTitle=Development",
            "EntryAuthor=Jane.*"
        ]
        result = match_rules(self.entry, allow_rules, [])
        self.assertTrue(result)  # Matches first rule


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios"""
    
    def test_translation_agent_pattern(self):
        """Test typical translation agent configuration"""
        entry = {
            'title': 'English Article',
            'url': 'https://foreign-site.com/article',
            'content': '<p>English content here</p>',
            'feed': {'site_url': 'https://foreign-site.com'}
        }
        
        # Typical translation config: only translate specific sites
        allow_rules = [
            "NeverMatch=保留此项",
            "FeedSiteURL=https://foreign-site\\.com.*"
        ]
        deny_rules = []
        
        result = match_rules(entry, allow_rules, deny_rules)
        self.assertTrue(result)
    
    def test_summary_agent_pattern(self):
        """Test typical summary agent configuration"""
        entry = {
            'title': 'Long Article',
            'url': 'https://blog.com/article',
            'content': '<p>' + 'content ' * 50 + '</p>',
            'feed': {'site_url': 'https://blog.com'}
        }
        
        # Typical summary config: exclude digest, require min length
        with patch('core.rule_matcher.get_content_length', return_value=100):
            allow_rules = []
            deny_rules = [
                "FeedSiteURL=.*digest.*",
                "EntryContentLength=gt:99"
            ]
            
            result = match_rules(entry, allow_rules, deny_rules)
            self.assertFalse(result)  # Blocked by EntryContentLength
    
    def test_filtering_spam_titles(self):
        """Test filtering out spam/ad titles"""
        spam_entry = {
            'title': 'Save $100 on this product!',
            'url': 'https://example.com/spam',
            'feed': {'site_url': 'https://example.com'}
        }
        
        deny_rules = [
            "EntryTitle=(?i)\\bsave\\s+\\$\\d+",
            "EntryTitle=(?i)\\$\\d+\\s+off"
        ]
        
        result = match_rules(spam_entry, [], deny_rules)
        self.assertFalse(result)  # Blocked by spam filter
    
    def test_category_based_filtering(self):
        """Test filtering by feed category"""
        entry = {
            'title': 'Article',
            'url': 'https://example.com/article',
            'feed': {
                'site_url': 'https://example.com',
                'category': {'title': 'Development'}
            }
        }
        
        allow_rules = ["FeedCategoryTitle=(?i)development"]
        result = match_rules(entry, allow_rules, [])
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()

