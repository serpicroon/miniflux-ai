import re
import mistune
import warnings
from typing import Dict, Tuple
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from bs4 import MarkupResemblesLocatorWarning
import tiktoken

from common import config

MARKER = '<a id="mfai-{0}" href="#mfai-{0}"></a>'
MARKER_PATTERN = r'<a\s+id="mfai-([^"]+)"\s+href="#mfai-[^"]+"[^>]*></a>'
_LEGACY_MARKER_PATTERN = r'<div data-ai-agent="([^"]+)" style="display: none;"></div>'

_TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")

_MISTUNE_INSTANCE = mistune.create_markdown(escape=False, hard_wrap=True, plugins=[
    'strikethrough',
    'table',
    'footnotes',
])

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

_CACHE_KEY = '_mfai_cache'


def _get_cache(entry: Dict) -> Dict:
    """Get or create cache dict for entry (internal use only)"""
    if _CACHE_KEY not in entry:
        entry[_CACHE_KEY] = {}
    return entry[_CACHE_KEY]


def get_clean_content(html_content: str) -> str:
    """
    Get clean content from HTML content.
    
    Args:
        html_content: HTML formatted content
        
    Returns:
        Clean content
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove invisible content: script, style, noscript, iframe, etc.
    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()
    
    return soup.get_text(separator=' ', strip=True)


def get_content_text(entry: Dict) -> str:
    """
    Get plain text content from entry with caching.
    
    This function strips HTML tags and caches the result in the entry
    to avoid repeated parsing when multiple rules check the same content.
    
    Args:
        entry: Entry dictionary (may be modified to add cache)
        
    Returns:
        Plain text content with HTML tags stripped
    """
    cache = _get_cache(entry)
    cache_key = 'content_text'
    
    if cache_key not in cache:
        html_content = entry.get('content', '')
        cache[cache_key] = get_clean_content(html_content)
    
    return cache[cache_key]


def get_content_length(entry: Dict) -> int:
    """
    Get the token count of entry content using tiktoken (OpenAI's tokenizer).
    
    This function uses tiktoken to count tokens, which provides:
    - Fair counting across different languages (CJK and Latin scripts)
    - Alignment with LLM processing units
    - Natural word boundary awareness (spaces preserved)
    
    The result is cached in the entry to avoid repeated tokenization.

    Args:
        entry: Entry dictionary (may be modified to add cache)

    Returns:
        Number of tokens in the content.
    """
    cache = _get_cache(entry)
    cache_key = 'content_length'
    
    if cache_key not in cache:
        content_text = get_content_text(entry)
        content_text = ' '.join(content_text.split())
        tokens = _TIKTOKEN_ENCODER.encode(content_text, disallowed_special=())
        cache[cache_key] = len(tokens)
    
    return cache[cache_key]


def to_markdown(content: str) -> str:
    """
    Convert content to markdown format
    
    Args:
        content: Raw content (HTML or plain text)
        
    Returns:
        Markdown formatted content
    """
    return md(content)


def to_html(content: str) -> str:
    """
    Convert markdown formatted content to HTML format
    
    Args:
        content: Markdown formatted content
        
    Returns:
        HTML formatted content
    """
    return _MISTUNE_INSTANCE(content)


def parse_entry_content(content: str) -> Tuple[str, Dict[str, str]]:
    """
    Parse entry content to extract original content and existing agent results
    
    Args:
        content: Full content including agent results and markers
        
    Returns:
        Tuple of (original_content, existing_agent_content_dict)
    """
    # Combined pattern to match both new and legacy markers
    combined_pattern = f'(?:{MARKER_PATTERN})|(?:{_LEGACY_MARKER_PATTERN})'
    matches = list(re.finditer(combined_pattern, content))
    
    if not matches:
        return content, {}
    
    agent_contents = {}
    
    for i, match in enumerate(matches):
        agent_name = match.group(1) or match.group(2)
        start_pos = match.start()
        
        # Extract content before this marker
        if i == 0:
            # First agent - content is from beginning to marker
            agent_content = content[:start_pos].strip()
        else:
            # Other agents - content is from previous marker end to current marker
            prev_marker_end = matches[i - 1].end()
            agent_content = content[prev_marker_end:start_pos].strip()
        
        if agent_content:
            agent_contents[agent_name] = agent_content
    
    # Extract original content (after the last marker)
    last_marker_end = matches[-1].end()
    original_content = content[last_marker_end:].strip()
    
    return original_content, agent_contents


def build_ordered_content(agent_contents: Dict[str, str], original_content: str) -> str:
    """
    Build final content with agent contents in proper order
    
    Args:
        agent_contents: Dictionary of agent_name to content
        original_content: Original article content
        
    Returns:
        Final ordered content string
    """
    if not agent_contents:
        return original_content
    
    ordered_parts = []
    
    for agent_name in config.agents.keys():
        if agent_name in agent_contents:
            ordered_parts.append(agent_contents[agent_name])
            ordered_parts.append(MARKER.format(agent_name))
    
    ordered_parts.append(original_content)
    
    return ''.join(ordered_parts)
