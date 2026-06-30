import os
import sys
import argparse

# Force UTF-8 output on Windows (prevents charmap encoding errors with emoji)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import csv_reader, settings

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "leads.csv")
SERVICES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "services.csv")


# ── Lead Commands ────────────────────────────────────────────

def cmd_list_leads(args):
    leads = csv_reader.load_leads(DATA_PATH)

    if not leads:
        print("\n  No leads found. Add leads with: cli.py add-lead")
        return

    status_emoji = {
        "new": "🆕", "emailed": "📧", "followup_sent": "📨",
        "meeting_sent": "📅", "meeting_booked": "✅",
        "meeting_completed": "🤝", "invoiced": "💰",
        "closed_won": "🎉", "not_interested": "❌",
    }

    print(f"\n{'═' * 80}")
    print(f"  📋 LEADS ({len(leads)} total)")
    print(f"{'═' * 80}")
    print(f"  {'#':3s} {'Company':14s} {'Contact':10s} {'Email':30s} {'Status':18s}")
    print(f"  {'─' * 75}")

    for i, lead in enumerate(leads, 1):
        status = lead.get("status", "?")
        emoji = status_emoji.get(status, "•")
        print(
            f"  {i:<3d} {lead.get('company', ''):14s} "
            f"{lead.get('contact', ''):10s} "
            f"{lead.get('email', ''):30s} "
            f"{emoji} {status}"
        )

    print(f"{'═' * 80}\n")


def cmd_add_lead(args):
    success = csv_reader.add_lead(
        DATA_PATH,
        company=args.company,
        contact=args.contact,
        email=args.email,
        website=args.website,
        notes=args.notes or "",
        status="new",
    )
    if success:
        print(f"\n  ✅ Lead added: {args.contact} at {args.company} ({args.email})")
        print(f"  Status: new — will be processed in next pipeline cycle.\n")
    else:
        print(f"\n  ❌ Failed to add lead. Check if email already exists.\n")


def cmd_update_lead(args):
    valid_fields = ["company", "contact", "email", "website", "notes", "status"]

    if args.field not in valid_fields:
        print(f"\n  ❌ Invalid field: '{args.field}'")
        print(f"  Valid fields: {', '.join(valid_fields)}\n")
        return

    if args.field == "status":
        valid_statuses = [
            "new", "emailed", "followup_sent", "meeting_sent",
            "meeting_booked", "meeting_completed", "invoiced",
            "closed_won", "not_interested",
        ]
        if args.value not in valid_statuses:
            print(f"\n  ❌ Invalid status: '{args.value}'")
            print(f"  Valid statuses: {', '.join(valid_statuses)}\n")
            return

    success = csv_reader.update_lead_field(DATA_PATH, args.email, args.field, args.value)
    if success:
        print(f"\n  ✅ Updated {args.email}: {args.field} → {args.value}\n")
    else:
        print(f"\n  ❌ Lead not found: {args.email}\n")


def cmd_remove_lead(args):
    success = csv_reader.remove_lead(DATA_PATH, args.email)
    if success:
        print(f"\n  ✅ Lead removed: {args.email}\n")
    else:
        print(f"\n  ❌ Lead not found: {args.email}\n")


# ── Service Commands ─────────────────────────────────────────

def cmd_list_services(args):
    services = csv_reader.load_services(SERVICES_PATH)

    if not services:
        print("\n  No services found. Add services with: cli.py add-service")
        return

    print(f"\n{'═' * 65}")
    print(f"  💼 SERVICES ({len(services)} total)")
    print(f"{'═' * 65}")
    print(f"  {'ID':4s} {'Name':25s} {'Price':10s} {'Description'}")
    print(f"  {'─' * 60}")

    for s in services:
        price = f"${s['amount_cents'] / 100:.2f}"
        print(f"  {s['id']:<4s} {s['name']:25s} {price:10s} {s['description']}")

    print(f"{'═' * 65}\n")


def cmd_add_service(args):
    success = csv_reader.add_service(
        SERVICES_PATH,
        service_id=args.id,
        name=args.name,
        description=args.description,
        amount_cents=args.amount,
    )
    if success:
        print(f"\n  ✅ Service added: [{args.id}] {args.name} — ${args.amount / 100:.2f}\n")
    else:
        print(f"\n  ❌ Failed to add service. Check if ID already exists.\n")


# ── Pipeline Status ──────────────────────────────────────────

def cmd_pipeline_status(args):
    leads = csv_reader.load_leads(DATA_PATH)

    if not leads:
        print("\n  No leads in pipeline.\n")
        return

    status_counts = {}
    for lead in leads:
        status = lead.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    pipeline_order = [
        ("new", "🆕"), ("emailed", "📧"), ("followup_sent", "📨"),
        ("meeting_sent", "📅"), ("meeting_booked", "✅"),
        ("meeting_completed", "🤝"), ("invoiced", "💰"),
        ("closed_won", "🎉"), ("not_interested", "❌"),
    ]

    total = len(leads)

    print(f"\n{'═' * 50}")
    print(f"  📊 PIPELINE FUNNEL — {total} leads")
    print(f"{'═' * 50}")

    for status, emoji in pipeline_order:
        count = status_counts.get(status, 0)
        if count > 0:
            bar = "█" * (count * 3) + "░" * max(0, 30 - count * 3)
            pct = count / total * 100
            print(f"  {emoji} {status:20s} {bar} {count} ({pct:.0f}%)")

    print(f"{'═' * 50}\n")


# ── Settings Commands ────────────────────────────────────────

def cmd_show_settings(args):
    settings.load_settings()
    print(settings.display())


def cmd_set(args):
    settings.load_settings()
    success = settings.update(args.key, args.value)
    if success:
        print(f"\n  ✅ Setting updated: {args.key} = {args.value}\n")


def cmd_reset_settings(args):
    settings.reset()
    print("\n  ✅ All settings reset to defaults.\n")


# ── Argument Parser ──────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autocloser-cli",
        description="AutoCloser — CLI for managing leads, services, and settings",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-leads
    subparsers.add_parser("list-leads", help="Show all leads")

    # add-lead
    p = subparsers.add_parser("add-lead", help="Add a new lead")
    p.add_argument("--company", required=True, help="Company name")
    p.add_argument("--contact", required=True, help="Contact person name")
    p.add_argument("--email", required=True, help="Contact email address")
    p.add_argument("--website", required=True, help="Company website URL")
    p.add_argument("--notes", default="", help="Optional notes about the lead")

    # update-lead
    p = subparsers.add_parser("update-lead", help="Update a lead's field")
    p.add_argument("--email", required=True, help="Lead's email (identifier)")
    p.add_argument("--field", required=True, help="Field to update (company, contact, website, notes, status)")
    p.add_argument("--value", required=True, help="New value for the field")

    # remove-lead
    p = subparsers.add_parser("remove-lead", help="Remove a lead")
    p.add_argument("--email", required=True, help="Lead's email to remove")

    # list-services
    subparsers.add_parser("list-services", help="Show all services")

    # add-service
    p = subparsers.add_parser("add-service", help="Add a new billable service")
    p.add_argument("--id", required=True, help="Service ID")
    p.add_argument("--name", required=True, help="Service name")
    p.add_argument("--description", required=True, help="Service description")
    p.add_argument("--amount", type=int, required=True, help="Amount in cents (e.g., 15000 = $150.00)")

    # pipeline-status
    subparsers.add_parser("pipeline-status", help="Show pipeline funnel")

    # show-settings
    subparsers.add_parser("show-settings", help="Show all settings")

    # set
    p = subparsers.add_parser("set", help="Update a single setting")
    p.add_argument("--key", required=True, help="Setting key")
    p.add_argument("--value", required=True, help="New value")

    # reset-settings
    subparsers.add_parser("reset-settings", help="Reset all settings to defaults")

    return parser


COMMANDS = {
    "list-leads": cmd_list_leads,
    "add-lead": cmd_add_lead,
    "update-lead": cmd_update_lead,
    "remove-lead": cmd_remove_lead,
    "list-services": cmd_list_services,
    "add-service": cmd_add_service,
    "pipeline-status": cmd_pipeline_status,
    "show-settings": cmd_show_settings,
    "set": cmd_set,
    "reset-settings": cmd_reset_settings,
}


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handler = COMMANDS.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)