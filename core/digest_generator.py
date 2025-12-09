import json
import re
import time
import traceback
from typing import Any, Dict, List, Optional

from common.logger import logger, log_entry_error
from common import config, SUMMARY_FILE_LOCK, SUMMARY_FILE, DIGEST_FILE
from core.llm_client import get_completion


def generate_digest_content() -> str | None:
    """
    Generate digest content using LLM based on summaries
        
    Returns:
        Generated digest content string
    """
    try:
        summaries = _load_summaries()
        if not summaries:
            logger.info('No summaries found, skipping digest generation')
            return None
            
        logger.info(f'Loaded {len(summaries)} summaries for digest generation')
        
        greeting = _generate_greeting()
        summary_digest = _generate_summary(summaries)

        # Combine all parts into final digest content
        response_content = f"{greeting}\n\n### 🌐Digest\n{summary_digest}"
        _save_digest_content(response_content)
        return response_content
        
    except Exception as e:
        logger.error(f'Failed to generate digest content: {e}')
        raise


def _generate_greeting() -> str:
    """
    Generate greeting with current timestamp
    
    Returns:
        Generated greeting string
        
    Raises:
        Exception: If both attempts fail
    """
    current_time = time.strftime('%B %d, %Y at %I:%M %p')
    logger.debug(f'Generating greeting for time: {current_time}')
    
    try:
        return get_completion(config.digest_prompts['greeting'], f"Current time: {current_time}", temperature=0.8)
    except Exception as e:
        logger.warning(f'Failed to generate greeting, retrying once: {e}')
        return get_completion(config.digest_prompts['greeting'], f"Current time: {current_time}", temperature=0.8)


def _generate_summary(summaries: List[Dict[str, Any]]) -> str:
    """
    Generate summary with entry links from LLM-processed summaries
    
    Args:
        summaries: List of summary dictionaries
        
    Returns:
        Generated summary content string with entry links
        
    Raises:
        Exception: If both attempts fail
    """
    logger.debug('Generating digest content from summaries')
    contents = '\n\n'.join(f'[{s["id"]}] {s["content"]}' for s in summaries)
    
    try:
        summary = get_completion(config.digest_prompts['summary'], contents)
    except Exception as e:
        logger.warning(f'Failed to generate summary, retrying once: {e}')
        summary = get_completion(config.digest_prompts['summary'], contents)
    
    summary_with_links = _apply_entry_links(summary, config.digest_entry_url)
    return summary_with_links


def _apply_entry_links(content: str, entry_url: str) -> str:
    """
    Transform [^ID] footnote references into superscript markdown links
    
    Args:
        content: Content string with [^ID] footnote references
        entry_url: URL template with {id} placeholder
        
    Returns:
        Content string with [^ID] footnote references replaced by entry links
    """
    def to_links(match: re.Match) -> str:
        ids = re.findall(r'\[\^(\d+)\]', match.group(0))
        links = ' '.join(f"[{id}]({entry_url.format(id=id)})" for id in ids)
        return f"<sup>{links}</sup>"
    
    return re.sub(r'(?:\[\^\d+\])+', to_links, content)


def save_summary(entry: Dict[str, Any], summary_content: str) -> None:
    """
    Save the summary entry to a temporary file for digest feature
    Each line contains one JSON object for better performance
    
    Args:
        entry: Original entry dictionary
        summary_content: Processed summary content
    """
    if not summary_content:
        return
    
    entry_data = {
        'id': entry['id'],
        'title': entry['title'],
        'url': entry['url'],
        'datetime': entry['created_at'],
        'content': summary_content
    }
    
    try:
        json_line = json.dumps(entry_data, ensure_ascii=False)

        with SUMMARY_FILE_LOCK:
            with open(SUMMARY_FILE, 'a', encoding='utf-8') as f:
                f.write(json_line + '\n')
            
    except Exception as e:
        log_entry_error(entry, message=f"Failed to save summary: {e}")
        logger.error(traceback.format_exc())


def _load_summaries() -> List[Dict[str, Any]]:
    """
    Load summaries from file with deduplication by entry ID
    Keep only the latest summary for each entry ID
    
    Returns:
        List of unique summary dictionaries, empty list if file not found or invalid
    """
    with SUMMARY_FILE_LOCK:
        try:
            logger.debug(f'Loading and clearing summaries from {SUMMARY_FILE}')
            
            if not SUMMARY_FILE.exists():
                logger.debug('Summary file does not exist')
                return []
            
            # Use dict to deduplicate by entry ID (last occurrence wins)
            unique_summaries: dict[int, Dict[str, Any]] = {}
            total_count = 0

            with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    summary = json.loads(line.strip())
                    unique_summaries[summary['id']] = summary
                    total_count += 1

            unique_count = len(unique_summaries)
            if total_count > unique_count:
                logger.info(
                    f'Deduplicated summaries: {total_count} -> {unique_count} '
                    f'({total_count - unique_count} duplicates removed)'
                )
            
            return list(unique_summaries.values())
            
        except Exception as e:
            logger.error(f'Unexpected error loading summaries: {e}')
            logger.error(traceback.format_exc())
            return []
        
        finally:
            SUMMARY_FILE.write_text('', encoding='utf-8')


def load_digest_content() -> str:
    """
    Load digest content from data file and clear it
    
    Returns:
        str: Digest content if available, empty string if file not found or empty
        
    Raises:
        Exception: If file operations fail
    """
    try:
        logger.debug(f'Loading digest content from {DIGEST_FILE}')
        
        if not DIGEST_FILE.exists():
            logger.warning('Digest content file does not exist')
            return ''

        content = DIGEST_FILE.read_text('utf-8')

        return content if content else ''
    except Exception as e:
        logger.error(f'Failed to load digest content: {e}')
        raise
    finally:
        DIGEST_FILE.write_text('', encoding='utf-8')


def _save_digest_content(content: str) -> None:
    """
    Save generated digest content to file
    
    Args:
        content: Generated digest content to save
    """
    try:
        DIGEST_FILE.write_text(content, encoding='utf-8')
        
    except Exception as e:
        logger.error(f'Failed to save digest content: {e}')
        raise


