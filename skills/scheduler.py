import os
from dotenv import load_dotenv
from skills import email_agent

load_dotenv()

CALENDLY_LINK = os.getenv("CALENDLY_LINK", "https://calendly.com/yourname/15min")


def qualify_lead(lead: dict, reply_analysis: str) -> bool:
    qualified = reply_analysis in ("interested", "needs_more_info")
    status = "QUALIFIED" if qualified else "NOT QUALIFIED"
    print(f"[SCHEDULER] {lead['company']} ({lead['contact']}) -> {status} (reply: {reply_analysis})")
    return qualified


def schedule_meeting(lead: dict) -> str:
    message = (
        f"Hi {lead['contact']},\n\n"
        f"Thanks for your interest! I'd love to set up a quick 15-minute call.\n\n"
        f"Pick a time that works for you: {CALENDLY_LINK}\n\n"
        f"Looking forward to it!\n"
        f"Alex"
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
