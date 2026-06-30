import os
import sys
from datetime import datetime

# Force UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Notification templates ───────────────────────────────────
STATUS_MESSAGES = {
    "emailed":           "📧 Cold email sent to {contact} at {company}",
    "followup_sent":     "📨 Follow-up sent to {contact} at {company}",
    "meeting_sent":      "📅 Meeting link sent to {contact} at {company}",
    "meeting_booked":    "✅ Meeting BOOKED with {contact} at {company}!",
    "meeting_completed": "🤝 Meeting COMPLETED with {contact} at {company}!",
    "invoiced":          "💰 Invoice sent to {contact} at {company}",
    "closed_won":        "🎉 CLOSED WON — {company} has paid! Deal complete!",
    "not_interested":    "❌ {contact} at {company} marked as not interested",
}

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOG_FILE = os.path.join(LOG_DIR, "notifications.log")


def _settings_enabled() -> bool:
    try:
        from . import settings as _settings
        return _settings.get("notifications_enabled", True)
    except Exception:
        return True


def notify(lead: dict, new_status: str, detail: str = "") -> None:
    if not _settings_enabled():
        return

    template = STATUS_MESSAGES.get(new_status)
    if not template:
        return

    contact = lead.get("contact", "Unknown")
    company = lead.get("company", "Unknown")
    email = lead.get("email", "")

    message = template.format(contact=contact, company=company)
    if detail:
        message += f" — {detail}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"

    # Print to stdout (Hermes gateway captures this)
    print(f"\n{'─' * 50}")
    print(f"  🔔 NOTIFICATION")
    print(f"  {message}")
    print(f"  Lead: {contact} ({email})")
    print(f"  Status: {new_status}")
    print(f"{'─' * 50}\n")

    # Append to log file
    _log_to_file(full_message, email, new_status)


def notify_summary(leads: list) -> None:
    if not _settings_enabled():
        return

    if not leads:
        print("\n[NOTIFY] No leads to summarize.")
        return

    # Count leads per status
    status_counts = {}
    for lead in leads:
        status = lead.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Pipeline order for display
    pipeline_order = [
        "new", "emailed", "followup_sent", "meeting_sent",
        "meeting_booked", "meeting_completed", "invoiced",
        "closed_won", "not_interested",
    ]

    status_emoji = {
        "new": "🆕", "emailed": "📧", "followup_sent": "📨",
        "meeting_sent": "📅", "meeting_booked": "✅",
        "meeting_completed": "🤝", "invoiced": "💰",
        "closed_won": "🎉", "not_interested": "❌",
    }

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'═' * 50}")
    print(f"  📊 PIPELINE SUMMARY — {timestamp}")
    print(f"{'═' * 50}")
    print(f"  Total leads: {len(leads)}")
    print(f"{'─' * 50}")

    for status in pipeline_order:
        count = status_counts.get(status, 0)
        if count > 0:
            emoji = status_emoji.get(status, "•")
            bar = "█" * count + "░" * (max(0, 10 - count))
            print(f"  {emoji} {status:20s} {bar} {count}")

    print(f"{'═' * 50}\n")

    # List individual leads
    for lead in leads:
        emoji = status_emoji.get(lead.get("status", ""), "•")
        print(f"  {emoji} {lead.get('company', '?'):12s} | {lead.get('contact', '?'):8s} | {lead.get('status', '?')}")

    print()


def _log_to_file(message: str, email: str, status: str) -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message} | {email} | {status}\n")
    except Exception:
        pass  # Don't let logging failures break the pipeline


# Quick self-test
if __name__ == "__main__":
    test_lead = {
        "company": "TestCorp",
        "contact": "Jane",
        "email": "jane@testcorp.com",
    }
    notify(test_lead, "emailed")
    notify(test_lead, "meeting_booked")
    notify(test_lead, "closed_won", detail="$150.00")

    test_leads = [
        {"company": "Notion", "contact": "John", "status": "emailed"},
        {"company": "Linear", "contact": "Sara", "status": "meeting_sent"},
        {"company": "Vercel", "contact": "Mike", "status": "closed_won"},
    ]
    notify_summary(test_leads)