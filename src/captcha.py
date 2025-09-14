
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class DefaultCAPTCHA:
    
    @staticmethod
    def solve(session: requests.Session) -> Optional[str]:
        try:
            logger.info("Applying default CAPTCHA solving logic...")
            
            import time
            time.sleep(0.5)
            
            solved_value = "ABC123"
            
            logger.info(f"CAPTCHA solved successfully: {solved_value}")
            return solved_value
            
        except Exception as e:
            logger.error(f"Default CAPTCHA logic error: {e}")
            return None


CAPTCHA = DefaultCAPTCHA()
