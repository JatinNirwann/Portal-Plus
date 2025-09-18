import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading
import time
import httpx
from jiit_checker import get_short_subject_name

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(30.0)
        )
        
        self.bot = Bot(token=self.bot_token)
        self.application = None
        self.jiit_checker = None
        self._loop = None
        self._loop_thread = None
        self._start_background_loop()
        logger.info("Telegram notifier initialized with proper connection management")

    def _start_background_loop(self):
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
        
        while self._loop is None:
            time.sleep(0.01)

    def _run_async(self, coro):
        if self._loop and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            try:
                return future.result(timeout=30.0)
            except Exception as e:
                logger.error(f"Async operation failed: {e}")
                raise
        else:
            raise RuntimeError("Background event loop is not running")

    async def send_message(self, message: str, parse_mode=None):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"Telegram message sent successfully")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    def send_message_sync(self, message: str):
        try:
            self._run_async(self.send_message(message))
        except Exception as e:
            logger.error(f"Error in sync message send: {e}")

    def cleanup(self):
        try:
            if self.http_client:
                self._run_async(self.http_client.aclose())
            if self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._loop.stop)
            logger.info("Telegram notifier cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def send_attendance_alert(self, attendance_data: Dict[str, Any]):
        try:
            attendance_pct = attendance_data.get('attendance_percentage', 0)
            subjects = attendance_data.get('subjects', {})

            message = f"Low Attendance Alert\n\n"
            message += f"Overall Attendance: {attendance_pct:.1f}%\n\n"

            low_subjects = []
            for subject, data in subjects.items():
                percentage = data.get('percentage', 0)
                if percentage < 75:
                    short_name = get_short_subject_name(subject)
                    low_subjects.append(f"- {short_name}: {percentage:.1f}%")

            if low_subjects:
                message += "Subjects below 75%:\n"
                message += "\n".join(low_subjects)
            else:
                message += "All subjects above 75%"

            await self.send_message(message, parse_mode=None)

        except Exception as e:
            logger.error(f"Error sending attendance alert: {e}")

    def send_attendance_alert_sync(self, attendance_data: Dict[str, Any]):
        try:
            self._run_async(self.send_attendance_alert(attendance_data))
        except Exception as e:
            logger.error(f"Error in sync attendance alert send: {e}")

    async def send_marks_update(self, marks_data: Dict[str, Any]):
        try:
            cgpa = marks_data.get('cgpa', 0.0)
            sgpa = marks_data.get('sgpa', 0.0)
            subjects = marks_data.get('subjects', {})

            message = f"Marks Update\n\n"
            message += f"CGPA: {cgpa:.2f}\n"
            message += f"SGPA: {sgpa:.2f}\n\n"

            if subjects:
                message += "Subject Updates:\n"
                for subject, marks in list(subjects.items())[:5]:
                    short_name = get_short_subject_name(subject)
                    if isinstance(marks, dict):
                        grade = marks.get('grade', 'N/A')
                        marks_val = marks.get('marks', 'N/A')
                        message += f"- {short_name}: {marks_val} ({grade})\n"
                    else:
                        message += f"- {short_name}: {marks}\n"

            await self.send_message(message, parse_mode=None)

        except Exception as e:
            logger.error(f"Error sending marks update: {e}")

    async def send_new_notices_alert(self, notices: List[Dict[str, Any]]):
        try:
            if not notices:
                return

            message = f"New Notices\n\n"

            for notice in notices[:3]:
                title = notice.get('title', 'No Title')[:60]
                date = notice.get('date', 'No Date')
                message += f"- {title}\n"
                message += f"  Date: {date}\n\n"

            if len(notices) > 3:
                message += f"... and {len(notices) - 3} more notices"

            await self.send_message(message, parse_mode=None)

        except Exception as e:
            logger.error(f"Error sending notices alert: {e}")

    def send_new_notices_alert_sync(self, notices: List[Dict[str, Any]]):
        try:
            self._run_async(self.send_new_notices_alert(notices))
        except Exception as e:
            logger.error(f"Error in sync notices alert send: {e}")

    def set_jiit_checker(self, jiit_checker):
        self.jiit_checker = jiit_checker

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_msg = (
            "Welcome to PortalPlus!\n\n"
            "I'm your JIIT portal monitoring assistant.\n\n"
            "I monitor:\n"
            "- Attendance levels\n"
            "- Marks and grades\n"
            "- Important notices\n\n"
            "Available Commands:\n"
            "/help - Show all commands\n"
            "/attendance - Check attendance\n"
            "/interval - Set check interval\n"
            "/status - System status\n\n"
            "Monitoring is now active."
        )
        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_msg = (
            "<b>PortalPlus Help</b>\n\n"
            "<b>Available Commands:</b>\n\n"
            "<b>/start</b> - Welcome message\n"
            "<b>/help</b> - Show this help\n"
            "<b>/attendance</b> - Check attendance\n"
            "<b>/interval [minutes]</b> - Set check interval\n"
            "<b>/status</b> - Bot status"
        )
        await update.message.reply_text(help_msg, parse_mode='HTML')

    async def attendance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not self.jiit_checker:
                await update.message.reply_text("Portal checker not available")
                return

            await update.message.reply_text("Fetching attendance data...")

            attendance_data = self.jiit_checker.fetch_attendance()
            attendance_pct = attendance_data.get('attendance_percentage', 0)
            subjects = attendance_data.get('subjects', {})

            message = f"Attendance Report\n\n"

            if subjects:
                message += "Subject-wise:\n"
                for subject, data in list(subjects.items())[:8]:
                    short_name = get_short_subject_name(subject)
                    percentage = data.get('percentage', 0)

                    message += f"<b>{short_name}</b>:  {percentage:.1f}%\n"

            await update.message.reply_text(message, parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error in attendance command: {e}")
            await update.message.reply_text("Error fetching attendance data")

    async def interval_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                current_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60))
                await update.message.reply_text(
                    f"Current check interval: {current_interval} minutes\n\n"
                    f"Usage: /interval [minutes]\n"
                    f"Example: /interval 30\n\n"
                    f"Valid range: 5 to 1440 minutes (24 hours)"
                )
                return

            try:
                new_interval = int(context.args[0])

                if new_interval < 5:
                    await update.message.reply_text(
                        f"Error: {new_interval} minutes is too low\n\n"
                        f"Minimum interval is 5 minutes\n"
                        f"Please use: /interval 5 or higher"
                    )
                    return

                if new_interval > 1440:
                    await update.message.reply_text(
                        f"Error: {new_interval} minutes is too high\n\n"
                        f"Maximum interval is 1440 minutes (24 hours)\n"
                        f"Please use: /interval 1440 or lower"
                    )
                    return

                os.environ['CHECK_INTERVAL_MINUTES'] = str(new_interval)

                env_path = os.path.join(os.path.dirname(__file__), '.env')

                try:
                    with open(env_path, 'r') as f:
                        env_content = f.read()

                    lines = env_content.split('\n')
                    updated_lines = []
                    found = False

                    for line in lines:
                        if line.startswith('CHECK_INTERVAL_MINUTES='):
                            updated_lines.append(f'CHECK_INTERVAL_MINUTES={new_interval}')
                            found = True
                        else:
                            updated_lines.append(line)

                    if not found:
                        updated_lines.append(f'CHECK_INTERVAL_MINUTES={new_interval}')

                    with open(env_path, 'w') as f:
                        f.write('\n'.join(updated_lines))

                except FileNotFoundError:
                    logger.warning(f".env file not found at {env_path}, only updating environment variable")
                except PermissionError:
                    logger.error(f"Permission denied writing to {env_path}")
                    await update.message.reply_text(
                        f"Warning: Updated runtime interval to {new_interval} minutes,\n"
                        f"but couldn't save to .env file (permission denied).\n\n"
                        f"Changes will be lost on restart."
                    )
                    return
                    f.write('\n'.join(updated_lines))

                await update.message.reply_text(
                    f"Success: Check interval updated to {new_interval} minutes\n\n"
                    f"Portal will be checked every {new_interval} minutes\n"
                    f"Changes are now active!"
                )

            except ValueError:
                await update.message.reply_text(
                    f"Error: '{context.args[0]}' is not a valid number\n\n"
                    f"Please enter a number between 5 and 1440\n"
                    f"Example: /interval 30"
                )

        except Exception as e:
            logger.error(f"Error in interval command: {e}")
            await update.message.reply_text("Error updating interval. Please try again.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        checker_status = "Online" if self.jiit_checker else "Offline"
        current_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60))

        message = (
            "PortalPlus Status\n\n"
            f"Bot Status: Online\n"
            f"Portal Checker: {'Online' if self.jiit_checker else 'Offline'}\n"
            f"Monitoring: Active\n"
            f"Check Interval: {current_interval} minutes (live updates)\n\n"
            "Last updated: Just now"
        )
        await update.message.reply_text(message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text.lower().strip()

        if message_text.isdigit():
            number = int(message_text)
            if number < 5:
                await update.message.reply_text(
                    f"Did you mean to set interval to {number} minutes?\n\n"
                    f"Minimum interval is 5 minutes\n"
                    f"Use: /interval 5 or higher"
                )
            elif number > 1440:
                await update.message.reply_text(
                    f"Did you mean to set interval to {number} minutes?\n\n"
                    f"Maximum interval is 1440 minutes (24 hours)\n"
                    f"Use: /interval {number} (if valid) or /interval 1440"
                )
            else:
                await update.message.reply_text(
                    f"Did you mean to set interval to {number} minutes?\n\n"
                    f"Use the command: /interval {number}"
                )
            return

        if any(word in message_text for word in ['attendance', 'attend']):
            await self.attendance_command(update, context)
        elif any(word in message_text for word in ['interval', 'time', 'check']):
            await self.interval_command(update, context)
        elif any(word in message_text for word in ['help', 'command']):
            await self.help_command(update, context)
        else:
            quick_help = (
                "Quick Help\n\n"
                "Try these commands:\n"
                "/attendance - Check attendance\n"
                "/interval - Set check interval\n"
                "/help - Full help menu"
            )
            await update.message.reply_text(quick_help)

    def setup_bot(self):
        self.application = Application.builder().token(self.bot_token).build()

        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("attendance", self.attendance_command))
        self.application.add_handler(CommandHandler("interval", self.interval_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("Telegram bot handlers set up")

    def run_bot(self):
        def bot_thread():
            try:
                logger.info("Starting Telegram bot...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.application.run_polling(drop_pending_updates=True)
            except Exception as e:
                logger.error(f"Error running Telegram bot: {e}")

        if not self.application:
            self.setup_bot()

        bot_thread_obj = threading.Thread(target=bot_thread, daemon=True)
        bot_thread_obj.start()
        logger.info("Telegram bot thread started")
