import concurrent.futures
import time
import traceback
from typing import Any

from common import config, shutdown_event
from common.logger import get_logger

from core.entry_processor import process_entry
from core.miniflux_client import get_miniflux_client

logger = get_logger(__name__)
# Global thread pool for concurrent entry processing
_executor: concurrent.futures.ThreadPoolExecutor | None = None


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
        max_workers=max_workers, thread_name_prefix="entry_processor"
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


PAGE_SIZE = 100


def handle_unread_entries() -> None:
    """
    Fetch and process unread entries from Miniflux using pagination.

    Processes at most `scheduler_entry_limit` entries per run (0 = unlimited),
    newest first (order=id desc). With a limit, only the newest entries are
    handled on every run; older unread entries beyond the limit are skipped
    again on the next run (they are never marked read here), so use a limit
    only to cap per-run work, not to eventually drain a backlog.

    The remaining per-run budget is folded into each page's size, so the API
    only returns as many entries as this run can still handle.
    """
    try:
        offset = 0
        processed = 0

        entry_limit = config.scheduler_entry_limit
        while True:
            if shutdown_event.is_set():
                break

            limit = PAGE_SIZE
            if entry_limit:
                limit = min(PAGE_SIZE, entry_limit - processed)
                if limit <= 0:
                    break

            total, entries = _fetch_entries_page(offset, limit)
            if not entries:
                logger.debug(f"Stopping pagination, offset: {offset}, total: {total}")
                break

            process_entries_concurrently(entries)
            processed += len(entries)

            offset += len(entries)
            if offset >= total:
                logger.debug(f"Stopping pagination, offset: {offset}, total: {total}")
                break

    except Exception as e:
        logger.error(f"Failed to fetch and process unread entries: {e}")
        logger.error(traceback.format_exc())


def _fetch_entries_page(offset: int, limit: int) -> tuple[int, list[dict[str, Any]]]:
    """
    Fetch a single page of unread entries from Miniflux

    Args:
        offset: Starting offset for pagination
        limit: Maximum number of entries to fetch

    Returns:
        Tuple of (total unread count, entries for the current page);
        entries is empty when there is nothing left to fetch
    """
    try:
        kwargs = {
            "status": ["unread"],
            "order": "id",
            "direction": "desc",
            "offset": offset,
            "limit": limit,
        }
        if config.scheduler_entry_window is not None:
            kwargs["after"] = int(time.time()) - config.scheduler_entry_window.seconds

        logger.debug(f"Fetching unread entries page with kwargs: {kwargs}")

        response = get_miniflux_client().get_entries(**kwargs)
        total = response.get("total", 0)
        entries = response.get("entries", [])

        logger.debug(
            f"Fetched {len(entries)} unread entries, total: {total}, offset: {offset}"
        )

        return total, entries

    except Exception as e:
        logger.error(f"Failed to fetch entries page from Miniflux: {e}")
        raise


def process_entries_concurrently(entries: list[dict[str, Any]]) -> None:
    """
    Process entries concurrently using thread pool

    Args:
        entries: List of entries to process
    """
    if shutdown_event.is_set():
        return

    logger.debug(
        f"Starting concurrent processing with {config.llm_max_workers} workers"
    )

    start_time = time.time()
    futures = [_executor.submit(process_entry, entry) for entry in entries]
    _wait_for_completion(futures)

    elapsed_time = time.time() - start_time
    logger.info(f"Processing completed in {elapsed_time:.2f} seconds")


def _wait_for_completion(futures: list[concurrent.futures.Future]) -> None:
    """
    Wait for all tasks to complete and handle exceptions

    Args:
        futures: List of Future objects
    """
    updated_count = 0
    partial_count = 0
    error_count = 0
    total_count = len(futures)

    for future in concurrent.futures.as_completed(futures):
        try:
            results = future.result()

            values = list(results.values())
            success = sum(r.is_success for r in values)
            error = sum(r.is_error for r in values)
            processed = success + error

            if processed == 0:
                continue
            elif success == processed:
                updated_count += 1
            elif error == processed:
                error_count += 1
            else:
                partial_count += 1
        except Exception:
            error_count += 1
            logger.error(traceback.format_exc())

    logger.info(
        f"Summary - Total: {total_count}, Updated: {updated_count}, "
        f"Partial: {partial_count}, Error: {error_count}"
    )
