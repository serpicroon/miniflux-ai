import concurrent.futures
import time
import traceback
from typing import Optional, List, Dict, Any, Tuple

from common import config
from common.logger import logger
from core.entry_processor import process_entry


def handle_unread_entries(miniflux_client) -> None:
    """
    Fetch and process unread entries from Miniflux using pagination
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        offset = 0
        limit = 500
        
        while True:
            total, entries = _fetch_entries_page(miniflux_client, offset, limit)
            if total == 0 or not entries:
                logger.debug(f"Stopping pagination, offset: {offset}, total: {total}")
                break
            
            process_entries_concurrently(miniflux_client, entries)
            
            offset += limit
            if offset >= total:
                logger.debug(f"Stopping pagination, offset: {offset}, total: {total}")
                break
        
    except Exception as e:
        logger.error(f"Failed to fetch and process unread entries: {e}")
        logger.error(traceback.format_exc())


def _fetch_entries_page(miniflux_client, offset: int, limit: int) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Fetch a single page of unread entries from Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
        offset: Starting offset for pagination
        limit: Maximum number of entries to fetch
        
    Returns:
        List of entries for current page, or None if no entries found
    """
    try:
        logger.info(f"Fetching unread entries page, offset: {offset}")

        kwargs = {
            'status': ['unread'],
            'order': 'id',
            'direction': 'desc',
            'offset': offset,
            'limit': limit
        }
        if config.entry_since > 0:
            kwargs['after'] = config.entry_since
        
        logger.debug(f"Fetching unread entries page with kwargs: {kwargs}")
        
        response = miniflux_client.get_entries(**kwargs)
        total = response.get('total', 0)
        entries = response.get('entries', [])
        
        logger.info(f"Fetched {len(entries)} unread entries, total: {total}, offset: {offset}")
        
        return total, entries
        
    except Exception as e:
        logger.error(f"Failed to fetch entries page from Miniflux: {e}")
        raise


def process_entries_concurrently(miniflux_client, entries: List[Dict[str, Any]]) -> None:
    """
    Process entries concurrently using thread pool
    
    Args:
        miniflux_client: Miniflux client instance
        entries: List of entries to process
    """
    max_workers = config.llm_max_workers
    logger.debug(f"Starting concurrent processing with {max_workers} workers")

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_entry, miniflux_client, entry) 
            for entry in entries
        ]
        _wait_for_completion(futures)
        
    elapsed_time = time.time() - start_time
    logger.info(f'Processing completed in {elapsed_time:.2f} seconds')


def _wait_for_completion(futures: List[concurrent.futures.Future]) -> None:
    """
    Wait for all tasks to complete and handle exceptions
    
    Args:
        futures: List of Future objects
    """
    completed_count = 0
    processed_count = 0
    failed_count = 0
    total_tasks = len(futures)
    
    for future in concurrent.futures.as_completed(futures):
        try:
            processed_agents = future.result()
            completed_count += 1
            if processed_agents:
                processed_count += 1
        except Exception:
            failed_count += 1
            logger.error(traceback.format_exc())
    
    logger.info(f"Processing summary - Total: {total_tasks}, Completed: {completed_count}, Processed: {processed_count}, Failed: {failed_count}")
