"""
AutoCloser Skill API
====================
A single-entry-point CLI dispatcher that exposes every AutoCloser pipeline
function as a callable tool for Hermes (or any agent that can run a subprocess).

Usage
-----
  python scripts/skill_api.py '{"tool": "load_leads"}'
  python scripts/skill_api.py '{"tool": "research_company", "args": {"lead_email": "john@notion.so"}}'
  python scripts/skill_api.py '{"tool": "send_email", "args": {"to": "...", "subject": "...", "body": "..."}}'

Or pipe JSON via stdin:
  echo '{"tool": "load_leads"}' | python scripts/skill_api.py

Every call prints a single JSON object to stdout and exits with code 0 on
success or 1 on error. Hermes reads that JSON object as the tool result.

Available tools
---------------
  load_leads
  research_company      lead_email
  generate_email        lead_email, research_summary
  generate_followup     lead_email, reply_body
  send_email            to, subject, body
  check_replies         lead_email
  analyze_reply         reply_body
  qualify_lead          lead_email, reply_analysis
  schedule_meeting      lead_email
  create_invoice        lead_email, amount_cents, description
  check_payment_status  lead_email
  mark_lead_status      lead_email, new_status
"""

import sys
import os
import json

# ── path setup ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

DATA_PATH     = os.path.join(ROOT, "data", "leads.csv")
SERVICES_PATH = os.path.join(ROOT, "data", "services.csv")


# ── helpers ───────────────────────────────────────────────────
def _ok(payload: dict):
    print(json.dumps({"ok": True, **payload}))
    sys.exit(0)


def _err(message: str):
    print(json.dumps({"ok": False, "error": message}))
    sys.exit(1)


def _get_lead(email: str) -> dict:
    from scripts import csv_reader
    leads = csv_reader.load_leads(DATA_PATH)
    for lead in leads:
        if lead["email"].strip().lower() == email.strip().lower():
            return lead
    return {}


# ── dispatcher ────────────────────────────────────────────────
def dispatch(tool: str, args: dict):
    from scripts import csv_reader, research, email_agent, scheduler, billing

    # ── load_leads ──────────────────────────────────────────
    if tool == "load_leads":
        leads = csv_reader.load_leads(DATA_PATH)
        _ok({"leads": leads, "count": len(leads)})

    # ── research_company ────────────────────────────────────
    elif tool == "research_company":
        lead_email = args.get("lead_email", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        summary = research.research_company(
            lead.get("website", ""), lead["company"], lead.get("notes", "")
        )
        _ok({"summary": summary, "company": lead["company"]})

    # ── generate_email ──────────────────────────────────────
    elif tool == "generate_email":
        lead_email      = args.get("lead_email", "")
        research_summary = args.get("research_summary", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        email_dict = email_agent.generate_email(lead, research_summary)
        _ok({"subject": email_dict["subject"], "body": email_dict["body"]})

    # ── generate_followup ───────────────────────────────────
    elif tool == "generate_followup":
        lead_email = args.get("lead_email", "")
        reply_body = args.get("reply_body", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        followup = email_agent.generate_followup(lead, reply_body)
        _ok({"subject": followup["subject"], "body": followup["body"]})

    # ── send_email ──────────────────────────────────────────
    elif tool == "send_email":
        to      = args.get("to", "")
        subject = args.get("subject", "")
        body    = args.get("body", "")
        if not to or not subject or not body:
            _err("send_email requires: to, subject, body")
        sent = email_agent.send_email(to, subject, body)
        _ok({"sent": sent, "to": to})

    # ── check_replies ───────────────────────────────────────
    elif tool == "check_replies":
        lead_email = args.get("lead_email", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        replies = email_agent.check_replies([lead])
        _ok({"replies": replies or [], "count": len(replies or [])})

    # ── analyze_reply ───────────────────────────────────────
    elif tool == "analyze_reply":
        reply_body = args.get("reply_body", "")
        if not reply_body:
            _err("analyze_reply requires: reply_body")
        classification = email_agent.analyze_reply(reply_body)
        _ok({"classification": classification})

    # ── qualify_lead ────────────────────────────────────────
    elif tool == "qualify_lead":
        lead_email     = args.get("lead_email", "")
        reply_analysis = args.get("reply_analysis", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        qualified = scheduler.qualify_lead(lead, reply_analysis)
        _ok({"qualified": qualified, "company": lead["company"]})

    # ── schedule_meeting ────────────────────────────────────
    elif tool == "schedule_meeting":
        lead_email = args.get("lead_email", "")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        result = scheduler.schedule_meeting(lead)
        _ok({"result": result})

    # ── create_invoice ──────────────────────────────────────
    elif tool == "create_invoice":
        lead_email   = args.get("lead_email", "")
        amount_cents = int(args.get("amount_cents", 0))
        description  = args.get("description", "Consulting service")
        lead = _get_lead(lead_email)
        if not lead:
            _err(f"No lead found with email: {lead_email}")
        if amount_cents <= 0:
            # Load services menu and pick first available service
            services = csv_reader.load_services(SERVICES_PATH)
            if services:
                amount_cents = services[0]["amount_cents"]
                description  = services[0]["description"]
            else:
                _err("amount_cents must be > 0 or data/services.csv must have entries")
        invoice_url = billing.create_invoice(lead, amount_cents, description)
        if invoice_url:
            csv_reader.mark_lead_status(DATA_PATH, lead["email"], "invoiced")
            _ok({"invoice_url": invoice_url, "invoiced": True})
        else:
            _err("Stripe invoice creation failed — check STRIPE_SECRET_KEY and logs")

    # ── check_payment_status ────────────────────────────────
    elif tool == "check_payment_status":
        lead_email = args.get("lead_email", "")
        if not lead_email:
            _err("check_payment_status requires: lead_email")
        status = billing.check_payment_status(lead_email)
        if status == "paid":
            csv_reader.mark_lead_status(DATA_PATH, lead_email, "closed_won")
        _ok({"payment_status": status, "lead_email": lead_email})

    # ── mark_lead_status ────────────────────────────────────
    elif tool == "mark_lead_status":
        lead_email = args.get("lead_email", "")
        new_status = args.get("new_status", "")
        valid = {"emailed", "followup_sent", "meeting_sent", "meeting_booked",
                 "meeting_completed", "invoiced", "closed_won", "not_interested"}
        if new_status not in valid:
            _err(f"Invalid status '{new_status}'. Valid values: {sorted(valid)}")
        success = csv_reader.mark_lead_status(DATA_PATH, lead_email, new_status)
        _ok({"updated": success, "lead_email": lead_email, "new_status": new_status})

    else:
        _err(f"Unknown tool: '{tool}'. Run with --help to see available tools.")


# ── entrypoint ────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    # Accept JSON from first CLI arg OR from stdin
    raw = None
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()

    if not raw:
        _err("No input. Pass a JSON payload as the first argument or via stdin.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        _err(f"Invalid JSON input: {e}")

    tool = payload.get("tool", "")
    args = payload.get("args", {})

    if not tool:
        _err("Payload must have a 'tool' key.")

    dispatch(tool, args)
