import resend
import requests
from django.conf import settings
from django.template.loader import render_to_string


def send_otp_email(to_email: str, otp_code: str):
    """
    Sends an OTP email via Resend using a custom HTML template.
    """
    resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'CodaExpress <onboarding@resend.dev>')

    html_content = render_to_string("emails/reset_password_otp.html", {"otp_code": otp_code})

    try:
        response = resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": f"{otp_code} is your CodaExpress security code",
            "html": html_content,
        })
        return response
    except Exception as e:
        print(f"[RESEND ERROR]: {e}")
        return None


def send_otp_sms(phone_number: str, otp_code: str):
    """
    Sends an SMS OTP via Termii.
    Formats numbers to '234...' and safely defaults sender_id to 'N-ALERT'.
    """
    # Safe fallback to N-ALERT during testing
    sender_id = getattr(settings, 'TERMII_SENDER_ID', 'N-ALERT') or 'N-ALERT'
    api_key = getattr(settings, 'TERMII_API_KEY', '')
    base_url = getattr(settings, 'TERMII_BASE_URL', 'https://api.ng.termii.com').rstrip('/')

    # Format phone number for Termii (expects '2349158841154')
    clean_phone = phone_number.replace("+", "").strip()
    if clean_phone.startswith("0") and len(clean_phone) == 11:
        clean_phone = "234" + clean_phone[1:]

    payload = {
        "to": clean_phone,
        "from": sender_id,
        "sms": f"{otp_code} is your CodaExpress verification code. It expires in 10 minutes.",
        "type": "plain",
        "channel": "dnd",  # Bypasses Nigerian DND restrictions
        "api_key": api_key,
    }

    headers = {'Content-Type': 'application/json'}
    url = f"{base_url}/api/sms/send"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        print(f"[TERMII RESPONSE]: {result}")
        return result
    except Exception as e:
        print(f"[TERMII SMS ERROR]: {e}")
        return None