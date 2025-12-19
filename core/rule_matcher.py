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
FIELD_ENTRY_CONTENT_LENGTH = 'EntryContentLength'
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
    FIELD_ENTRY_CONTENT_LENGTH,
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

    elif field_name == FIELD_FEED_SITE_URL:
        return entry.get('feed', {}).get('site_url', '')
    
    elif field_name == FIELD_FEED_TITLE:
        return entry.get('feed', {}).get('title', '')
    
    elif field_name == FIELD_FEED_CATEGORY_TITLE:
        return entry.get('feed', {}).get('category', {}).get('title', '')
    
    return ''


def _match_content_length(entry: Dict[str, Any], operator: str) -> bool:
    """
    Check if entry content length matches the operator condition.
    
    Supports standard comparison operators:
    - gt:N        - length > N (greater than)
    - ge:N        - length >= N (greater or equal)
    - lt:N        - length < N (less than)
    - le:N        - length <= N (less or equal)
    - eq:N        - length == N (equal)
    - between:N,M - N <= length <= M (inclusive range)
    
    Args:
        entry: Entry dictionary
        operator: Operator string (e.g., "gt:100", "between:50,200")
        
    Returns:
        True if content length matches the condition
        
    Examples:
        >>> _match_content_length(entry, "gt:100")  # length > 100
        >>> _match_content_length(entry, "ge:100")  # length >= 100
        >>> _match_content_length(entry, "lt:50")  # length < 50
        >>> _match_content_length(entry, "le:50")  # length <= 50
        >>> _match_content_length(entry, "eq:100")  # length == 100
        >>> _match_content_length(entry, "between:50,200")  # 50 <= length <= 200
    """
    content_length = get_content_length(entry)
    
    try:
        if operator.startswith('gt:'):
            threshold = int(operator[3:])
            return content_length > threshold
        
        elif operator.startswith('ge:'):
            threshold = int(operator[3:])
            return content_length >= threshold
        
        elif operator.startswith('lt:'):
            threshold = int(operator[3:])
            return content_length < threshold
        
        elif operator.startswith('le:'):
            threshold = int(operator[3:])
            return content_length <= threshold
        
        elif operator.startswith('eq:'):
            threshold = int(operator[3:])
            return content_length == threshold
        
        elif operator.startswith('between:'):
            range_str = operator[8:]
            if ',' not in range_str:
                logger.warning(f"Invalid between operator format: {operator}")
                return False
            min_val, max_val = range_str.split(',', 1)
            min_length = int(min_val.strip())
            max_length = int(max_val.strip())
            return min_length <= content_length <= max_length
        
        else:
            logger.warning(f"Unknown EntryContentLength operator: {operator}")
            return False
            
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid EntryContentLength operator '{operator}': {e}")
        return False


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
        
        # Special handling for EntryContentLength with operators
        if field_name == FIELD_ENTRY_CONTENT_LENGTH:
            if _match_content_length(entry, pattern):
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
    
    Rule processing order (following Miniflux behavior):
    1. Check deny_rules (Block Rules) first - highest priority
       → If matched: immediately block, return False
    2. Check allow_rules (Keep Rules) - if defined
       → If matched: keep, return True
       → If NOT matched: block, return False
    3. If no allow_rules defined: default to keep, return True
    
    This implements:
    - Blacklist mode (only deny_rules): Block specific entries, keep others
    - Whitelist mode (only allow_rules): Keep only specific entries
    - Combined mode (both): Block first, then require allow match
    
    Args:
        entry: Entry dictionary from Miniflux
        allow_rules: List of rules to allow (keep) entries
        deny_rules: List of rules to block entries
        
    Returns:
        True if entry should be processed, False otherwise
        
    Examples:
        >>> # Blacklist mode: block spam, keep others
        >>> match_rules(entry, [], ["EntryTitle=(?i)spam"])
        
        >>> # Whitelist mode: keep only Python articles
        >>> match_rules(entry, ["EntryTitle=(?i)python"], [])
        
        >>> # Combined mode: block ads first, then keep only tech
        >>> match_rules(entry, ["FeedCategory=Tech"], ["EntryTitle=(?i)ad"])
        
        >>> # No rules: process everything
        >>> match_rules(entry, [], [])
        True
    """
    # Step 1: Check deny_rules first (Block Rules - highest priority)
    # If entry matches ANY deny rule, immediately block it
    if deny_rules and _match_any_rule(entry, deny_rules):
        return False
    
    # Step 2: Check allow_rules (Keep Rules)
    # If allow_rules are defined, entry MUST match at least one
    if allow_rules:
        return _match_any_rule(entry, allow_rules)
    
    # Step 3: No allow_rules defined, default to keep
    # (Blacklist mode: only block entries matching deny_rules)
    return True

