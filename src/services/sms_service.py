"""SMS Gateway Abstraction & Pakistan Mobile Number Service for SDC.
Supports legitimate delivery to Pakistani mobile networks (Jazz, Telenor, Zong, Ufone, SCOM)
with strict credential protection, mock provider isolation for tests, and sanitized audit logging.
Authored under agency-application-security-engineer and agency-backend-architect.
"""

from abc import ABC, abstractmethod
import logging
import re
from typing import Dict, List, Optional
import urllib.parse
import urllib.request
import json

from src.config import settings

logger = logging.getLogger("sdc.sms")


class SMSProviderError(Exception):
    """Raised when SMS delivery fails or provider is misconfigured."""
    pass


def normalize_pakistan_phone(raw_phone: str) -> str:
    """Normalize and validate mobile numbers for Pakistan.
    
    Accepts:
    - 03001234567
    - 0300-1234567
    - +923001234567
    - 923001234567
    - 00923001234567
    
    Returns E.164 formatted string: '+923001234567'
    Raises ValueError on invalid formats or non-mobile prefixes.
    """
    if not raw_phone:
        raise ValueError("موبائل فون نمبر لازمي آهي (Mobile phone number is required).")

    cleaned = re.sub(r'[\s\-\(\)\.]', '', raw_phone.strip())
    
    if cleaned.startswith("0092"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("92") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    elif cleaned.startswith("03"):
        cleaned = "+92" + cleaned[1:]
    elif not cleaned.startswith("+92"):
        if cleaned.startswith("3") and len(cleaned) == 10:
            cleaned = "+92" + cleaned

    # Validate against Pakistan mobile regex: +92 followed by 3 and 9 digits (10 digits total mobile block)
    # Valid prefixes: 030x, 031x, 032x, 033x, 034x, 0355 (SCOM)
    pattern = r'^\+92(3[0-9]{9})$'
    if not re.match(pattern, cleaned):
        raise ValueError(
            "پاڪستان جو صحيح موبائل نمبر داخل ڪريو، مثال: 03001234567 يا +923001234567 "
            "(Please enter a valid Pakistani mobile number, e.g. 03001234567 or +923001234567)."
        )

    return cleaned


class BaseSMSProvider(ABC):
    """Abstract SMS Gateway Interface."""

    @abstractmethod
    def send_sms(self, phone: str, message: str) -> bool:
        """Send an SMS message to the normalized phone number."""
        pass


class MockSMSProvider(BaseSMSProvider):
    """Isolated in-memory mock provider for automated tests and offline development."""

    def __init__(self):
        self.sent_messages: List[Dict[str, str]] = []

    def send_sms(self, phone: str, message: str) -> bool:
        self.sent_messages.append({"phone": phone, "message": message})
        # Log delivery without exposing full credentials
        masked_phone = phone[:6] + "..." + phone[-2:]
        logger.info(f"[MockSMSProvider] Dispatched message to {masked_phone}")
        return True

    def clear(self):
        self.sent_messages.clear()


class TwilioSMSProvider(BaseSMSProvider):
    """Twilio Programmable SMS provider for international and Pakistan routing."""

    def __init__(self, account_sid: str, auth_token: str, sender_id: str):
        self.account_sid = account_sid.strip()
        self.auth_token = auth_token.strip()
        self.sender_id = sender_id.strip()

    def send_sms(self, phone: str, message: str) -> bool:
        if not self.account_sid or not self.auth_token:
            logger.error("Twilio SMS credentials not configured in environment.")
            raise SMSProviderError("ايس ايم ايس گيٽ وي جو انتظام ناهي ٿيل (SMS Gateway is not configured).")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = urllib.parse.urlencode({
            "To": phone,
            "From": self.sender_id,
            "Body": message
        }).encode("utf-8")

        import base64
        auth_header = "Basic " + base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if 200 <= resp.status < 300:
                    masked_phone = phone[:6] + "..." + phone[-2:]
                    logger.info(f"[TwilioSMSProvider] Successfully sent SMS to {masked_phone}")
                    return True
                raise SMSProviderError(f"Twilio returned status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to dispatch SMS via Twilio: {str(e)}")
            raise SMSProviderError("ايس ايم ايس موڪلڻ دوران نقص پيش آيو (Failed to deliver SMS).")


class PakistanTelcoHTTPProvider(BaseSMSProvider):
    """Generic HTTP REST SMS Gateway compatible with Pakistani telco aggregators (Telenor, Jazz, BrandSMS)."""

    def __init__(self, endpoint_url: str, api_key: str, api_secret: str, sender_id: str):
        self.endpoint_url = endpoint_url.strip()
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.sender_id = sender_id.strip()

    def send_sms(self, phone: str, message: str) -> bool:
        if not self.endpoint_url or not self.api_key:
            logger.error("Pakistan Telco SMS Gateway URL or API Key is missing.")
            raise SMSProviderError("مقامي ايس ايم ايس گيٽ وي جو انتظام ناهي ٿيل (Local SMS gateway not configured).")

        payload = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "sender": self.sender_id,
            "receiver": phone,
            "message": message
        }
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(self.endpoint_url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if 200 <= resp.status < 300:
                    masked = phone[:6] + "..." + phone[-2:]
                    logger.info(f"[PakistanTelcoHTTPProvider] Dispatched SMS to {masked}")
                    return True
                raise SMSProviderError(f"Telco gateway returned status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to dispatch SMS via Pakistan Telco Gateway: {str(e)}")
            raise SMSProviderError("ايس ايم ايس سروس غير دستياب آهي (SMS service unavailable).")


# Provider Factory
mock_sms_provider = MockSMSProvider()


def get_sms_provider() -> BaseSMSProvider:
    """Retrieve active SMS provider based on configuration."""
    provider_name = settings.sms_provider.lower().strip()
    if provider_name == "twilio":
        return TwilioSMSProvider(
            account_sid=settings.sms_api_key,
            auth_token=settings.sms_api_secret,
            sender_id=settings.sms_sender_id or "SDC"
        )
    elif provider_name in {"pakistan_http", "telenor", "jazz"}:
        return PakistanTelcoHTTPProvider(
            endpoint_url=settings.sms_endpoint_url,
            api_key=settings.sms_api_key,
            api_secret=settings.sms_api_secret,
            sender_id=settings.sms_sender_id or "SDC-Alert"
        )
    return mock_sms_provider
