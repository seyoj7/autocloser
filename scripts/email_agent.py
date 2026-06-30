import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv

# Explicit .env path — works regardless of CWD (needed for Hermes)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_ENV_PATH)

# Nemotron client
client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("NVIDIA_BASE_URL"),
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"

# Email config
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"


def _get_sender_name() -> str:
    """Get sender name from settings, falling back to env var."""
    try:
        from . import settings
        return settings.get("sender_name", os.getenv("SENDER_NAME", "Alex"))
    except Exception:
        return os.getenv("SENDER_NAME", "Alex")


def _get_company_name() -> str:
    """Get company name from settings, falling back to env var."""
    try:
        from . import settings
        return settings.get("company_name", os.getenv("COMPANY_NAME", "Autocloser"))
    except Exception:
        return os.getenv("COMPANY_NAME", "Autocloser")


def _get_email_tone() -> str:
    """Get email tone from settings."""
    try:
        from . import settings
        return settings.get("email_tone", "conversational")
    except Exception:
        return "conversational"


def _get_max_words() -> int:
    """Get max email word count from settings."""
    try:
        from . import settings
        return settings.get("max_email_words", 100)
    except Exception:
        return 100



def generate_email(lead: dict, research_summary: str) -> dict:
    sender = _get_sender_name()
    company = _get_company_name()
    tone = _get_email_tone()
    max_words = _get_max_words()

    prompt = f"""Write a short, personalized cold B2B email to {lead['contact']} at {lead['company']}.

    Use this research about their company:
    {research_summary}

    Rules:
    - Keep it under {max_words} words
    - Be {tone}, not salesy
    - Reference something specific about their company from the research
    - End with a soft CTA (suggest a 15-min call)
    - Don't use generic phrases like "I hope this email finds you well"
    - Sign off as "{sender}" from "{company}"

    Return ONLY a JSON object with "subject" and "body" keys. No markdown, no code fences."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a B2B sales copywriter. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()

        # Clean up markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        import json
        email_dict = json.loads(raw)
        print(f"[EMAIL] Generated email for {lead['contact']} at {lead['company']}")
        print(f"  Subject: {email_dict['subject']}")
        return email_dict

    except Exception as e:
        print(f"[EMAIL] Failed to generate email: {e}")
        sender = _get_sender_name()
        return {
            "subject": f"Quick question for {lead['contact']}",
            "body": f"Hi {lead['contact']},\n\nI came across {lead['company']} and would love to chat about how we might help. Do you have 15 minutes this week?\n\nBest,\n{sender}"
        }


def generate_followup(lead: dict, reply_body: str) -> dict:
    sender = _get_sender_name()
    company = _get_company_name()
    tone = _get_email_tone()

    prompt = f"""A prospect named {lead['contact']} at {lead['company']} replied to our cold email with a question or request for more info.

    Their reply:
    "{reply_body}"

    Write a helpful follow-up email that:
    - Directly answers their specific question or concern
    - Keeps it under 120 words
    - Is {tone} and confident, not evasive
    - Ends with a soft CTA suggesting a 15-min call to discuss further
    - Sign off as "{sender}" from "{company}"

    Return ONLY a JSON object with "subject" and "body" keys. No markdown, no code fences."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful B2B sales consultant. Answer questions directly and concisely. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=400,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        import json
        email_dict = json.loads(raw)
        print(f"[EMAIL] Generated followup for {lead['contact']} at {lead['company']}")
        print(f"  Subject: {email_dict['subject']}")
        return email_dict

    except Exception as e:
        print(f"[EMAIL] Failed to generate followup: {e}")
        sender = _get_sender_name()
        return {
            "subject": f"Re: Your question about {_get_company_name()}",
            "body": f"Hi {lead['contact']},\n\nGreat question! I'd love to walk you through the details on a quick 15-minute call — much easier than going back and forth over email.\n\nWould that work for you?\n\nBest,\n{sender}"
        }


def _find_thread(to: str):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select('"[Gmail]/Sent Mail"')

        status, messages = mail.search(None, f'(TO "{to}")')
        if status != "OK" or not messages[0]:
            mail.logout()
            return None, None

        # Check from newest to oldest, verify exact To match
        msg_ids = messages[0].split()
        for msg_id in reversed(msg_ids):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            to_header = (msg["To"] or "").lower()

            # Exact match -- Gmail search ignores +aliases so we must verify
            if to.lower() in to_header:
                mail.logout()
                return msg["Message-ID"], msg["Subject"] or ""

        mail.logout()
        return None, None

    except Exception:
        return None, None


def send_email(to: str, subject: str, body: str) -> bool:
    print(f"[EMAIL] Sending to {to}...")

    try:
        # Check for existing thread to reply in
        thread_msg_id, thread_subject = _find_thread(to)

        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to

        if thread_msg_id:
            # Reply in existing thread
            msg["In-Reply-To"] = thread_msg_id
            msg["References"] = thread_msg_id
            # Use original subject with Re: prefix
            clean_subject = thread_subject.replace("Re: ", "")
            msg["Subject"] = f"Re: {clean_subject}"
            print(f"[EMAIL] Replying in thread: {msg['Subject']}")
        else:
            msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())

        print(f"[EMAIL SENT] -> {to}")
        return True

    except Exception as e:
        print(f"[EMAIL] Send failed: {e}")
        return False


def check_replies(leads: list) -> list:
    replies = []
    print("[EMAIL] Checking inbox for replies...")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("INBOX")

        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")

        for lead in leads:
            lead_email = lead["email"].strip().lower()
            
            # Search specifically for emails FROM this lead
            status, messages = mail.search(None, f'(FROM "{lead_email}" SINCE {since_date})')
            
            if status != "OK" or not messages[0]:
                continue
                
            for msg_id in messages[0].split():
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                # Extract body
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body_text = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                if not body_text.strip():
                    continue

                replies.append({
                    "sender": lead_email,
                    "subject": msg["Subject"] or "",
                    "body": body_text.strip(),
                })

                print(f"[EMAIL] Reply from {lead_email}: {msg['Subject']}")

        mail.logout()

    except Exception as e:
        print(f"[EMAIL] IMAP error: {e}")

    print(f"[EMAIL] Found {len(replies)} replies from leads")
    return replies



def analyze_reply(reply_body: str) -> str:
    prompt = f"""Classify this email reply into exactly one category:
    - interested
    - not_interested
    - needs_more_info
    - unsubscribe

    Reply text:
    "{reply_body}"

    Return ONLY the category word, nothing else."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You classify email replies. Return only one word."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=10,
            timeout=30,
        )
        result = response.choices[0].message.content.strip().lower()

        valid = {"interested", "not_interested", "needs_more_info", "unsubscribe"}
        if result not in valid:
            result = "needs_more_info"

        print(f"[EMAIL] Reply classified as: {result}")
        return result

    except Exception as e:
        print(f"[EMAIL] Classification failed: {e}")
        return "needs_more_info"


# Quick self-test
if __name__ == "__main__":
    test_lead = {
        "company": "TestCorp",
        "contact": "Jane",
        "email": "brocode09x+test1@gmail.com",
        "website": "example.com",
    }
    result = generate_email(test_lead, "TestCorp is a SaaS company helping teams collaborate.")
    print(f"\nGenerated:\n  Subject: {result['subject']}\n  Body: {result['body']}")