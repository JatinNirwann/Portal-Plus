import os
import logging
import time
import re
import io
import pdfplumber
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

        self.marks_semesters: List[str] = []
        self.selected_marks_sem: Optional[str] = None
        self.marks_semester_data: Optional[Dict[str, Any]] = None
        self.marks_data: Dict[str, Any] = {}
        self.marks_loading: bool = False
        self.grades_loading: bool = True
        self.grades_error: Optional[str] = None
        self.grade_card_loading: bool = False
        self.is_download_dialog_open: bool = False
        self.marks_cache = {}
        self.marks_cache_expiry = {}
        self.cache_duration = 300

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.marks_cache_expiry:
            return False
        return time.time() < self.marks_cache_expiry[cache_key]

    def _set_cache(self, cache_key: str, data: Any):
        self.marks_cache[cache_key] = data
        self.marks_cache_expiry[cache_key] = time.time() + self.cache_duration

    def _get_cache(self, cache_key: str) -> Optional[Any]:
        if self._is_cache_valid(cache_key):
            return self.marks_cache[cache_key]
        return None

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
            if self._is_cache_valid('latest_marks'):
                logger.info("Using cached latest marks data")
                return self.marks_data

            self.marks_loading = True

            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info("Fetching latest marks data...")
            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            max_retries = 3
            sgpa_cgpa_data = None
            for attempt in range(max_retries):
                try:
                    sgpa_cgpa_data = webportal.get_sgpa_cgpa()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed to fetch SGPA/CGPA, retrying: {e}")
                    time.sleep(1)

            semesters = None
            for attempt in range(max_retries):
                try:
                    semesters = webportal.get_semesters_for_grade_card()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed to fetch semesters, retrying: {e}")
                    time.sleep(1)

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
                    grade_card = None
                    for attempt in range(max_retries):
                        try:
                            grade_card = webportal.get_grade_card(latest_semester)
                            break
                        except Exception as e:
                            if attempt == max_retries - 1:
                                raise e
                            logger.warning(f"Attempt {attempt + 1} failed to fetch grade card, retrying: {e}")
                            time.sleep(1)

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

            self.marks_data = marks_data
            self._set_cache('latest_marks', marks_data)
            self.marks_loading = False

            logger.info(f"Latest marks fetched: CGPA {marks_data['cgpa']}")
            return marks_data

        except Exception as e:
            self.marks_loading = False
            logger.error(f"Error fetching latest marks: {e}")
            raise

    def fetch_semesters(self) -> List[Dict[str, str]]:
        try:
            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")
            logger.info("Fetching semesters list...")
            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")
            semesters = webportal.get_semesters_for_grade_card()
            semester_list = []
            if semesters:
                semester_counter = 1
                for semester in semesters:
                    semester_name = getattr(semester, 'semester_name', str(semester))
                    logger.info(f"Processing semester: {semester_name}")

                    # Extract registration code from semester name (usually in parentheses)
                    import re
                    reg_code_match = re.search(r'\(([^)]+)\)', semester_name)
                    reg_code = reg_code_match.group(1) if reg_code_match else ""

                    # If no parentheses, try to extract from the semester object attributes
                    if not reg_code:
                        reg_code = getattr(semester, 'registration_code', '')

                    year = None
                    reg_code_upper = reg_code.upper() if reg_code else semester_name.upper()
                    if reg_code:
                        import re
                        year_match = re.search(r'(\d{4})', reg_code)
                        if year_match:
                            year = year_match.group(1)

                    if 'ODD' in reg_code_upper or 'ODD' in semester_name.upper():
                        semester_type = "odd"
                        display_name = f"Odd {year}" if year else "Odd Semester"
                    elif 'EVE' in reg_code_upper or 'EVEN' in semester_name.upper():
                        semester_type = "even"
                        display_name = f"Even {year}" if year else "Even Semester"
                    elif 'SUMMER' in reg_code_upper or 'SUMMER' in semester_name.upper():
                        semester_type = "summer"
                        display_name = f"Summer {year}" if year else "Summer Semester"
                    else:
                        semester_type = "unknown"
                        display_name = semester_name if semester_name else "Unknown Semester"

                    semester_list.append({
                        'original_name': semester_name,
                        'display_name': display_name,
                        'type': semester_type,
                        'reg_code': reg_code,
                        'number': semester_counter
                    })
                    semester_counter += 1

            logger.info(f"Fetched {len(semester_list)} semesters")
            return semester_list
        except Exception as e:
            logger.error(f"Error fetching semesters: {e}")
            raise

    def fetch_marks_semesters(self) -> List[str]:
        try:
            # Check cache first
            if self._is_cache_valid('marks_semesters'):
                logger.info("Using cached marks semesters data")
                return self.marks_semesters

            # Set loading state
            self.marks_loading = True

            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info("Fetching marks semesters list...")
            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            try:
                semesters = webportal.get_semesters_for_marks()
                logger.info("Successfully fetched marks semesters using get_semesters_for_marks")
            except AttributeError:
                # Fallback to grade card semesters if marks semesters not available
                logger.info("get_semesters_for_marks not found, using get_semesters_for_grade_card")
                semesters = webportal.get_semesters_for_grade_card()

            semester_names = []
            if semesters:
                for semester in semesters:
                    semester_name = getattr(semester, 'semester_name', str(semester))
                    logger.info(f"Processing semester: {semester_name}")

                    import re
                    reg_code_match = re.search(r'\(([^)]+)\)', semester_name)
                    reg_code = reg_code_match.group(1) if reg_code_match else ""

                    # If no parentheses, try to extract from the semester object attributes
                    if not reg_code:
                        reg_code = getattr(semester, 'registration_code', '')

                    year = None
                    reg_code_upper = reg_code.upper() if reg_code else semester_name.upper()

                    # Try multiple patterns to extract year
                    year_patterns = [
                        r'(\d{4})',  # 4-digit year
                        r'(\d{2})(\d{2})',  # Two 2-digit numbers (like 24 25)
                        r'(\d{2})',  # 2-digit year
                    ]

                    for pattern in year_patterns:
                        year_match = re.search(pattern, reg_code_upper)
                        if year_match:
                            year_part = year_match.group(1)
                            # Convert 2-digit year to 4-digit
                            if len(year_part) == 2:
                                year_num = int(year_part)
                                # Assume years 50-99 are 1900s, 00-49 are 2000s
                                if year_num >= 50:
                                    year = f"19{year_part}"
                                else:
                                    year = f"20{year_part}"
                            else:
                                year = year_part
                            break

                    # If still no year found, try to extract from semester name
                    if not year:
                        name_match = re.search(r'(\d{4})', semester_name.upper())
                        if name_match:
                            year = name_match.group(1)

                    # Determine semester type and create simple display name
                    if 'ODD' in reg_code_upper or 'ODD' in semester_name.upper():
                        display_name = f"Odd {year}" if year else "Odd Semester"
                    elif 'EVE' in reg_code_upper or 'EVEN' in semester_name.upper():
                        display_name = f"Even {year}" if year else "Even Semester"
                    elif 'SUMMER' in reg_code_upper or 'SUMMER' in semester_name.upper():
                        display_name = f"Summer {year}" if year else "Summer Semester"
                    else:
                        # For unknown semester types, use the original name
                        display_name = semester_name if semester_name else "Unknown Semester"

                    semester_names.append(display_name)

            # Update state and cache
            self.marks_semesters = semester_names
            self._set_cache('marks_semesters', semester_names)
            self.marks_loading = False

            logger.info(f"Fetched {len(semester_names)} marks semesters")
            return semester_names

        except Exception as e:
            self.marks_loading = False
            logger.error(f"Error fetching marks semesters: {e}")
            raise

    def select_marks_semester(self, semester: str) -> None:
        if semester in self.marks_semesters:
            self.selected_marks_sem = semester
            logger.info(f"Selected semester: {semester}")
            self.fetch_marks_for_semester(semester)
        else:
            logger.warning(f"Invalid semester: {semester}")

    def get_current_marks(self) -> Optional[Dict[str, Any]]:
        if self.selected_marks_sem and self.selected_marks_sem in self.marks_data:
            return self.marks_data[self.selected_marks_sem]
        return None

    def download_marks(self, semester: str, file_path: str = "marks.pdf") -> bool:
        if not self.ensure_logged_in():
            logger.error("Not authenticated.")
            return False

        if semester not in self.marks_data:
            logger.error(f"No data for semester {semester}. Fetch first.")
            return False

        try:
            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            # Find the Semester object that matches the semester name
            try:
                semesters = webportal.get_semesters_for_marks()
            except AttributeError:
                semesters = webportal.get_semesters_for_grade_card()

            target_semester = None
            for sem in semesters:
                semester_name = getattr(sem, 'semester_name', str(sem))

                # Extract registration code and create display name (same logic as fetch_marks_semesters)
                import re
                reg_code_match = re.search(r'\(([^)]+)\)', semester_name)
                reg_code = reg_code_match.group(1) if reg_code_match else ""
                if not reg_code:
                    reg_code = getattr(sem, 'registration_code', '')

                year = None
                reg_code_upper = reg_code.upper() if reg_code else semester_name.upper()
                if reg_code:
                    year_match = re.search(r'(\d{4})', reg_code)
                    if year_match:
                        year = year_match.group(1)

                display_name = semester_name
                if 'ODD' in reg_code_upper or 'ODD' in semester_name.upper():
                    display_name = f"Odd {year}" if year else "Odd Semester"
                elif 'EVE' in reg_code_upper or 'EVEN' in semester_name.upper():
                    display_name = f"Even {year}" if year else "Even Semester"
                elif 'SUMMER' in reg_code_upper or 'SUMMER' in semester_name.upper():
                    display_name = f"Summer {year}" if year else "Summer Semester"

                if display_name == semester:
                    target_semester = sem
                    break

            if not target_semester:
                logger.error(f"Semester {semester} not found for download")
                return False

            # Download marks using the Semester object
            pdf_bytes = webportal.download_marks(target_semester)
            
            # Save the PDF bytes to file
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info(f"Downloaded marks to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def fetch_marks_for_semester(self, semester: str) -> Optional[Dict[str, Any]]:
        try:
            cache_key = f"marks_semester_{semester}"

            # Check cache first
            if self._is_cache_valid(cache_key):
                logger.info(f"Using cached marks data for semester: {semester}")
                return self._get_cache(cache_key)

            # Set loading state
            self.marks_loading = True

            if not self.ensure_logged_in():
                raise LoginError("Failed to establish valid session")

            logger.info(f"Fetching marks for semester: {semester}")
            webportal = self.session_manager.get_webportal()
            if not webportal:
                raise APIError("No webportal session available")

            # Get marks data using the correct pyjiit method
            try:
                # Use get_semesters_for_marks to find the correct semester object
                semesters = webportal.get_semesters_for_marks()
                logger.info("Successfully fetched semesters for marks")
            except AttributeError:
                # Fallback to grade card semesters if marks semesters not available
                logger.info("get_semesters_for_marks not found, using get_semesters_for_grade_card")
                semesters = webportal.get_semesters_for_grade_card()

            # Find the target semester object
            target_semester = None
            logger.info(f"Looking for semester: {semester}")
            logger.info(f"Available semesters: {[getattr(s, 'semester_name', str(s)) for s in semesters]}")

            for sem in semesters:
                semester_name = getattr(sem, 'semester_name', str(sem))

                # Extract registration code from semester name (same logic as in fetch_marks_semesters)
                import re
                reg_code_match = re.search(r'\(([^)]+)\)', semester_name)
                reg_code = reg_code_match.group(1) if reg_code_match else ""

                # If no parentheses, try to extract from the semester object attributes
                if not reg_code:
                    reg_code = getattr(sem, 'registration_code', '')

                # Extract year from registration code - more robust extraction
                year = None
                reg_code_upper = reg_code.upper() if reg_code else semester_name.upper()

                # Try multiple patterns to extract year
                year_patterns = [
                    r'(\d{4})',  # 4-digit year
                    r'(\d{2})(\d{2})',  # Two 2-digit numbers (like 24 25)
                    r'(\d{2})',  # 2-digit year
                ]

                for pattern in year_patterns:
                    year_match = re.search(pattern, reg_code_upper)
                    if year_match:
                        year_part = year_match.group(1)
                        # Convert 2-digit year to 4-digit
                        if len(year_part) == 2:
                            year_num = int(year_part)
                            # Assume years 50-99 are 1900s, 00-49 are 2000s
                            if year_num >= 50:
                                year = f"19{year_part}"
                            else:
                                year = f"20{year_part}"
                        else:
                            year = year_part
                        break

                # If still no year found, try to extract from semester name
                if not year:
                    name_match = re.search(r'(\d{4})', semester_name.upper())
                    if name_match:
                        year = name_match.group(1)

                # Determine semester type and create display name (same as fetch_marks_semesters)
                display_name = semester_name  # Default fallback
                if 'ODD' in reg_code_upper or 'ODD' in semester_name.upper():
                    display_name = f"Odd {year}" if year else "Odd Semester"
                elif 'EVE' in reg_code_upper or 'EVEN' in semester_name.upper():
                    display_name = f"Even {year}" if year else "Even Semester"
                elif 'SUMMER' in reg_code_upper or 'SUMMER' in semester_name.upper():
                    display_name = f"Summer {year}" if year else "Summer Semester"

                # Check if the display name matches the selected semester
                if display_name == semester:
                    target_semester = sem
                    logger.info(f"Found matching semester: {display_name} for selected: {semester}")
                    break
                else:
                    logger.debug(f"Semester {display_name} does not match selected {semester}")

            if not target_semester:
                logger.error(f"Semester {semester} not found among available semesters")
                raise ValueError(f"Semester {semester} not found")

            # Fetch grade card for the target semester
            max_retries = 3
            grade_card = None
            for attempt in range(max_retries):
                try:
                    logger.info(f"Fetching grade card for semester {semester} (attempt {attempt + 1})")
                    grade_card = webportal.get_grade_card(target_semester)
                    if grade_card:
                        logger.info(f"Grade card fetched successfully for {semester}")
                        break
                    else:
                        logger.warning(f"Grade card fetch returned None for {semester}")
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to fetch grade card after {max_retries} attempts: {e}")
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed to fetch grade card, retrying: {e}")
                    time.sleep(1)

            marks_data = {
                'subjects': {},
                'semester': semester,
                'last_updated': time.time()
            }

            if grade_card and 'gradecard' in grade_card:
                for subject_grade in grade_card['gradecard']:
                    subject_name = getattr(subject_grade, 'subject_name', 'Unknown Subject')
                    internal_marks = getattr(subject_grade, 'internal_marks', 0)
                    marks_data['subjects'][subject_name] = {
                        't1': internal_marks,
                        'grade': ''
                    }

                logger.info(f"Found {len(grade_card['gradecard'])} subjects from API for {semester}")
            else:
                logger.warning(f"No grade card data found for {semester}")

            # If no subjects found from API, try extracting from PDF
            if not marks_data['subjects']:
                logger.info("No marks found in API response, trying PDF extraction")
                try:
                    logger.info(f"Downloading PDF for semester: {semester}")
                    pdf_bytes = webportal.download_marks(target_semester)
                    if pdf_bytes:
                        logger.info(f"PDF downloaded successfully, size: {len(pdf_bytes)} bytes")
                        pdf_subjects = self._extract_marks_from_pdf(pdf_bytes)

                        if pdf_subjects:
                            marks_data['subjects'] = pdf_subjects
                            logger.info(f"Successfully extracted {len(pdf_subjects)} subjects from PDF")
                        else:
                            logger.warning("No marks found in PDF either")
                    else:
                        logger.warning("PDF download returned empty data")
                except Exception as e:
                    logger.error(f"Error downloading/extracting marks from PDF: {e}")
                    # Don't re-raise the exception, just log it and continue with empty marks

            # Update state and cache
            self.marks_semester_data = marks_data
            self.marks_data[semester] = marks_data
            self._set_cache(cache_key, marks_data)
            self.marks_loading = False

            logger.info(f"Marks fetched for semester {semester}: {len(marks_data['subjects'])} subjects")
            return marks_data

        except Exception as e:
            self.marks_loading = False
            logger.error(f"Error fetching marks for semester {semester}: {e}")
            raise

    def fetch_notices(self) -> List[Dict[str, Any]]:
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

    def _extract_marks_from_pdf(self, pdf_bytes: bytes) -> Dict[str, Dict[str, Any]]:
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            with pdfplumber.open(pdf_file) as pdf:
                text_content = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + '\n'
            
            # Parse the text to extract marks
            subjects = {}
            lines = text_content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for subject names (they don't start with special characters and are followed by marks)
                if (line and 
                    not line.startswith('(') and 
                    not line.startswith('Page') and
                    not line.startswith('Jaypee') and
                    not line.startswith('Subject') and
                    not line.startswith('Name:') and
                    not line.startswith('Registration') and
                    not line.startswith('Legend') and
                    not line.startswith('OM/FM') and
                    not line.startswith('Thu') and
                    not line.startswith('A-10') and
                    not line.startswith('Noida') and
                    not any(char.isdigit() for char in line[:10]) and  # Avoid lines starting with numbers
                    len(line) > 10):  # Subject names are usually long enough
                    
                    subject_name = line
                    
                    # Look for marks in the next line
                    if i + 1 < len(lines):
                        marks_line = lines[i + 1].strip()
                        
                        # Parse marks (format: "1.5/ 20 1.5/20.0" or "A 0.0/20.0")
                        marks_data = self._parse_marks_line(marks_line)
                        
                        if marks_data:
                            # Look for subject code in the next line
                            subject_code = ""
                            if i + 2 < len(lines):
                                code_line = lines[i + 2].strip()
                                if code_line.startswith('(') and code_line.endswith(')'):
                                    subject_code = code_line[1:-1]  # Remove parentheses
                            
                            subjects[subject_name] = {
                                'subject_code': subject_code,
                                't1': marks_data.get('t1', 0),
                                'grade': marks_data.get('grade', ''),
                                'marks_line': marks_line
                            }
                            
                            # Skip the next lines we already processed
                            i += 2
                
                i += 1
            
            logger.info(f"Extracted marks for {len(subjects)} subjects from PDF")
            return subjects
            
        except Exception as e:
            logger.error(f"Error extracting marks from PDF: {e}")
            return {}

    def _parse_marks_line(self, marks_line: str) -> Optional[Dict[str, Any]]:
        try:
            marks_line = marks_line.strip()

            # Handle absent case (e.g., "A 0.0/20.0") - A means absent, not a grade
            if marks_line.startswith('A ') and len(marks_line.split()) >= 2:
                parts = marks_line.split()
                if len(parts) >= 2 and '/' in parts[1]:
                    # A indicates absent, so T1 marks should be "A"
                    return {
                        't1': 'A',  # Absent
                        'grade': ''
                    }

            # Handle other grade formats (B, C, D, F) - these are actual grades
            if marks_line.startswith(('B', 'C', 'D', 'F')) and len(marks_line.split()) >= 2:
                parts = marks_line.split()
                grade = parts[0]
                marks_part = parts[1] if len(parts) > 1 else "0.0/0.0"

                if '/' in marks_part:
                    obtained, total = marks_part.split('/', 1)
                    t1_marks = float(obtained.strip()) if obtained.strip() else 0
                    return {
                        't1': t1_marks,
                        'grade': grade
                    }

            # Handle numerical format (e.g., "1.5/ 20 1.5/20.0")
            if '/' in marks_line:
                parts = marks_line.split()
                marks_parts = [p for p in parts if '/' in p]

                if len(marks_parts) >= 1:
                    # Parse first marks part (T1 marks)
                    obtained, weightage = marks_parts[0].split('/', 1)
                    t1_marks = float(obtained.strip()) if obtained.strip() else 0

                    return {
                        't1': t1_marks,
                        'grade': ''
                    }

            return None

        except Exception as e:
            logger.error(f"Error parsing marks line '{marks_line}': {e}")
            return None
