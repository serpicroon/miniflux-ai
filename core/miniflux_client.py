import time
import traceback
from functools import cache

import miniflux

from common import config
from common.logger import get_logger

logger = get_logger(__name__)


@cache
def get_miniflux_client() -> miniflux.Client:
    """
    Get or create Miniflux client connection (Singleton).
    The connection is established on the first call, not at import time.
    """
    client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
    
    while True:
        try:
            client.me()
            logger.info('Successfully connected to Miniflux!')
            return client
        except Exception as e:
            logger.error(f'Cannot connect to Miniflux: {e}')
            logger.debug(traceback.format_exc())
            time.sleep(3)
