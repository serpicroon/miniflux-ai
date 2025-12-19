"""
Rule-based entry filtering using Miniflux-compatible rule syntax.

Supports filtering entries based on various fields with regex patterns.
Rule format: FieldName=RegexPattern
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from common.logger import logger
from core.content_helper import get_content_text, get_content_length


FIELD_ENTRY_TITLE = 'EntryTitle'
FIELD_ENTRY_URL = 'EntryURL'
FIELD_ENTRY_CONTENT = 'EntryContent'
FIELD_ENTRY_AUTHOR = 'EntryAuthor'
FIELD_ENTRY_TAG = 'EntryTag'
FIELD_ENTRY_CONTENT_MIN_LENGTH = 'EntryContentMinLength'
FIELD_FEED_SITE_URL = 'FeedSiteUrl'
FIELD_FEED_TITLE = 'FeedTitle'
FIELD_FEED_CATEGORY_TITLE = 'FeedCategoryTitle'
FIELD_NEVER_MATCH = 'NeverMatch'

SUPPORTED_FIELDS = {
    FIELD_ENTRY_TITLE,
    FIELD_ENTRY_URL,
    FIELD_ENTRY_CONTENT,
    FIELD_ENTRY_AUTHOR,
    FIELD_ENTRY_TAG,
    FIELD_ENTRY_CONTENT_MIN_LENGTH,
    FIELD_FEED_SITE_URL,
    FIELD_FEED_TITLE,
    FIELD_FEED_CATEGORY_TITLE,
    FIELD_NEVER_MATCH,
}


def parse_rule(rule_string: str) -> Optional[Tuple[str, str]]:
    """
    Parse a rule string in format 'FieldName=RegEx' into field and pattern.
    
    Args:
        rule_string: Rule in format "FieldName=RegEx"
        
    Returns:
        Tuple of (field_name, pattern) if valid, None if invalid
        
    Examples:
        >>> parse_rule("EntryTitle=(?i)test")
        ('EntryTitle', '(?i)test')
        >>> parse_rule("InvalidField=pattern")
        None
    """
    if not rule_string or '=' not in rule_string:
        logger.debug(f"Invalid rule format (missing '='): {rule_string}")
        return None
    
    field_name, pattern = rule_string.split('=', 1)
    field_name = field_name.strip()
    pattern = pattern.strip()
    
    if field_name not in SUPPORTED_FIELDS:
        logger.debug(f"Unsupported field name in rule: {field_name}")
        return None
    
    # Allow empty pattern for NeverMatch
    if not pattern and field_name != FIELD_NEVER_MATCH:
        logger.debug(f"Empty pattern in rule: {rule_string}")
        return None
    
    return (field_name, pattern)


def get_entry_field_value(entry: Dict[str, Any], field_name: str) -> str:
    """
    Extract field value from entry based on field name.
    
    Args:
        entry: Entry dictionary from Miniflux
        field_name: Name of the field to extract
        
    Returns:
        String value of the field (empty string for missing optional fields)
    """
    if field_name == FIELD_ENTRY_TITLE:
        return entry.get('title', '')
    
    elif field_name == FIELD_ENTRY_URL:
        return entry.get('url', '')
    
    elif field_name == FIELD_ENTRY_CONTENT:
        return get_content_text(entry)
    
    elif field_name == FIELD_ENTRY_AUTHOR:
        return entry.get('author', '')
    
    elif field_name == FIELD_ENTRY_TAG:
        tags = entry.get('tags', [])
        return ','.join(tags) if tags else ''
    
    elif field_name == FIELD_ENTRY_CONTENT_MIN_LENGTH:
        return str(get_content_length(entry))

    elif field_name == FIELD_FEED_SITE_URL:
        return entry.get('feed', {}).get('site_url', '')
    
    elif field_name == FIELD_FEED_TITLE:
        return entry.get('feed', {}).get('title', '')
    
    elif field_name == FIELD_FEED_CATEGORY_TITLE:
        return entry.get('feed', {}).get('category', {}).get('title', '')
    
    return ''


def _match_any_rule(entry: Dict[str, Any], rules: List[str]) -> bool:
    """
    Check if entry matches any rule in the list.
    Returns True on first match (Miniflux behavior).
    
    Args:
        entry: Entry dictionary
        rules: List of rules in "FieldName=RegEx" format
        
    Returns:
        True if entry matches at least one rule, False otherwise
    """
    for rule_string in rules:
        parsed = parse_rule(rule_string)
        if not parsed:
            continue
        
        field_name, pattern = parsed
        
        if field_name == FIELD_NEVER_MATCH:
            continue
        
        if field_name == FIELD_ENTRY_CONTENT_MIN_LENGTH:
            min_length = int(pattern)
            if get_content_length(entry) >= min_length:
                return True
            continue
        
        field_value = get_entry_field_value(entry, field_name)
        
        try:
            if re.search(pattern, field_value):
                return True
        except re.error as e:
            logger.warning(f"Invalid regex pattern in rule '{rule_string}': {e}")
            continue
    
    return False


def match_rules(entry: Dict[str, Any], 
                allow_rules: List[str], 
                deny_rules: List[str]) -> bool:
    """
    Determine if entry should be processed based on allow and deny rules.
    
    Rule logic (following Miniflux behavior):
    1. If allow_rules exist and not empty: entry must match at least one allow rule
    2. Elif deny_rules exist: entry must NOT match any deny rule
    3. Else (no rules): process all entries
    
    Args:
        entry: Entry dictionary from Miniflux
        allow_rules: List of rules to allow (keep) entries
        deny_rules: List of rules to block entries
        
    Returns:
        True if entry should be processed, False otherwise
        
    Examples:
        >>> # Only process entries matching allow rules
        >>> match_rules(entry, ["EntryTitle=(?i)python"], [])
        
        >>> # Process all except entries matching deny rules
        >>> match_rules(entry, [], ["EntryTitle=(?i)spam"])
        
        >>> # No rules: process everything
        >>> match_rules(entry, [], [])
        True
    """
    # Priority 1: If allow_rules exist, entry must match at least one
    if allow_rules:
        return _match_any_rule(entry, allow_rules)
    
    # Priority 2: If deny_rules exist, entry must NOT match any
    if deny_rules:
        return not _match_any_rule(entry, deny_rules)
    
    # No rules: process all entries
    return True

