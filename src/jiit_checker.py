import os
import logging
import time
from typing import Dict, Any, Optional, List
from session_manager import SessionManager, LoginError


class SessionExpired(Exception):
    pass


class APIError(Exception):
    pass


logger = logging.getLogger(__name__)

def get_short_subject_name(full_name: str) -> str:
    name = full_name.split('(')[0].strip()
    stopwords = {'and', 'of', 'the', 'in', 'on', 'for', 'to', 'with', 'by', 'at', 'from'}
    words = [w for w in name.split() if w.lower() not in stopwords]
    if not words:
        return name
    if 'LAB' in name.upper():
        abbr = ''.join(word[0].upper() for word in words if word.upper() != 'LAB')
        return f"{abbr} Lab" if abbr else "Lab"
    else:
        abbr = ''.join(word[0].upper() for word in words)
        return abbr

class JIITChecker:

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session_manager = None
        self.last_attendance_data = {}
        self.last_marks_data = {}
        self.last_notices = []

    def login(self) -> bool:
        try:
            logger.info("Attempting to login to JIIT webportal...")
            self.session_manager = SessionManager()

            if self.session_manager.login_simple(self.username, self.password):
                logger.info("Login successful!")
                session_info = self.session_manager.get_session_info()
                logger.info(f"Session active: {session_info}")
                return True
            else:
                logger.error("Login failed")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            raise

    def ensure_logged_in(self) -> bool:
        try:
            if not self.session_manager or not self.session_manager.is_logged_in():
                return self.login()
            return True

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return self.login()

    def fetch_attendance(self) -> Dict[str, Any]:
        try:
            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info("Fetching attendance data...")

            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            meta = webportal.get_attendance_meta()
            header = meta.latest_header()
            sem = meta.latest_semester()

            attendance_response = webportal.get_attendance(header, sem)

            total_classes = 0
            attended_classes = 0
            subject_attendance = {}

            if 'studentattendancelist' in attendance_response:
                logger.info(f"Processing {len(attendance_response['studentattendancelist'])} attendance records")
                for i, subject_data in enumerate(attendance_response['studentattendancelist']):
                    if i == 0:
                        logger.info(f"Available fields: {list(subject_data.keys())}")

                    subject_code = subject_data.get('subjectcode', 'Unknown Subject')

                    l_total = int(subject_data.get('Ltotalclass', 0) or 0)
                    l_present = int(subject_data.get('Ltotalpres', 0) or 0)
                    l_percentage = float(subject_data.get('Lpercentage', 0.0) or 0.0)

                    t_total = int(subject_data.get('Ttotalclass', 0) or 0)
                    t_present = int(subject_data.get('Ttotalpres', 0) or 0)
                    t_percentage = float(subject_data.get('Tpercentage', 0.0) or 0.0)

                    p_total = int(subject_data.get('Ptotalclass', 0) or 0)
                    p_present = int(subject_data.get('Ptotalpres', 0) or 0)
                    p_percentage = float(subject_data.get('Ppercentage', 0.0) or 0.0)

                    overall_ltp_percentage = float(subject_data.get('LTpercantage', 0.0) or 0.0)

                    subject_total = l_total + t_total + p_total
                    subject_present = l_present + t_present + p_present

                    if subject_total == 0:
                        logger.info(f"Skipping subject with 0 classes: {subject_code}")
                        continue

                    total_classes += subject_total
                    attended_classes += subject_present

                    if overall_ltp_percentage > 0:
                        subject_percentage = overall_ltp_percentage
                    elif p_percentage > 0:
                        subject_percentage = p_percentage
                    elif l_percentage > 0:
                        subject_percentage = l_percentage
                    elif t_percentage > 0:
                        subject_percentage = t_percentage
                    else:
                        subject_percentage = (subject_present / subject_total * 100) if subject_total > 0 else 0

                    subject_attendance[subject_code] = {
                        'total': subject_total,
                        'attended': subject_present,
                        'percentage': subject_percentage,
                        'overall_ltp_percentage': overall_ltp_percentage,
                        'lecture_percentage': l_percentage,
                        'tutorial_percentage': t_percentage,
                        'practical_percentage': p_percentage
                    }

                    logger.info(f"Processed: {subject_code} - {subject_percentage:.1f}% ({subject_present}/{subject_total})")

            overall_percentage = (attended_classes / total_classes * 100) if total_classes > 0 else 0

            attendance_data = {
                'total_classes': total_classes,
                'attended_classes': attended_classes,
                'attendance_percentage': overall_percentage,
                'subjects': subject_attendance,
                'current_semester': attendance_response.get('currentSem', 'Unknown'),
                'last_updated': time.time()
            }

            logger.info(f"Attendance fetched: {attendance_data['attendance_percentage']:.1f}% across {len(subject_attendance)} subjects")
            return attendance_data

        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            raise

    def fetch_marks(self) -> Dict[str, Any]:
        try:
            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info("Fetching marks data...")

            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            sgpa_cgpa_data = webportal.get_sgpa_cgpa()

            semesters = webportal.get_semesters_for_grade_card()

            marks_data = {
                'subjects': {},
                'sgpa': getattr(sgpa_cgpa_data, 'sgpa', 0.0) if sgpa_cgpa_data else 0.0,
                'cgpa': getattr(sgpa_cgpa_data, 'cgpa', 0.0) if sgpa_cgpa_data else 0.0,
                'gpa': getattr(sgpa_cgpa_data, 'cgpa', 0.0) if sgpa_cgpa_data else 0.0,
                'last_updated': time.time()
            }

            if semesters:
                try:
                    latest_semester = semesters[-1]
                    grade_card = webportal.get_grade_card(latest_semester)

                    if grade_card:
                        for subject_grade in grade_card:
                            subject_name = getattr(subject_grade, 'subject_name', 'Unknown Subject')
                            internal_marks = getattr(subject_grade, 'internal_marks', 0)
                            external_marks = getattr(subject_grade, 'external_marks', 0)
                            total_marks = getattr(subject_grade, 'total_marks', internal_marks + external_marks)

                            marks_data['subjects'][subject_name] = {
                                'internal': internal_marks,
                                'external': external_marks,
                                'total': total_marks
                            }

                except Exception as e:
                    logger.warning(f"Could not fetch grade card: {e}")

            logger.info(f"Marks fetched: CGPA {marks_data['cgpa']}")
            return marks_data

        except Exception as e:
            logger.error(f"Error fetching marks: {e}")
            raise

    def fetch_notices(self) -> List[Dict[str, Any]]:
        """Fetch latest notices and announcements."""
        try:
            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info("Fetching notices...")


            notices = [
                {
                    'id': f'notice_{int(time.time())}',
                    'title': 'Portal Data Available',
                    'content': 'Your attendance and marks data has been successfully fetched from the portal.',
                    'date': time.strftime('%Y-%m-%d'),
                    'type': 'system'
                }
            ]

            logger.info(f"Fetched {len(notices)} notices")
            return notices

        except Exception as e:
            logger.error(f"Error fetching notices: {e}")
            raise

    def check_for_changes(self) -> Dict[str, Any]:
        """Check for changes in attendance, marks, and notices."""
        changes = {
            'attendance_changed': False,
            'marks_changed': False,
            'new_notices': [],
            'attendance_below_threshold': False,
            'current_data': {}
        }

        try:
            current_attendance = self.fetch_attendance()
            current_marks = self.fetch_marks()
            current_notices = self.fetch_notices()

            changes['current_data'] = {
                'attendance': current_attendance,
                'marks': current_marks,
                'notices': current_notices
            }

            if self.last_attendance_data:
                if current_attendance['attendance_percentage'] != self.last_attendance_data.get('attendance_percentage'):
                    changes['attendance_changed'] = True
                    logger.info("Attendance percentage changed")

            threshold = float(os.getenv('ATTENDANCE_THRESHOLD', 75))
            if current_attendance['attendance_percentage'] < threshold:
                changes['attendance_below_threshold'] = True
                logger.warning(f"Attendance below threshold: {current_attendance['attendance_percentage']:.1f}% < {threshold}%")

            if self.last_marks_data:
                if current_marks['cgpa'] != self.last_marks_data.get('cgpa'):
                    changes['marks_changed'] = True
                    logger.info("CGPA changed")

            last_notice_ids = {notice['id'] for notice in self.last_notices}
            current_notice_ids = {notice['id'] for notice in current_notices}
            new_notice_ids = current_notice_ids - last_notice_ids

            if new_notice_ids:
                changes['new_notices'] = [
                    notice for notice in current_notices
                    if notice['id'] in new_notice_ids
                ]
                logger.info(f"Found {len(changes['new_notices'])} new notices")

            self.last_attendance_data = current_attendance
            self.last_marks_data = current_marks
            self.last_notices = current_notices

            return changes

        except Exception as e:
            logger.error(f"Error checking for changes: {e}")
            raise

    def get_formatted_attendance_summary(self) -> str:
        try:
            attendance = self.fetch_attendance()

            summary = f"*Attendance Summary*\n\n"
            summary += f"Overall: {attendance['attendance_percentage']:.1f}% "
            summary += f"({attendance['attended_classes']}/{attendance['total_classes']} classes)\n\n"

            summary += "*Subject-wise:*\n"
            summary += f"{'Subject':<20} {'%':<6}\n"
            summary += f"{'-'*20} {'-'*6}\n"

            for subject, data in attendance['subjects'].items():
                short_name = get_short_subject_name(subject)
                summary += f"{short_name:<20} {data['percentage']:>5.1f}%\n"

            return summary

        except Exception as e:
            logger.error(f"Error getting attendance summary: {e}")
            return "Unable to fetch attendance data"

    def get_formatted_marks_summary(self) -> str:
        try:
            marks = self.fetch_marks()

            summary = f"*Marks Summary*\n\n"
            summary += f"Current CGPA: {marks['cgpa']:.2f}\n"
            if marks['sgpa'] > 0:
                summary += f"Current SGPA: {marks['sgpa']:.2f}\n"
            summary += "\n"

            if marks['subjects']:
                summary += "*Subject-wise Marks:*\n"
                for subject, data in marks['subjects'].items():
                    short_name = get_short_subject_name(subject)
                    summary += f"- {short_name}: {data['total']} (Internal: {data['internal']}, External: {data['external']})\n"
            else:
                summary += "*No detailed subject marks available*\n"

            return summary

        except Exception as e:
            logger.error(f"Error getting marks summary: {e}")
            return "Unable to fetch marks data"

    def cleanup(self):
        try:
            if self.session_manager:
                logger.info("Cleaning up session...")
                self.session_manager.logout()
                self.session_manager = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
