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
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"

# Email config
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"


def _get_sender_name() -> str:
    try:
        from . import settings
        value = settings.get("sender_name", os.getenv("SENDER_NAME", "Alex"))
        return value if isinstance(value, str) else os.getenv("SENDER_NAME", "Alex") or "Alex"
    except Exception:
        return os.getenv("SENDER_NAME", "Alex")


def _get_company_name() -> str:
    try:
        from . import settings
        value = settings.get("company_name", os.getenv("COMPANY_NAME", "Autocloser"))
        return value if isinstance(value, str) else os.getenv("COMPANY_NAME", "Autocloser") or "Autocloser"
    except Exception:
        return os.getenv("COMPANY_NAME", "Autocloser")


def _get_email_tone() -> str:
    try:
        from . import settings
        value = settings.get("email_tone", "conversational")
        return value if isinstance(value, str) else "conversational"
    except Exception:
        return "conversational"


def _get_max_words() -> int:
    try:
        from . import settings
        value = settings.get("max_email_words", 100)
        return value if isinstance(value, int) else 100
    except Exception:
        return 100


def _generate_email(prompt: str, system_prompt: str, label: str) -> dict:
    try:
        import json
        retry_prompt = prompt
        result = None
        parse_error = None

        for attempt in range(2):
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": retry_prompt},
                ],
                temperature=0.5,
                max_tokens=500,
                timeout=30,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                parse_error = ValueError("Email generation returned no text")
            else:
                raw = content.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                candidates = [raw]
                decoder = json.JSONDecoder()
                candidates.extend(
                    raw[start:]
                    for start, character in enumerate(raw)
                    if character == "{"
                )
                for candidate in candidates:
                    try:
                        parsed, _ = decoder.raw_decode(candidate.lstrip())
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(parsed, dict):
                        continue
                    subject, body = parsed.get("subject"), parsed.get("body")
                    if isinstance(subject, str) and subject.strip() and isinstance(body, str) and body.strip():
                        result = {"subject": subject.strip(), "body": body.strip()}
                        break

                if result is None:
                    parse_error = ValueError("LLM response was not a JSON object with a non-empty subject and body")

            if result is not None:
                break
            if attempt == 0:
                retry_prompt = (
                    prompt
                    + "\n\nFormatting correction: return only one valid JSON object with exactly two string keys, "
                    + '"subject" and "body". Do not include markdown, reasoning, or text outside the object.'
                )

        if result is None:
            raise parse_error or ValueError("Email generation failed")

        print(f"[EMAIL] Generated {label}")
        print(f"  Subject: {result['subject']}")
        return result
    except Exception as e:
        print(f"[EMAIL] Failed to generate {label}: {e}")
        return {}



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

    return _generate_email(
        prompt,
        "You are a B2B sales copywriter. Return only valid JSON.",
        f"cold email for {lead['contact']} at {lead['company']}",
    )


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

    return _generate_email(
        prompt,
        "You are a helpful B2B sales consultant. Answer questions directly and concisely. Return only valid JSON.",
        f"follow-up for {lead['contact']} at {lead['company']}",
    )


def generate_meeting_email(lead: dict, calendly_link: str) -> dict:
    prompt = f"""Write a concise email to {lead['contact']} at {lead['company']} who expressed interest in a meeting.
Include this exact booking link: {calendly_link}
Invite them to choose a convenient time, keep the tone conversational, and sign off as {_get_sender_name()} from {_get_company_name()}.
Return ONLY a JSON object with non-empty "subject" and "body" strings. No markdown or code fences."""
    return _generate_email(
        prompt,
        "You write helpful, concise B2B emails. Return only valid JSON.",
        f"meeting email for {lead['contact']} at {lead['company']}",
    )


def generate_invoice_email(lead: dict, invoice_url: str, description: str) -> dict:
    prompt = f"""Write a concise email to {lead['contact']} at {lead['company']} about the invoice for {description}.
Include this exact invoice link: {invoice_url}
Keep the message clear and professional, and sign off as {_get_sender_name()} from {_get_company_name()}.
Return ONLY a JSON object with non-empty "subject" and "body" strings. No markdown or code fences."""
    return _generate_email(
        prompt,
        "You write clear, professional invoice emails. Return only valid JSON.",
        f"invoice email for {lead['contact']} at {lead['company']}",
    )


def _find_thread(to: str) -> tuple[str | None, str | None]:
    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            return None, None
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select('"[Gmail]/Sent Mail"')

        status, messages = mail.search(None, f'(TO "{to}")')
        if status != "OK" or not messages or not messages[0]:
            mail.logout()
            return None, None

        # Check from newest to oldest, verify exact To match
        msg_ids = messages[0].split()
        for msg_id in reversed(msg_ids):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            if not msg_data or not isinstance(msg_data[0], tuple) or len(msg_data[0]) < 2:
                continue
            raw_message = msg_data[0][1]
            if not isinstance(raw_message, bytes):
                continue
            msg = email.message_from_bytes(raw_message)

            # Exact match -- Gmail search ignores +aliases so we must verify
            from email.utils import parseaddr as _parseaddr
            _, actual_to = _parseaddr(msg["To"] or "")
            if actual_to.lower() == to.lower():
                mail.logout()
                return msg["Message-ID"], msg["Subject"] or ""

        mail.logout()
        return None, None

    except Exception:
        return None, None


def send_email(to: str, subject: str, body: str) -> bool:
    print(f"[EMAIL] Sending to {to}...")

    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            raise ValueError("SMTP_USER and SMTP_PASSWORD must be configured")
        # Check for existing thread to reply in
        thread_msg_id, thread_subject = _find_thread(to)

        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to

        if thread_msg_id and thread_subject:
            msg["In-Reply-To"] = thread_msg_id
            msg["References"] = thread_msg_id
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


def check_replies(leads: list[dict[str, str]]) -> list[dict[str, str]]:
    replies = []
    print("[EMAIL] Checking inbox for replies...")

    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            raise ValueError("SMTP_USER and SMTP_PASSWORD must be configured")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("INBOX")

        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")

        for lead in leads:
            lead_email = lead["email"].strip().lower()

            # Look up the subject of the email we sent to this lead.
            # Gmail strips +aliases from the From header, so we can't
            # distinguish leads by sender address alone.  Matching by
            # thread subject is reliable.
            sent_msg_id, sent_subject = _find_thread(lead_email)

            if sent_subject:
                # Strip leading "Re: " to get the base thread subject
                base_subject = sent_subject
                while base_subject.lower().startswith("re: "):
                    base_subject = base_subject[4:]
                base_subject = base_subject.strip()

                # Remove characters that break IMAP SUBJECT queries
                import re as _re
                safe_subject = _re.sub(r"[\"'\\]", " ", base_subject)
                # Use first ~6 significant words to keep search broad but relevant
                words = safe_subject.split()
                if len(words) > 6:
                    safe_subject = " ".join(words[:6])
                safe_subject = safe_subject.strip()

                # Search inbox by sanitized thread subject
                status, messages = mail.search(
                    None, f'(SUBJECT "{safe_subject}" SINCE {since_date})'
                )

                # Fallback: if subject search found nothing, try by References header
                if (status != "OK" or not messages or not messages[0]) and sent_msg_id:
                    status, messages = mail.search(
                        None, f'(HEADER References "{sent_msg_id}" SINCE {since_date})'
                    )
            else:
                # Fallback: search by FROM (works when leads have unique domains)
                status, messages = mail.search(
                    None, f'(FROM "{lead_email}" SINCE {since_date})'
                )

            if status != "OK" or not messages or not messages[0]:
                continue

            for msg_id in messages[0].split():
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                if not msg_data or not isinstance(msg_data[0], tuple) or len(msg_data[0]) < 2:
                    continue
                raw_message = msg_data[0][1]
                if not isinstance(raw_message, bytes):
                    continue
                msg = email.message_from_bytes(raw_message)

                # Skip emails we sent ourselves
                from email.utils import parseaddr
                _, sender_addr = parseaddr(msg.get("From", ""))
                if sender_addr.lower() == (SMTP_USER or "").lower():
                    continue

                # Extract body
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, bytes):
                                body_text = payload.decode("utf-8", errors="ignore")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body_text = payload.decode("utf-8", errors="ignore")

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
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("Reply classification returned no text")
        result = content.strip().lower()

        valid = {"interested", "not_interested", "needs_more_info", "unsubscribe"}
        if result not in valid:
            result = "needs_more_info"

        print(f"[EMAIL] Reply classified as: {result}")
        return result

    except Exception as e:
        print(f"[EMAIL] Classification failed: {e}")
        return "needs_more_info"


