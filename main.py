import os
import sys
import logging
import threading
import time
import signal
from typing import Optional
from dotenv import load_dotenv

from jiit_checker import JIITChecker
from notifier import WhatsAppNotifier, create_webhook_app

jiit_checker: Optional[JIITChecker] = None
notifier: Optional[WhatsAppNotifier] = None
running = True


def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('jiit_monitor.log', encoding='utf-8')
        ]
    )
    
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('twilio').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def load_environment():
    load_dotenv()
    
    required_vars = [
        'JIIT_USERNAME', 'JIIT_PASSWORD',
        'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
        'TWILIO_WHATSAPP_FROM', 'WHATSAPP_TO'
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
        
        notifier = WhatsAppNotifier()
        
        try:
            if jiit_checker.login():
                logging.info("JIIT portal login successful")
                notifier.send_message(
                    "JIIT Monitor Started\n\n"
                    "Your portal monitoring is now active!\n\n"
                    "I'll alert you about:\n"
                    "- Low attendance warnings\n"
                    "- New marks/grades\n"
                    "- Important notices\n\n"
                    "Send 'help' anytime for commands."
                )
            else:
                logging.warning("JIIT portal login failed, but WhatsApp bot will still work")
                notifier.send_message(
                    "JIIT Monitor Started (Limited Mode)\n\n"
                    "WhatsApp bot is active, but portal connection failed.\n\n"
                    "Portal login will be retried automatically.\n"
                    "Send 'help' for available commands."
                )
        except Exception as portal_error:
            logging.error(f"Portal login failed: {portal_error}")
            notifier.send_message(
                "JIIT Monitor Started (Bot Only)\n\n"
                "WhatsApp bot is active, but portal connection is unavailable.\n\n"
                "Will keep trying to connect to portal.\n"
                "Send 'help' for available commands."
            )
        
        logging.info("Services initialized (portal connection may be retried)")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize core services: {e}")
        return False


def periodic_check():
    global running, jiit_checker, notifier
    
    check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60)) * 60
    logging.info(f"Starting periodic checks every {check_interval // 60} minutes")
    
    consecutive_failures = 0
    max_failures = 3
    
    while running:
        try:
            if not jiit_checker or not notifier:
                logging.error("Services not properly initialized")
                break
            
            logging.info("Starting periodic portal check...")
            
            if not jiit_checker.ensure_logged_in():
                consecutive_failures += 1
                logging.warning(f"Portal connection failed (attempt {consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    notifier.send_message(
                        "Portal Connection Issues\n\n"
                        "Unable to connect to JIIT portal after multiple attempts.\n\n"
                        "WhatsApp bot remains active, but portal monitoring is temporarily disabled.\n"
                        "Will continue trying to reconnect..."
                    )
                    consecutive_failures = 0
                
                time.sleep(300)
                continue
            
            consecutive_failures = 0
            
            changes = jiit_checker.check_for_changes()
            
            if changes['attendance_below_threshold']:
                notifier.send_attendance_alert(changes['current_data']['attendance'])
            
            if changes['marks_changed']:
                notifier.send_marks_update(changes['current_data']['marks'])
            
            if changes['new_notices']:
                notifier.send_new_notices_alert(changes['new_notices'])
            
            # Log summary
            attendance_pct = changes['current_data']['attendance']['attendance_percentage']
            gpa = changes['current_data']['marks']['cgpa']
            notices_count = len(changes['current_data']['notices'])
            
            logging.info(
                f"Check completed - Attendance: {attendance_pct:.1f}%, "
                f"CGPA: {gpa}, Notices: {notices_count}"
            )
            
            time.sleep(check_interval)
            
        except Exception as e:
            consecutive_failures += 1
            logging.error(f"Error during periodic check: {e}")
            
            if consecutive_failures >= max_failures and notifier:
                try:
                    notifier.send_message(
                        "Monitoring Error\n\n"
                        "Experiencing technical difficulties with portal monitoring.\n\n"
                        "WhatsApp bot remains active. Will keep trying to restore monitoring..."
                    )
                    consecutive_failures = 0
                except:
                    pass
            
            time.sleep(300)


def run_webhook_server():
    global notifier
    
    if not notifier:
        logging.error("Notifier not initialized, cannot start webhook server")
        return
    
    try:
        app = create_webhook_app(notifier)
        host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        port = int(os.getenv('WEBHOOK_PORT', 5000))
        
        logging.info(f"Starting webhook server on {host}:{port}")
        
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except Exception as e:
        logging.error(f"Error running webhook server: {e}")


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
        logging.info("=== JIIT Portal Monitor Starting ===")
        
        load_environment()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if not initialize_services():
            logging.error("Failed to initialize services, exiting")
            sys.exit(1)
        
        checker_thread = threading.Thread(target=periodic_check, daemon=True)
        checker_thread.start()
        
        logging.info("All systems ready, starting webhook server...")
        run_webhook_server()
        
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logging.info("=== JIIT Portal Monitor Stopped ===")


if __name__ == "__main__":
    main()
