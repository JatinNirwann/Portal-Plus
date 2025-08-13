import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jiit_checker import JIITChecker
from session_manager import SessionManager
from notifier import WhatsAppNotifier

def main():
    print("JIIT Attendance Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    username = os.getenv('JIIT_USERNAME')
    password = os.getenv('JIIT_PASSWORD')
    whatsapp_number = os.getenv('WHATSAPP_TO') 
    
    if not username or not password:
        print("ERROR: JIIT credentials not found in .env file")
        print("Please ensure JIIT_USERNAME and JIIT_PASSWORD are set")
        return False
    
    if not whatsapp_number:
        print("WARNING: WHATSAPP_TO not found in .env file")
        print("WhatsApp notification will be skipped")
    
    print(f"Testing with username: {username}")
    if whatsapp_number:
        print(f"WhatsApp notifications will be sent to: {whatsapp_number}")
    print()
    
    try:
        jiit_checker = JIITChecker(username, password)
        print("SUCCESS: JIITChecker initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize JIITChecker: {e}")
        return False
    
    notifier = None
    if whatsapp_number:
        try:
            notifier = WhatsAppNotifier()
            print("SUCCESS: WhatsApp notifier initialized successfully")
        except Exception as e:
            print(f"WARNING: Failed to initialize WhatsApp notifier: {e}")
            print("Continuing without WhatsApp notifications...")
    
    try:
        if jiit_checker.login():
            print("Login successful")
        else:
            print("Login failed")
            return False
    except Exception as e:
        print(f"Login error: {e}")
        return False
    
    print()
    print("Fetching attendance data...")
    print("-" * 30)
    

    try:
        attendance_data = jiit_checker.fetch_attendance()
        
        if attendance_data:
            print("SUCCESS: Attendance data fetched successfully")
            print()
            
            subjects = attendance_data.get('subjects', {})
            if subjects:
                print("SUBJECT-WISE ATTENDANCE:")
                print("-" * 40)
                for subject, data in subjects.items():
                    print(f"  {subject}:")
                    print(f"    Attended: {data.get('attended', 'N/A')}/{data.get('total', 'N/A')}")
                    print(f"    Percentage: {data.get('percentage', 'N/A'):.1f}%")
                    print()
            else:
                print("No subject-wise data available")
            

            print("FORMATTED SUMMARY:")
            print("-" * 20)
            summary = jiit_checker.get_formatted_attendance_summary()
            print(summary)
            

            if notifier and whatsapp_number:
                print()
                print("SENDING WHATSAPP NOTIFICATION:")
                print("-" * 35)
                try:
                    message = f"JIIT Attendance Test Report\n\n{summary}\n\nTest completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    message_sid = notifier.send_message(message, whatsapp_number)
                    if message_sid:
                        print(f"SUCCESS: WhatsApp message sent successfully!")
                        print(f"Message SID: {message_sid}")
                    else:
                        print("ERROR: Failed to send WhatsApp message")
                        
                except Exception as e:
                    print(f"ERROR: WhatsApp sending failed: {e}")
            else:
                print()
                print("WHATSAPP NOTIFICATION: Skipped (no number configured)")
            
        else:
            print("ERROR: No attendance data retrieved")
            return False
            
    except Exception as e:
        print(f"ERROR: Error fetching attendance: {e}")
        return False
    
    try:
        jiit_checker.cleanup()
        print()
        print("SUCCESS: Cleanup completed")
    except Exception as e:
        print(f"WARNING: Warning during cleanup: {e}")
    
    print()
    print("=" * 50)
    print("Test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\nAttendance test passed!")
            sys.exit(0)
        else:
            print("\nAttendance test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
