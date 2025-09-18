import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import threading
import time
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
        self.bot = Bot(token=self.bot_token)
        self.application = None
        self.jiit_checker = None
        self._loop = None
        self._loop_thread = None
        self._running = False
        self._start_background_loop()
        logger.info("Telegram notifier initialized")

    def _start_background_loop(self):
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._running = True
            self._loop.run_forever()
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
        while self._loop is None or not self._running:
            time.sleep(0.01)

    def _run_async(self, coro):
        if self._loop and not self._loop.is_closed() and self._running:
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
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parse_mode)
            logger.info("Telegram message sent successfully")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    def send_message_sync(self, message: str, parse_mode='HTML'):
        try:
            self._run_async(self.send_message(message, parse_mode))
        except Exception as e:
            logger.error(f"Error in sync message send: {e}")

    def cleanup(self):
        try:
            self._running = False
            if self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=5)
            logger.info("Telegram notifier cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def send_attendance_alert(self, attendance_data: Dict[str, Any]):
        try:
            attendance_pct = attendance_data.get('attendance_percentage', 0)
            subjects = attendance_data.get('subjects', {})

            message = f"<b> Low Attendance Alert</b>\n\n"

            low_subjects = []
            for subject, data in subjects.items():
                percentage = data.get('percentage', 0)
                if percentage < 75:
                    low_subjects.append((subject, percentage))

            if low_subjects:
                message += "<pre>"
                message += "┌─────────────────┬────────────┐\n"
                message += "│ Subject         │ Attendance │\n"
                message += "├─────────────────┼────────────┤\n"

                for subject, percentage in low_subjects[:8]:  # Limit to 8 subjects
                    short_name = get_short_subject_name(subject)
                    if len(short_name) > 15:
                        short_name = short_name[:12] + "..."
                    message += f"│ {short_name:<15} │ {percentage:>8.1f}%  │\n"

                message += "└─────────────────┴────────────┘"
                message += "</pre>"
                if attendance_pct >= 65:
                    status_text = "Warning"
                else:
                    status_text = "Critical"

                message += f"\n<b>Status: {status_text}</b> - {len(low_subjects)} subject(s) below 75%"
            else:
                message += "<b>All subjects above 75%</b>"

            await self.send_message(message, parse_mode='HTML')
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
            message = f"Marks Update\n\nCGPA: {cgpa:.2f}\nSGPA: {sgpa:.2f}\n\n"
            if subjects:
                message += "Subject Updates:\n"
                for subject, marks in list(subjects.items())[:5]:
                    short_name = get_short_subject_name(subject)
                    if isinstance(marks, dict):
                        marks_val = marks.get('marks', 'N/A')
                        message += f"- {short_name}: {marks_val}\n"
                    else:
                        message += f"- {short_name}: {marks}\n"
            await self.send_message(message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error sending marks update: {e}")

    async def send_new_notices_alert(self, notices: List[Dict[str, Any]]):
        try:
            if not notices:
                return
            message = "New Notices\n\n"
            for notice in notices[:3]:
                title = notice.get('title', 'No Title')[:60]
                date = notice.get('date', 'No Date')
                message += f"- {title}\n  Date: {date}\n\n"
            if len(notices) > 3:
                message += f"... and {len(notices) - 3} more notices"
            await self.send_message(message, parse_mode='HTML')
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
        welcome_msg = "Welcome to PortalPlus!\n\nI'm your JIIT portal monitoring assistant.\n\nI monitor:\n- Attendance levels\n- Marks\n- Important notices\n\nAvailable Commands:\n/help - Show all commands\n/attendance - Check attendance\n/interval - Set check interval\n/status - System status\n\nMonitoring is now active."
        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_msg = "<b>PortalPlus Help</b>\n\n<b>Available Commands:</b>\n\n<b>/start</b> - Welcome message\n<b>/help</b> - Show this help\n<b>/attendance</b> - Check attendance\n<b>/marks</b> - Check semester marks\n<b>/interval [minutes]</b> - Set check interval\n<b>/status</b> - Bot status"
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

            message = f"<b>Attendance Report</b>\n\n"

            if subjects:
                message += "<pre>"
                message += "┌─────────────────┬────────────┐\n"
                message += "│ Subject         │ Attendance │\n"
                message += "├─────────────────┼────────────┤\n"

                for subject, data in list(subjects.items())[:8]:
                    short_name = get_short_subject_name(subject)
                    if len(short_name) > 15:
                        short_name = short_name[:12] + "..."

                    percentage = data.get('percentage', 0)
                    message += f"│ {short_name:<15} │ {percentage:>8.1f}%  │\n"

                message += "└─────────────────┴────────────┘"
                message += "</pre>"

                if attendance_pct >= 85:
                    status_text = "Excellent"
                elif attendance_pct >= 75:
                    status_text = "Good"
                elif attendance_pct >= 65:
                    status_text = "Average"
                else:
                    status_text = "Low"

                message += f"\n\n<b>Status: {status_text}</b>"

            await update.message.reply_text(message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in attendance command: {e}")
            await update.message.reply_text("Error fetching attendance data")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        # Handle any future callback queries here
        await query.edit_message_text("This feature is not currently available.")

    async def marks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not self.jiit_checker:
                await update.message.reply_text("Portal checker not available")
                return

            user_id = update.effective_user.id
            await update.message.reply_text("Fetching marks for current semester...")

            semesters = self.jiit_checker.fetch_marks_semesters()
            if not semesters:
                await update.message.reply_text("No semesters found\n\nThis could mean:\n• No academic records available\n• Portal connection issue\n• Data not yet uploaded")
                return

            # Automatically select the first (current/latest) semester
            semester_name = semesters[0]
            loading_text = f"Fetching marks for {semester_name}..."
            await update.message.reply_text(loading_text)

            self.jiit_checker.select_marks_semester(semester_name)
            marks = self.jiit_checker.get_current_marks()

            if marks and marks['subjects']:
                header_text = f"<b>Marks for {semester_name}</b>\n\n"
                marks_text = header_text

                marks_text += "<pre>"
                marks_text += "┌─────────────────┬────────┐\n"
                marks_text += "│ Subject         │ T1     │\n"
                marks_text += "├─────────────────┼────────┤\n"

                subjects_shown = 0
                for subject, mark_data in marks['subjects'].items():
                    if subjects_shown >= 10:  # Limit to 10 subjects to avoid message length limits
                        marks_text += "│ ... and more subjects ...              │\n"
                        break

                    short_name = get_short_subject_name(subject)
                    if len(short_name) > 15:
                        short_name = short_name[:12] + "..."

                    t1_marks = mark_data.get('t1', 0)

                    if isinstance(t1_marks, str):
                        t1_display = f"{t1_marks:>6}"
                    else:
                        t1_display = f"{t1_marks:>6.1f}"

                    marks_text += f"│ {short_name:<15} │ {t1_display} │\n"
                    subjects_shown += 1

                marks_text += "└─────────────────┴────────┘"
                marks_text += "</pre>\n\n"

                total_subjects = len(marks['subjects'])
                marked_count = sum(1 for m in marks['subjects'].values() if (isinstance(m.get('t1', 0), (int, float)) and m.get('t1', 0) > 0) or (isinstance(m.get('t1'), str) and m.get('t1', '').strip()))
                pending_count = total_subjects - marked_count

                marks_text += f"<b>📊 Summary for {semester_name}:</b>\n"
                marks_text += f"Total Subjects: {total_subjects}\n"
                if marked_count > 0:
                    marks_text += f"With T1 Marks: {marked_count}\n"
                if pending_count > 0:
                    marks_text += f"Pending: {pending_count}\n"

                marks_text += f"\n<i>Last updated: {time.strftime('%Y-%m-%d %H:%M', time.localtime(marks.get('last_updated', time.time())))}</i>"
                await update.message.reply_text(marks_text, parse_mode='HTML')
            else:
                await update.message.reply_text(f"No marks found for {semester_name}\n\nThis could mean:\n• Marks haven't been uploaded yet\n• Semester data is not available\n• There might be an issue with the portal")

        except Exception as e:
            logger.error(f"Error in marks command: {e}")
            await update.message.reply_text("Error fetching marks\n\nPlease try again later or contact support if the issue persists.")

    async def interval_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                current_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60))
                await update.message.reply_text(f"Current check interval: {current_interval} minutes\n\nUsage: /interval [minutes]\nExample: /interval 30\n\nValid range: 5 to 1440 minutes (24 hours)")
                return
            try:
                new_interval = int(context.args[0])
                if new_interval < 5:
                    await update.message.reply_text(f"Error: {new_interval} minutes is too low\n\nMinimum interval is 5 minutes\nPlease use: /interval 5 or higher")
                    return
                if new_interval > 1440:
                    await update.message.reply_text(f"Error: {new_interval} minutes is too high\n\nMaximum interval is 1440 minutes (24 hours)\nPlease use: /interval 1440 or lower")
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
                    logger.warning(".env file not found, only updating environment variable")
                except PermissionError:
                    logger.error("Permission denied writing to .env file")
                    await update.message.reply_text(f"Warning: Updated runtime interval to {new_interval} minutes,\nbut couldn't save to .env file (permission denied).\n\nChanges will be lost on restart.")
                    return
                await update.message.reply_text(f"Success: Check interval updated to {new_interval} minutes\n\nPortal will be checked every {new_interval} minutes\nChanges are now active!")
            except ValueError:
                await update.message.reply_text(f"Error: '{context.args[0]}' is not a valid number\n\nPlease enter a number between 5 and 1440\nExample: /interval 30")
        except Exception as e:
            logger.error(f"Error in interval command: {e}")
            await update.message.reply_text("Error updating interval. Please try again.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        checker_status = "Online" if self.jiit_checker else "Offline"
        current_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', 60))
        message = f"PortalPlus Status\n\nBot Status: Online\nPortal Checker: {checker_status}\nMonitoring: Active\nCheck Interval: {current_interval} minutes (live updates)\n\nLast updated: Just now"
        await update.message.reply_text(message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text.lower().strip()
        if message_text.isdigit():
            number = int(message_text)
            if number < 5:
                await update.message.reply_text(f"Did you mean to set interval to {number} minutes?\n\nMinimum interval is 5 minutes\nUse: /interval 5 or higher")
            elif number > 1440:
                await update.message.reply_text(f"Did you mean to set interval to {number} minutes?\n\nMaximum interval is 1440 minutes (24 hours)\nUse: /interval {number} (if valid) or /interval 1440")
            else:
                await update.message.reply_text(f"Did you mean to set interval to {number} minutes?\n\nUse the command: /interval {number}")
            return
        if any(word in message_text for word in ['attendance', 'attend']):
            await self.attendance_command(update, context)
        elif any(word in message_text for word in ['interval', 'time', 'check']):
            await self.interval_command(update, context)
        elif any(word in message_text for word in ['help', 'command']):
            await self.help_command(update, context)
        else:
            quick_help = "Quick Help\n\nTry these commands:\n/attendance - Check attendance\n/interval - Set check interval\n/help - Full help menu"
            await update.message.reply_text(quick_help)

    def setup_bot(self):
        self.application = Application.builder().token(self.bot_token).build()
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("attendance", self.attendance_command))
        self.application.add_handler(CommandHandler("marks", self.marks_command))
        self.application.add_handler(CommandHandler("interval", self.interval_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("Telegram bot handlers set up")

    def run_bot(self):
        def bot_thread():
            try:
                logger.info("Starting Telegram bot...")
                if not self.application:
                    self.setup_bot()
                async def run_polling():
                    try:
                        await self.application.initialize()
                        await self.application.start()
                        logger.info("Telegram bot started successfully")
                        await self.application.updater.start_polling(drop_pending_updates=True)
                        logger.info("Telegram bot polling started")
                        while True:
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error in polling: {e}")
                    finally:
                        try:
                            await self.application.stop()
                            await self.application.shutdown()
                        except Exception as e:
                            logger.error(f"Error during shutdown: {e}")
                asyncio.run(run_polling())
            except Exception as e:
                logger.error(f"Error running Telegram bot: {e}")
        bot_thread_obj = threading.Thread(target=bot_thread, daemon=True)
        bot_thread_obj.start()
        logger.info("Telegram bot thread started")
