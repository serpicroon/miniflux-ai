import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from feedgen.feed import FeedGenerator
from miniflux import ClientError

from common import logger, config
from core.digest_generator import generate_digest_content, load_digest_content
from core.content_formater import to_html

FEED_URL = f"{config.digest_url}/rss/digest"


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
            logger.debug(f'Digest feed already exists with ID: {digest_feed_id}')
            
    except Exception as e:
        logger.error(f'Failed to initialize AI digest feed: {e}')
        raise


def generate_daily_digest(miniflux_client) -> None:
    """
    Generate daily digest from AI summaries and refresh corresponding feed
    
    Args:
        miniflux_client: Miniflux client instance for feed refresh
    """
    logger.info('Starting daily digest generation')
    
    try:
        if generate_digest_content():
            _refresh_digest_feed(miniflux_client)
            logger.info('Daily digest generation completed successfully')
    except Exception as e:
        logger.error(f'Failed to generate daily digest: {e}')
        logger.error(traceback.format_exc())


def generate_digest_rss() -> str:
    """
    Generate RSS feed content
    
    Returns:
        RSS XML content as string
    """
    logger.info('Generating Digest RSS feed')
    
    feed_generator = _create_rss_feed_generator()
    _add_welcome_entry(feed_generator)
    
    digest_content = load_digest_content()
    if digest_content:
        _add_digest_entry(feed_generator, digest_content)
        logger.debug(f'Successfully loaded digest content: {len(digest_content)} characters')
    else:
        logger.debug('No digest content available, RSS feed contains only welcome entry')
        
    return feed_generator.rss_str(pretty=True)


def _create_rss_feed_generator() -> FeedGenerator:
    """Create and configure the base RSS feed generator"""
    feed_generator = FeedGenerator()
    feed_generator.id(config.digest_url)
    feed_generator.title(config.digest_name)
    feed_generator.author({'name': 'Minifluxᴬᴵ'})
    feed_generator.subtitle('Powered by Minifluxᴬᴵ')
    feed_generator.link(href=config.digest_url, rel='self')
    return feed_generator


def _add_welcome_entry(feed_generator: FeedGenerator) -> None:
    """Add welcome entry to the RSS feed"""
    welcome_entry = feed_generator.add_entry()
    welcome_entry.id(config.digest_url)
    welcome_entry.link(href=config.digest_url)
    welcome_entry.author({'name': 'Minifluxᴬᴵ'})
    welcome_entry.title(f'Welcome to {config.digest_name}')


def _add_digest_entry(feed_generator: FeedGenerator, digest_content: str) -> None:
    """Add daily digest entry to the RSS feed"""
    logger.debug('Adding daily digest entry to RSS feed')
    
    timestamp = time.strftime('%Y-%m-%d-%H-%M')
    date_str = time.strftime('%Y-%m-%d')
    time_period = _get_digest_time_period(datetime.today().hour)
    
    digest_entry = feed_generator.add_entry()
    digest_entry.id(f'{config.digest_url}/{timestamp}')
    digest_entry.author({'name': 'Minifluxᴬᴵ'})
    digest_entry.title(f'{time_period} Digest for you - {date_str}')
    digest_entry.description(to_html(digest_content))
    
    logger.info(f'Successfully added {time_period.lower()} digest entry for {date_str}')


def _get_digest_time_period(hour: int) -> str:
    """Get the time period for the digest entry"""
    if not 0 <= hour <= 23:
        raise ValueError("hour must be in 0..23")
    if 5 <= hour < 12:
        return "Morning"
    elif hour == 12:
        return "Midday"
    elif 13 <= hour < 18:
        return "Afternoon"
    elif 18 <= hour < 22:
        return "Evening"
    else:
        return "Nightly"


def _create_digest_feed(miniflux_client) -> None:
    """Create digest feed in Miniflux"""
    try:
        logger.debug(f'Creating AI digest feed with URL: {FEED_URL}')
        miniflux_client.create_feed(category_id=1, feed_url=FEED_URL)
        logger.info(f'Successfully created AI digest feed in Miniflux: {FEED_URL}')
    except ClientError as e:
        logger.error(f'Failed to create AI digest feed in Miniflux: {e.get_error_reason()}')
        raise
    except Exception as e:
        logger.error(f'Failed to create AI digest feed in Miniflux: {e}')
        raise


def _refresh_digest_feed(miniflux_client) -> None:
    """Find and refresh the AI digest feed in Miniflux"""
    try:
        feeds = miniflux_client.get_feeds()
        digest_feed_id = _find_digest_feed_id(feeds)
        
        if digest_feed_id:
            logger.debug(f'Found AI digest feed with ID: {digest_feed_id}')
            miniflux_client.refresh_feed(digest_feed_id)
            logger.info('Successfully refreshed AI digest feed in Miniflux')
        else:
            logger.warning('AI digest feed not found in Miniflux')
    except ClientError as e:
        logger.error(f'Failed to refresh AI digest feed in Miniflux: {e.get_error_reason()}')
        raise
    except Exception as e:
        logger.error(f'Failed to refresh AI digest feed: {e}')
        raise


def _find_digest_feed_id(feeds: List[Dict[str, Any]]) -> Optional[int]:
    """Find the AI digest feed ID from the list of feeds"""
    for feed in feeds:
        if FEED_URL == feed.get('feed_url', ''):
            return feed['id']
    return None
