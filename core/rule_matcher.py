"""
Rule-based entry filtering using Miniflux-compatible rule syntax.

Supports filtering entries based on various fields with regex patterns.
Rule format: FieldName=RegexPattern
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from common.logger import get_logger
from core.content_helper import get_content_text, get_content_length

logger = get_logger(__name__)


class FieldType(Enum):
    """Field matching type for rule processing"""
    REGEX = "regex"      # Match using regular expression
    NUMERIC = "numeric"  # Match using numeric operators (gt, ge, lt, le, eq, between)
    NONE = "none"        # Never matches (placeholder)


# Field name constants
FIELD_ENTRY_TITLE = 'EntryTitle'
FIELD_ENTRY_URL = 'EntryURL'
FIELD_ENTRY_CONTENT = 'EntryContent'
FIELD_ENTRY_AUTHOR = 'EntryAuthor'
FIELD_ENTRY_TAG = 'EntryTag'
FIELD_ENTRY_CONTENT_LENGTH = 'EntryContentLength'
FIELD_FEED_SITE_URL = 'FeedSiteURL'
FIELD_FEED_TITLE = 'FeedTitle'
FIELD_FEED_CATEGORY_TITLE = 'FeedCategoryTitle'
FIELD_NEVER_MATCH = 'NeverMatch'

# Field configuration: maps field name to its matching type
FIELD_CONFIG = {
    FIELD_ENTRY_TITLE: FieldType.REGEX,
    FIELD_ENTRY_URL: FieldType.REGEX,
    FIELD_ENTRY_CONTENT: FieldType.REGEX,
    FIELD_ENTRY_AUTHOR: FieldType.REGEX,
    FIELD_ENTRY_TAG: FieldType.REGEX,
    FIELD_ENTRY_CONTENT_LENGTH: FieldType.NUMERIC,
    FIELD_FEED_SITE_URL: FieldType.REGEX,
    FIELD_FEED_TITLE: FieldType.REGEX,
    FIELD_FEED_CATEGORY_TITLE: FieldType.REGEX,
    FIELD_NEVER_MATCH: FieldType.NONE,
}

# All supported field names
SUPPORTED_FIELDS = set(FIELD_CONFIG.keys())


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

    elif field_name == FIELD_ENTRY_CONTENT_LENGTH:
        return str(get_content_length(entry))
    
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


def _match_numeric_operator(value: int, operator: str, field_name: str = "numeric field") -> bool:
    """
    Generic numeric comparison for rule fields with operator syntax.
    
    Supports standard comparison operators for any numeric field:
    - gt:N        - value > N (greater than)
    - ge:N        - value >= N (greater or equal)
    - lt:N        - value < N (less than)
    - le:N        - value <= N (less or equal)
    - eq:N        - value == N (equal)
    - between:N,M - N <= value <= M (inclusive range)
    
    Args:
        value: The numeric value to compare
        operator: Operator string (e.g., "gt:100", "between:50,200")
        field_name: Field name for logging purposes (optional)
        
    Returns:
        True if value matches the operator condition
    """
    try:
        if operator.startswith('gt:'):
            threshold = int(operator[3:])
            return value > threshold
        
        elif operator.startswith('ge:'):
            threshold = int(operator[3:])
            return value >= threshold
        
        elif operator.startswith('lt:'):
            threshold = int(operator[3:])
            return value < threshold
        
        elif operator.startswith('le:'):
            threshold = int(operator[3:])
            return value <= threshold
        
        elif operator.startswith('eq:'):
            threshold = int(operator[3:])
            return value == threshold
        
        elif operator.startswith('between:'):
            range_str = operator[8:]
            if ',' not in range_str:
                logger.warning(f"Invalid between operator format for {field_name}: {operator}")
                return False
            min_val, max_val = range_str.split(',', 1)
            min_threshold = int(min_val.strip())
            max_threshold = int(max_val.strip())
            return min_threshold <= value <= max_threshold
        
        else:
            logger.warning(f"Unknown numeric operator for {field_name}: {operator}")
            return False
            
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid numeric operator for {field_name} '{operator}': {e}")
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
        field_type = FIELD_CONFIG.get(field_name)
        
        # Skip NONE type fields (e.g., NeverMatch)
        if field_type == FieldType.NONE:
            continue
        
        field_value = get_entry_field_value(entry, field_name)
        
        # Handle different field types
        if field_type == FieldType.NUMERIC:
            # Numeric comparison using operators
            try:
                numeric_value = int(field_value)
                if _match_numeric_operator(numeric_value, pattern, field_name):
                    return True
            except ValueError:
                logger.warning(f"Invalid numeric value for {field_name}: {field_value}")
            continue
        
        elif field_type == FieldType.REGEX:
            # Regex pattern matching
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
    
    Rule processing order:
    1. Check deny_rules. If entry matches ANY deny rule, immediately block it
    2. Check allow_rules. If allow_rules are defined, entry MUST match at least one
    3. If no allow_rules defined, default to keep.
    
    Args:
        entry: Entry dictionary from Miniflux
        allow_rules: List of rules to allow (keep) entries
        deny_rules: List of rules to block entries
        
    Returns:
        True if entry should be processed, False otherwise
    """
    # Step 1: Check deny_rules first.If entry matches ANY deny rule, immediately block it
    if deny_rules and _match_any_rule(entry, deny_rules):
        return False
    
    # Step 2: Check allow_rules. If allow_rules are defined, entry MUST match at least one
    if allow_rules:
        return _match_any_rule(entry, allow_rules)
    
    # Step 3: No allow_rules defined, default to keep.
    return True
