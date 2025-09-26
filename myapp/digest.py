import time
import traceback
from datetime import datetime

from feedgen.feed import FeedGenerator
from flask import Response

from common import logger, DIGEST_FILE, config
from core.content_formater import to_html
from myapp import app


@app.route('/rss/digest', methods=['GET'])
def rss_ai_digest() -> Response:
    """
    AI Digest RSS Feed endpoint
    
    Generates an RSS feed containing daily AI-generated digest summaries.
    Loads digest content from temporary data file, generates RSS feed with
    welcome entry and daily digest entry, then clears the data file.
    
    Returns:
        Response: RSS XML feed content
        
    Raises:
        500: If feed generation fails
    """
    try:
        logger.info('Generating AI Digest RSS feed')
        
        feed_generator = _create_rss_feed_generator()
        _add_welcome_entry(feed_generator)
        
        digest_content = _load_digest_content()
        if digest_content:
            _add_digest_entry(feed_generator, digest_content)
            logger.debug(f'Successfully loaded digest content: {len(digest_content)} characters')
        else:
            logger.warning('No digest content available, RSS feed contains only welcome entry')
            
        rss_content = feed_generator.rss_str(pretty=True)

        return rss_content
        
    except Exception as e:
        logger.error(f'Failed to generate AI digest RSS feed: {e}')
        logger.error(traceback.format_exc())
        raise


def _load_digest_content() -> str:
    """
    Load AI digest content from data file and clear it
    
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


def _create_rss_feed_generator() -> FeedGenerator:
    """
    Create and configure the base RSS feed generator
    
    Returns:
        FeedGenerator: Configured feed generator with base settings
    """
    feed_generator = FeedGenerator()
    feed_generator.id(config.digest_url)
    feed_generator.title(config.digest_name)
    feed_generator.author({'name': 'Minifluxᴬᴵ'})
    feed_generator.subtitle('Powered by Minifluxᴬᴵ')
    feed_generator.link(href=config.digest_url, rel='self')
    return feed_generator


def _add_welcome_entry(feed_generator: FeedGenerator) -> None:
    """
    Add welcome entry to the RSS feed
    
    Args:
        feed_generator: Feed generator to add entry to
    """
    welcome_entry = feed_generator.add_entry()
    welcome_entry.id(config.digest_url)
    welcome_entry.link(href=config.digest_url)
    welcome_entry.author({'name': 'Minifluxᴬᴵ'})
    welcome_entry.title(f'Welcome to {config.digest_name}')


def _add_digest_entry(feed_generator: FeedGenerator, digest_content: str) -> None:
    """
    Add daily digest entry to the RSS feed
    
    Args:
        feed_generator: Feed generator to add entry to
        digest_content: Digest content in markdown format
    """
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
    """
    Get the time period for the digest entry
    
    Args:
        hour: The hour of the day
        
    Returns:
        The time period
    """
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
