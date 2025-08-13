import os
import logging
from typing import Optional, Dict, Any
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)


def get_short_subject_name(full_name: str) -> str:
    name = full_name.split('(')[0].strip()
    
    subject_map = {
        'COMPUTER ORGANISATION AND ARCHITECTURE LAB': 'COA Lab',
        'COMPUTER ORGANISATION AND ARCHITECTURE': 'COA',
        'OPERATING SYSTEMS AND SYSTEMS PROGRAMMING LAB': 'OS Lab',
        'OPERATING SYSTEMS AND SYSTEMS PROGRAMMING': 'OS',
        'MINOR PROJECT-1': 'Minor Project',
        'MINOR PROJECT': 'Minor Project',
        'OPEN SOURCE SOFTWARE LAB': 'OSS Lab',
        'INFORMATION SECURITY LAB': 'Info Security Lab',
        'FUNDAMENTALS OF COMPUTER SECURITY': 'Computer Security',
        'INDIAN CONSTITUTION & TRADITIONAL KNOWLEDGE': 'Constitution',
        'FOUNDATIONS OF R SOFTWARE': 'R Programming',
        'Consumer Behaviour': 'Consumer Behavior',
        'DATABASE MANAGEMENT SYSTEMS LAB': 'DBMS Lab',
        'DATABASE MANAGEMENT SYSTEMS': 'DBMS',
        'SOFTWARE ENGINEERING': 'Software Eng',
        'COMPUTER NETWORKS LAB': 'Networks Lab',
        'COMPUTER NETWORKS': 'Networks',
        'WEB TECHNOLOGIES LAB': 'Web Tech Lab',
        'WEB TECHNOLOGIES': 'Web Tech',
        'ARTIFICIAL INTELLIGENCE': 'AI',
        'MACHINE LEARNING': 'ML',
        'DATA STRUCTURES LAB': 'DSA Lab',
        'DATA STRUCTURES': 'DSA',
        'ALGORITHMS': 'Algorithms',
        'PROGRAMMING': 'Programming',
        'MATHEMATICS': 'Math',
        'PHYSICS': 'Physics',
        'CHEMISTRY': 'Chemistry',
        'ENGLISH': 'English',
        'COMMUNICATIONS': 'Communication'
    }
    
    for full_subject, short_name in subject_map.items():
        if full_subject.lower() == name.lower():
            return short_name
    
    words = name.split()
    if len(words) <= 2:
        return name
    elif 'LAB' in name.upper():
        return f"{words[0]} Lab"
    else:
        return ' '.join(words[:2])


class WhatsAppNotifier:
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_from = os.getenv('TWILIO_WHATSAPP_FROM')
        self.whatsapp_to = os.getenv('WHATSAPP_TO')
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_from, self.whatsapp_to]):
            raise ValueError("Missing required Twilio configuration in .env file")
        
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("WhatsApp notifier initialized successfully")
    
    def send_message(self, message: str, to_number: Optional[str] = None) -> bool:
        try:
            recipient = to_number or self.whatsapp_to
            
            message_instance = self.client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=recipient
            )
            
            logger.info(f"WhatsApp message sent successfully. SID: {message_instance.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    def send_attendance_alert(self, attendance_data: Dict[str, Any]) -> bool:
        try:
            percentage = attendance_data['attendance_percentage']
            threshold = float(os.getenv('ATTENDANCE_THRESHOLD', 75))
            
            message = f"ATTENDANCE ALERT\n\n"
            message += f"Your attendance has dropped below {threshold}%!\n\n"
            message += f"Current Attendance: {percentage:.1f}%\n"
            message += f"Classes Attended: {attendance_data['attended_classes']}/{attendance_data['total_classes']}\n\n"
            
            message += "Subject-wise breakdown:\n"
            message += f"{'Subject':<20} {'%':<6}\n"
            message += f"{'-'*20} {'-'*6}\n"
            
            for subject, data in attendance_data['subjects'].items():
                short_name = get_short_subject_name(subject)
                message += f"{short_name:<20} {data['percentage']:>5.1f}%\n"
            
            message += f"\nAction Required: Attend more classes to improve your attendance!"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending attendance alert: {e}")
            return False
    
    def send_marks_update(self, marks_data: Dict[str, Any]) -> bool:
        try:
            message = f"NEW MARKS AVAILABLE\n\n"
            message += f"Your GPA has been updated!\n\n"
            message += f"Current GPA: {marks_data['gpa']}\n\n"
            
            message += "Recent Subject Marks:\n"
            for subject, data in marks_data['subjects'].items():
                short_name = get_short_subject_name(subject)
                message += f"- {short_name}: {data['total']} marks\n"
                message += f"  Internal: {data['internal']}, External: {data['external']}\n"
            
            message += f"\nCheck the JIIT portal for detailed breakdown!"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending marks update: {e}")
            return False
    
    def send_new_notices_alert(self, notices: list) -> bool:
        try:
            if not notices:
                return True
            
            message = f"NEW NOTICES AVAILABLE\n\n"
            message += f"Found {len(notices)} new notice(s):\n\n"
            
            for notice in notices[:3]:  # Limit to first 3 notices
                message += f"- {notice['title']}\n"
                message += f"Date: {notice['date']}\n"
                if len(notice['content']) > 100:
                    message += f"{notice['content'][:100]}...\n\n"
                else:
                    message += f"{notice['content']}\n\n"
            
            if len(notices) > 3:
                message += f"... and {len(notices) - 3} more notices available on the portal."
            
            message += f"\nCheck JIIT portal for complete details!"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending notices alert: {e}")
            return False
    
    def handle_incoming_message(self, message_body: str, from_number: str) -> str:
        try:
            message_body = message_body.lower().strip()
            logger.info(f"Processing incoming message: '{message_body}' from {from_number}")
            
            from main import get_jiit_checker
            jiit_checker = get_jiit_checker()
            
            if not jiit_checker:
                return "Portal connection not available. Please try again later."
            
            if 'attendance' in message_body or 'attend' in message_body:
                return jiit_checker.get_formatted_attendance_summary()
            
            elif 'marks' in message_body or 'grades' in message_body or 'gpa' in message_body:
                return jiit_checker.get_formatted_marks_summary()
            
            elif 'notices' in message_body or 'news' in message_body or 'announcement' in message_body:
                try:
                    notices = jiit_checker.fetch_notices()
                    if notices:
                        response = "Latest Notices:\n\n"
                        for notice in notices[:3]:
                            response += f"- {notice['title']} ({notice['date']})\n"
                        return response
                    else:
                        return "No new notices available."
                except Exception:
                    return "Unable to fetch notices at the moment."
            
            elif 'help' in message_body or 'commands' in message_body:
                return (" Commands:\n\n"
                       "- Send 'attendance' - Get your attendance summary\n"
                       "- Send 'marks' - Get your marks/GPA\n"
                       "- Send 'notices' - Get latest notices\n"
                       "- Send 'help' - Show this help message\n\n"
                       "I'll also send automatic alerts for:\n"
                       "- Low attendance warnings\n"
                       "- New marks updates\n"
                       "- Important notices")
            
            else:
                return ("Hi! I'm your JIIT Portal assistant.\n\n"
                       "Send 'help' to see available commands, or try:\n"
                       "- 'attendance' - Check your attendance\n"
                       "- 'marks' - Check your marks\n"
                       "- 'notices' - Latest announcements")
            
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            return "Sorry, I encountered an error. Please try again later."


def create_webhook_app(notifier: WhatsAppNotifier) -> Flask:
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST'])
    def whatsapp_webhook():
        try:
            incoming_msg = request.values.get('Body', '').strip()
            from_number = request.values.get('From', '')
            
            logger.info(f"Received webhook message: '{incoming_msg}' from {from_number}")
            
            response_text = notifier.handle_incoming_message(incoming_msg, from_number)
            
            resp = MessagingResponse()
            resp.message(response_text)
            
            return str(resp)
            
        except Exception as e:
            logger.error(f"Error in webhook handler: {e}")
            resp = MessagingResponse()
            resp.message("Sorry, I'm experiencing technical difficulties. Please try again later.")
            return str(resp)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy', 'service': 'jiit-whatsapp-bot'}, 200
    
    return app
