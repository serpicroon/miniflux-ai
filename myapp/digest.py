import traceback

from flask import Response

from common import logger
from core.digest_handler import generate_digest_rss
from myapp import app


@app.route('/rss/digest', methods=['GET'])
def rss_digest() -> Response:
    """
    AI Digest RSS Feed endpoint
    
    Generates an RSS feed containing daily AI-generated digest summaries.
    
    Returns:
        Response: RSS XML feed content
        
    Raises:
        500: If feed generation fails
    """
    try:
        digest_rss = generate_digest_rss()
        return Response(digest_rss, mimetype='application/rss+xml')
    except Exception as e:
        logger.error(f'Failed to generate AI digest RSS feed: {e}')
        logger.error(traceback.format_exc())
        raise
