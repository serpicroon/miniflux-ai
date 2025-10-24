import concurrent.futures
import time
import traceback
from typing import Optional, List, Dict, Any, Tuple

from common import config
from common.logger import logger
from core.entry_processor import process_entry

# Global thread pool for concurrent entry processing
_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None


def initialize_executor() -> concurrent.futures.ThreadPoolExecutor:
    """
    Get or create the global thread pool instance (singleton pattern)
    
    Returns:
        ThreadPoolExecutor: Global thread pool instance
    """
    global _executor
    if _executor is not None:
        logger.warning("Thread pool already initialized, skipping")
        return
    
    max_workers = config.llm_max_workers
    _executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix='entry_processor'
    )
    logger.info(f"Initialized thread pool with {max_workers} workers")


def shutdown_executor() -> None:
    """
    Shutdown the global thread pool (should be called on application exit)
    """
    global _executor
    if _executor is not None:
        logger.info("Shutting down thread pool")
        _executor.shutdown(wait=True)
        _executor = None


def handle_unread_entries(miniflux_client) -> None:
    """
    Fetch and process unread entries from Miniflux using pagination
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        offset = 0
        limit = 100
        
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
        
        logger.debug(f"Fetched {len(entries)} unread entries, total: {total}, offset: {offset}")
        
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
    logger.debug(f"Starting concurrent processing with {config.llm_max_workers} workers")

    start_time = time.time()
    futures = [
        _executor.submit(process_entry, miniflux_client, entry) 
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
