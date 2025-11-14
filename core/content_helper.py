import re
import mistune
import warnings
from typing import Dict, Tuple
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from bs4 import MarkupResemblesLocatorWarning
import tiktoken

from common import config

MARKER = '<div data-ai-agent="{}" style="display: none;"></div>'
MARKER_PATTERN = r'<div data-ai-agent="([^"]+)" style="display: none;"></div>'

_TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")

_MISTUNE_INSTANCE = mistune.create_markdown(escape=False, hard_wrap=True, plugins=[
    'strikethrough',
    'table',
    'footnotes',
])

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

def get_content_length(html_content: str) -> int:
    """
    Get the token count of content using tiktoken (OpenAI's tokenizer).
    
    This function uses tiktoken to count tokens, which provides:
    - Fair counting across different languages (CJK and Latin scripts)
    - Alignment with LLM processing units
    - Natural word boundary awareness (spaces preserved)

    Args:
        html_content: HTML formatted content.

    Returns:
        Number of tokens in the content.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove invisible content: script, style, noscript, iframe, etc.
    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()

    content_text = soup.get_text(separator=' ', strip=True)
    content_text = ' '.join(content_text.split())
    tokens = _TIKTOKEN_ENCODER.encode(content_text)
    return len(tokens)


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

    matches = list(re.finditer(MARKER_PATTERN, content))
    
    if not matches:
        return content, {}
    
    agent_contents = {}
    
    for i, match in enumerate(matches):
        agent_name = match.group(1)
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
