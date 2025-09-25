import json
import time
import traceback
from typing import Any, Dict, List, Optional

from common.logger import logger
from common import config, SUMMARY_FILE_LOCK, SUMMARY_FILE, DIGEST_FILE
from miniflux import ClientError
from core.llm_client import get_completion

FEED_NAME = 'Digestᴬᴵ for you'


def init_digest_feed(miniflux_client) -> None:
    """
    Initialize AI digest feed if it doesn't exist in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        logger.debug('Checking if AI digest feed exists')
        
        feeds = miniflux_client.get_feeds()
        digest_feed_id = _find_digest_feed_id(feeds)
        
        if digest_feed_id is None:
            _create_digest_feed(miniflux_client)
        else:
            logger.debug(f'AI digest feed already exists with ID: {digest_feed_id}')
            
    except Exception as e:
        logger.error(f'Failed to initialize AI digest feed: {e}')
        raise


def _create_digest_feed(miniflux_client) -> None:
    """
    Create AI digest feed in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        feed_url = f"{config.digest_url}/rss/ai-digest"
        logger.debug(f'Creating AI digest feed with URL: {feed_url}')
        
        miniflux_client.create_feed(category_id=1, feed_url=feed_url)
        logger.info(f'Successfully created AI digest feed in Miniflux: {feed_url}')

    except ClientError as e:
        logger.error(f'Failed to create AI digest feed in Miniflux: {e.get_error_reason()}')
        raise
    except Exception as e:
        logger.error(f'Failed to create AI digest feed in Miniflux: {e}')
        raise


def generate_daily_digest(miniflux_client) -> None:
    """
    Generate daily digest from AI summaries and refresh corresponding feed
    
    Args:
        miniflux_client: Miniflux client instance for feed refresh
    """
    logger.info('Starting daily digest generation')
    
    try:
        summaries = _load_summaries()
        if not summaries:
            logger.info('No summaries found, skipping digest generation')
            return
            
        logger.info(f'Loaded {len(summaries)} summaries for processing')
        
        digest_content = _generate_digest_content(summaries)
        _save_digest_content(digest_content)
        _refresh_ai_digest_feed(miniflux_client)
        
        logger.info('Daily digest generation completed successfully')
        
    except Exception as e:
        logger.error(f'Failed to generate daily digest: {e}')
        logger.error(traceback.format_exc())


def _load_summaries() -> List[Dict[str, Any]]:
    """
    Load summaries from file
    
    Returns:
        List of summary dictionaries, empty list if file not found or invalid
    """
    with SUMMARY_FILE_LOCK:
        try:
            logger.debug(f'Loading and clearing summaries from {SUMMARY_FILE}')
            
            if not SUMMARY_FILE.exists():
                logger.debug('Summary file does not exist')
                return []
                
            # Read and parse summaries
            with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                summaries = [json.loads(line) for line in lines if line.strip()]

            return summaries
            
        except Exception as e:
            logger.error(f'Unexpected error loading summaries: {e}')
            logger.error(traceback.format_exc())
            return []
        
        finally:
            SUMMARY_FILE.write_text('', encoding='utf-8')


def _generate_digest_content(summaries: List[Dict[str, Any]]) -> str:
    """
    Generate digest content using LLM based on summaries
    
    Args:
        summaries: List of summary dictionaries
        
    Returns:
        Generated digest content string
    """
    try:
        contents = '\n'.join([summary['content'] for summary in summaries])
        
        # Generate greeting with current timestamp
        current_time = time.strftime('%B %d, %Y at %I:%M %p')
        logger.debug(f'Generating greeting for time: {current_time}')
        greeting = get_completion(config.digest_prompts['greeting'], current_time)
        
        logger.debug('Generating digest content from summaries')
        summary_digest = get_completion(config.digest_prompts['summary'], contents)
        
        # Combine all parts into final digest content
        response_content = f"{greeting}\n\n### 🌐Digest\n{summary_digest}"
        
        return response_content
        
    except Exception as e:
        logger.error(f'Failed to generate digest content: {e}')
        raise


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


def _refresh_ai_digest_feed(miniflux_client) -> None:
    """
    Find and refresh the AI digest feed in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        feeds = miniflux_client.get_feeds()
        digest_feed_id = _find_digest_feed_id(feeds)
        
        if digest_feed_id:
            logger.debug(f'Found AI digest feed with ID: {digest_feed_id}')
            miniflux_client.refresh_feed(digest_feed_id)
            logger.info('Successfully refreshed AI digest feed in Miniflux')
        else:
            # Feed should have been initialized at startup; avoid recreating to prevent potential issues
            logger.warning('AI digest feed not found in Miniflux')
            
    except Exception as e:
        logger.error(f'Failed to refresh AI digest feed: {e}')
        raise


def _find_digest_feed_id(feeds: List[Dict[str, Any]]) -> Optional[int]:
    """
    Find the AI digest feed ID from the list of feeds
    
    Args:
        feeds: List of feed dictionaries from Miniflux
        
    Returns:
        Feed ID if found, None otherwise
    """
    for feed in feeds:
        if FEED_NAME in feed.get('title', ''):
            return feed['id']
    return None
