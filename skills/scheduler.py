import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from . import email_agent

load_dotenv()

CALENDLY_LINK = os.getenv("CALENDLY_LINK", "https://calendly.com/yourname/15min")
CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY", "")
CALENDLY_API_BASE = "https://api.calendly.com"


def _calendly_headers():
    return {
        "Authorization": f"Bearer {CALENDLY_API_KEY}",
        "Content-Type": "application/json",
    }


def _get_user_uri() -> str:
    """Get the current Calendly user URI (needed to query events)."""
    try:
        resp = requests.get(f"{CALENDLY_API_BASE}/users/me", headers=_calendly_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()["resource"]["uri"]
    except Exception as e:
        print(f"[SCHEDULER] Calendly user lookup failed: {e}")
        return ""


def check_meeting_completed(lead_email: str) -> bool:
    """Query Calendly API to check if a meeting with this lead has ended."""
    if not CALENDLY_API_KEY:
        print("[SCHEDULER] WARNING: No CALENDLY_API_KEY set, cannot verify meeting status")
        return False

    user_uri = _get_user_uri()
    if not user_uri:
        return False

    try:
        resp = requests.get(
            f"{CALENDLY_API_BASE}/scheduled_events",
            headers=_calendly_headers(),
            params={
                "user": user_uri,
                "invitee_email": lead_email,
                "status": "active",
                "sort": "start_time:desc",
                "count": 5,
            },
            timeout=10,
        )
        resp.raise_for_status()
        events = resp.json().get("collection", [])

        if not events:
            print(f"[SCHEDULER] No Calendly events found for {lead_email}")
            return False

        now = datetime.now(timezone.utc)
        for event in events:
            end_time = datetime.fromisoformat(event["end_time"].replace("Z", "+00:00"))
            if end_time < now:
                print(f"[SCHEDULER] Meeting completed for {lead_email} (ended {end_time.isoformat()})")
                return True

        print(f"[SCHEDULER] Meeting scheduled but not yet completed for {lead_email}")
        return False

    except Exception as e:
        print(f"[SCHEDULER] Calendly API error: {e}")
        return False


def qualify_lead(lead: dict, reply_analysis: str) -> bool:
    qualified = reply_analysis in ("interested", "needs_more_info")
    status = "QUALIFIED" if qualified else "NOT QUALIFIED"
    print(f"[SCHEDULER] {lead['company']} ({lead['contact']}) -> {status} (reply: {reply_analysis})")
    return qualified


SENDER_NAME = os.getenv("SENDER_NAME", "Alex")


def schedule_meeting(lead: dict) -> str:
    message = (
        f"Hi {lead['contact']},\n\n"
        f"Thanks for your interest! I'd love to set up a quick 15-minute call.\n\n"
        f"Pick a time that works for you: {CALENDLY_LINK}\n\n"
        f"Looking forward to it!\n"
        f"{SENDER_NAME}"
    )

    subject = "Let's connect -- 15 min call"

    sent = email_agent.send_email(lead["email"], subject, message)

    if sent:
        print(f"[SCHEDULER] Meeting link sent -> {lead['email']}")
        return f"Meeting link sent to {lead['contact']} at {lead['email']}"
    else:
        print(f"[SCHEDULER] Failed to send meeting link to {lead['email']}")
        return f"Failed to send meeting link to {lead['contact']}"


# Quick self-test
if __name__ == "__main__":
    test_lead = {
        "company": "TestCorp",
        "contact": "Jane",
        "email": "brocode09x+test1@gmail.com",
    }
    print(qualify_lead(test_lead, "interested"))
    print(qualify_lead(test_lead, "not_interested"))
