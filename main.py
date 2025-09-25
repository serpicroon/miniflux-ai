import threading
import schedule
import signal
import os

from common import config, logger
from myapp import app
from core import handle_unread_entries, generate_daily_digest, init_digest_feed, miniflux_client

shutdown_event = threading.Event()

def my_schedule():
    if config.digest_schedule:
        init_digest_feed(miniflux_client)
        for digest_schedule in config.digest_schedule:
            schedule.every().day.at(digest_schedule).do(generate_daily_digest, miniflux_client)

    interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(handle_unread_entries, miniflux_client)
    schedule.run_all()

    while not shutdown_event.is_set():
        schedule.run_pending()
        shutdown_event.wait(1)

def my_flask():
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    logger.info("Application starting...")

    os.makedirs('data', exist_ok=True)

    signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
    signal.signal(signal.SIGTERM, lambda s, f: shutdown_event.set())

    flask_thread = threading.Thread(target=my_flask, daemon=True)
    schedule_thread = threading.Thread(target=my_schedule, daemon=False)
    
    flask_thread.start()
    schedule_thread.start()
    schedule_thread.join()

    logger.info("Application stopped...")
