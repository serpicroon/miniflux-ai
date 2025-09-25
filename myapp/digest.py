import time
import traceback
from datetime import datetime

import markdown
from feedgen.feed import FeedGenerator
from flask import Response

from common import logger, DIGEST_FILE
from myapp import app

FEED_TITLE = 'Digestᴬᴵ for you'
FEED_LINK = 'https://ai-digest.miniflux'


@app.route('/rss/ai-digest', methods=['GET'])
def miniflux_ai_digest() -> Response:
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
    feed_generator.id(FEED_LINK)
    feed_generator.title(FEED_TITLE)
    feed_generator.subtitle('Powered by miniflux-ai')
    feed_generator.author({'name': 'miniflux-ai'})
    feed_generator.link(href=FEED_LINK, rel='self')
    return feed_generator


def _add_welcome_entry(feed_generator: FeedGenerator) -> None:
    """
    Add welcome entry to the RSS feed
    
    Args:
        feed_generator: Feed generator to add entry to
    """
    welcome_entry = feed_generator.add_entry()
    welcome_entry.id(FEED_LINK)
    welcome_entry.link(href=FEED_LINK)
    welcome_entry.title('Welcome to Digestᴬᴵ')
    welcome_entry.description('Welcome to Digestᴬᴵ')


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
    current_hour = datetime.today().hour
    if current_hour < 12:
        time_period = 'Morning'
    elif current_hour < 14:
        time_period = 'Noon'
    elif current_hour < 18:
        time_period = 'Afternoon'
    else:
        time_period = 'Nightly'
    
    digest_entry = feed_generator.add_entry()
    digest_entry.id(f'{FEED_LINK}/{timestamp}')
    digest_entry.link(href=f'{FEED_LINK}/{timestamp}')
    digest_entry.title(f'{time_period} {FEED_TITLE} - {date_str}')
    digest_entry.description(markdown.markdown(digest_content))
    
    logger.info(f'Successfully added {time_period.lower()} digest entry for {date_str}')