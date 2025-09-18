import logging
from typing import Dict, Any, Optional
from pyjiit import Webportal
from pyjiit.default import CAPTCHA

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.webportal = Webportal()
        self.session = None
        self.headers = {}
        self.logged_in = False

    def login_simple(self, username: str, password: str) -> bool:
        try:
            logger.info("Starting login process with PyJIIT default CAPTCHA...")
            self.session = self.webportal.student_login(
                username=username,
                password=password,
                captcha=CAPTCHA
            )
            if self.session:
                self.logged_in = True
                self.headers = self.session.get_headers()
                logger.info(f"Login successful! Client ID: {self.webportal.session.clientid}")
                return True
            else:
                logger.error("Login failed - invalid credentials")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        if self.session:
            return self.session.get_headers()
        return self.headers.copy()

    def get_session_info(self) -> Dict[str, Any]:
        return {
            'logged_in': self.logged_in,
            'headers_count': len(self.headers),
            'session_active': self.session is not None,
            'client_id': getattr(self.webportal.session, 'clientid', None) if hasattr(self.webportal, 'session') else None
        }

    def is_logged_in(self) -> bool:
        return self.logged_in and self.session is not None

    def get_webportal(self) -> Optional[Webportal]:
        return self.webportal if self.logged_in else None

    def get_session(self):
        return self.session

    def logout(self):
        try:
            self.session = None
            self.headers.clear()
            self.logged_in = False
            logger.info("Logged out successfully")
        except Exception as e:
            logger.error(f"Logout error: {e}")

class LoginError(Exception):
    pass

class APIError(Exception):
    pass

class SessionExpired(Exception):
    pass
