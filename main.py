"""
Main entry point for the Miniflux-AI application.
"""
import datetime
import os
import signal
import sys
import threading
import traceback
from typing import NoReturn

import schedule

from app import create_app
from common import config, logger, shutdown_event
from core import handle_unread_entries, generate_daily_digest, init_digest_feed, get_miniflux_client
from core.entry_handler import initialize_executor, shutdown_executor


def run_flask_server() -> None:
    """Start the Flask web application server."""
    try:
        app = create_app()
        logger.info("Starting Flask server on 0.0.0.0:80")
        app.run(host='0.0.0.0', port=80, threaded=True)
    except Exception as e:
        logger.error(f"Flask server failed: {e}")
        logger.error(traceback.format_exc())
        shutdown_event.set()


def run_scheduler() -> None:
    """
    Start the background task scheduler.
    
    Schedules daily digest generation and periodic entry processing,
    then runs until shutdown_event is set.
    """
    try:
        if config.digest_schedule:
            init_digest_feed()
            for digest_time in config.digest_schedule:
                schedule.every().day.at(digest_time).do(generate_daily_digest)
                logger.info(f"Scheduled daily digest at {digest_time}")
        
        interval = 15 if config.miniflux_webhook_secret else 1
        unread_entries_job = schedule.every(interval).minutes.do(handle_unread_entries)
        logger.info(f"Scheduled entry processing every {interval} minute(s)")
        unread_entries_job.next_run = datetime.datetime.now()
        
        while not shutdown_event.is_set():
            schedule.run_pending()
            shutdown_event.wait(1)
            
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        logger.error(traceback.format_exc())
        shutdown_event.set()


def handle_shutdown(signum: int, frame) -> None:
    """Signal handler for graceful shutdown."""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    shutdown_event.set()


def initialize_application() -> None:
    """Initialize application components and resources."""
    try:
        os.makedirs('data', exist_ok=True)
        get_miniflux_client()
        initialize_executor()
        logger.info("Application initialized")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    logger.info("Signal handlers registered")


def cleanup_application() -> None:
    """Clean up application resources."""
    try:
        shutdown_executor()
        logger.info("Application resources cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        logger.error(traceback.format_exc())


def main() -> NoReturn:
    """Main application entry point."""
    logger.info("=" * 60)
    logger.info("Miniflux-AI Application Starting")
    logger.info("=" * 60)
    
    initialize_application()
    setup_signal_handlers()
    
    flask_thread = threading.Thread(
        target=run_flask_server,
        name="FlaskServer",
        daemon=True
    )
    
    schedule_thread = threading.Thread(
        target=run_scheduler,
        name="Scheduler",
        daemon=False
    )
    
    flask_thread.start()
    logger.info("Flask server thread started")
    
    schedule_thread.start()
    logger.info("Scheduler thread started")
    
    try:
        schedule_thread.join()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_event.set()
    
    cleanup_application()
    
    logger.info("=" * 60)
    logger.info("Miniflux-AI Application Stopped")
    logger.info("=" * 60)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
