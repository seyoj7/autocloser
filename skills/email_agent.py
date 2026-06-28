import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

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


def generate_email(lead: dict, research_summary: str) -> dict:
    prompt = f"""Write a short, personalized cold B2B email to {lead['contact']} at {lead['company']}.

    Use this research about their company:
    {research_summary}

    Rules:
    - Keep it under 100 words
    - Be conversational, not salesy
    - Reference something specific about their company from the research
    - End with a soft CTA (suggest a 15-min call)
    - Don't use generic phrases like "I hope this email finds you well"
    - Sign off as "Alex" from "SalesHermes"

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
        return {
            "subject": f"Quick question for {lead['contact']}",
            "body": f"Hi {lead['contact']},\n\nI came across {lead['company']} and would love to chat about how we might help. Do you have 15 minutes this week?\n\nBest,\nAlex"
        }


def send_email(to: str, subject: str, body: str) -> bool:
    print(f"[EMAIL] Sending to {to}...")

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to
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
    lead_emails = {lead["email"].strip().lower() for lead in leads}
    replies = []

    print("[EMAIL] Checking inbox for replies...")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("INBOX")

        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print("[EMAIL] No new replies")
            mail.logout()
            return replies

        for msg_id in messages[0].split():
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            # Extract sender email
            from_header = msg["From"]
            sender = email.utils.parseaddr(from_header)[1].lower()

            if sender not in lead_emails:
                continue

            # Extract body
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body_text = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            replies.append({
                "sender": sender,
                "subject": msg["Subject"] or "",
                "body": body_text.strip(),
            })

            # Mark as read
            mail.store(msg_id, "+FLAGS", "\\Seen")
            print(f"[EMAIL] Reply from {sender}: {msg['Subject']}")

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
