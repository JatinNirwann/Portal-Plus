import os
import sys
import logging
import threading
import time
import signal
import asyncio
from typing import Optional
from dotenv import load_dotenv

from jiit_checker import JIITChecker
from telegram_notifier import TelegramNotifier

jiit_checker: Optional[JIITChecker] = None
notifier: Optional[TelegramNotifier] = None
running = True


def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('portalplus.log', encoding='utf-8')
        ]
    )

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('twilio').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def load_environment():
    load_dotenv()

    required_vars = [
        'JIIT_USERNAME', 'JIIT_PASSWORD',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    logging.info("Environment variables loaded successfully")


def initialize_services():
    global jiit_checker, notifier

    try:
        username = os.getenv('JIIT_USERNAME')
        password = os.getenv('JIIT_PASSWORD')
        jiit_checker = JIITChecker(username, password)

        notifier = TelegramNotifier()
        notifier.set_jiit_checker(jiit_checker)

        try:
            if jiit_checker.login():
                logging.info("JIIT portal login successful")
                notifier.send_message_sync(
                    "PortalPlus Started\n\n"
                    "Your portal monitoring is now active.\n\n"
                    "I'll alert you about:\n"
                    "- Low attendance warnings\n\n"
                    "Send /help anytime for commands."
                )
            else:
                logging.warning("JIIT portal login failed, but Telegram bot will still work")
                notifier.send_message_sync(
                    "PortalPlus Started (Limited Mode)\n\n"
                    "Telegram bot is active, but portal connection failed.\n\n"
                    "Portal login will be retried automatically.\n"
                    "Send /help for available commands."
                )
        except Exception as portal_error:
            logging.error(f"Portal login failed: {portal_error}")
            notifier.send_message_sync(
                "PortalPlus Started (Bot Only)\n\n"
                "Telegram bot is active, but portal connection is unavailable.\n\n"
                "Will keep trying to connect to portal.\n"
                "Send /help for available commands."
            )

        notifier.run_bot()
        logging.info("Services initialized (portal connection may be retried)")
        return True

    except Exception as e:
        logging.error(f"Failed to initialize core services: {e}")
        return False


def periodic_check():
    global running, jiit_checker, notifier

    logging.info("Starting periodic monitoring with dynamic interval checking")

    consecutive_failures = 0
    max_failures = 3

    while running:
        try:
            check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60)) * 60

            if not jiit_checker or not notifier:
                logging.error("Services not properly initialized")
                break

            logging.info(f"Starting periodic portal check (next check in {check_interval // 60} minutes)...")

            if not jiit_checker.ensure_logged_in():
                consecutive_failures += 1
                logging.warning(f"Portal connection failed (attempt {consecutive_failures}/{max_failures})")

                if consecutive_failures >= max_failures:
                    notifier.send_message_sync(
                        "Portal Connection Issues\n\n"
                        "Unable to connect to JIIT portal after multiple attempts.\n\n"
                        "Telegram bot remains active, but portal monitoring is temporarily disabled.\n"
                        "Will continue trying to reconnect..."
                    )
                    consecutive_failures = 0

                time.sleep(300)
                continue

            consecutive_failures = 0

            changes = jiit_checker.check_for_changes()

            if changes['attendance_below_threshold']:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(notifier.send_attendance_alert(changes['current_data']['attendance']))
                loop.close()

            attendance_pct = changes['current_data']['attendance']['attendance_percentage']

            logging.info(f"Check completed - Attendance: {attendance_pct:.1f}% (next check in {check_interval // 60} minutes)")

            sleep_start_time = time.time()
            while running and (time.time() - sleep_start_time) < check_interval:
                current_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60)) * 60
                if current_interval != check_interval:
                    logging.info(f"Interval changed from {check_interval // 60} to {current_interval // 60} minutes - adjusting schedule")
                    break
                time.sleep(min(30, check_interval - (time.time() - sleep_start_time)))

        except Exception as e:
            consecutive_failures += 1
            logging.error(f"Error during periodic check: {e}")

            if consecutive_failures >= max_failures and notifier:
                try:
                    notifier.send_message_sync(
                        "Monitoring Error\n\n"
                        "Experiencing technical difficulties with portal monitoring.\n\n"
                        "Telegram bot remains active. Will keep trying to restore monitoring..."
                    )
                    consecutive_failures = 0
                except:
                    pass

            time.sleep(300)


def signal_handler(signum, frame):
    global running, jiit_checker

    logging.info(f"Received signal {signum}, shutting down gracefully...")
    running = False

    if jiit_checker:
        jiit_checker.cleanup()

    sys.exit(0)


def get_jiit_checker() -> Optional[JIITChecker]:
    return jiit_checker


def main():
    try:
        setup_logging()
        logging.info("=== PortalPlus Starting ===")

        load_environment()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        if not initialize_services():
            logging.error("Failed to initialize services, exiting")
            sys.exit(1)

        checker_thread = threading.Thread(target=periodic_check, daemon=True)
        checker_thread.start()

        logging.info("Monitoring system started, checking portal periodically...")

        try:
            while running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Application interrupted by user")

    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logging.info("=== PortalPlus Stopped ===")


if __name__ == "__main__":
    main()
