import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import csv_reader
from skills import research
from skills import email_agent

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "leads.csv")


def main():
    print("=" * 60)
    print("  SalesHermes -- Step 1 + 2 + 3 Test")
    print("=" * 60)

    # Step 1: Load leads from CSV
    print("\n--- STEP 1: Load Leads ---")
    leads = csv_reader.load_leads(DATA_PATH)

    if not leads:
        print("[MAIN] No leads found. Add leads to data/leads.csv")
        return

    print(f"[MAIN] Found {len(leads)} leads:")
    for i, lead in enumerate(leads, 1):
        print(f"  {i}. {lead['company']:12s} | {lead['contact']:8s} | status: {lead['status']}")

    # Step 2 + 3: Research -> Generate email -> Send email (for "new" leads)
    print("\n--- STEP 2+3: Research & Email ---")
    for lead in leads:
        if lead["status"] == "new":
            # Step 2: Research
            summary = research.research_company(
                website=lead["website"],
                company=lead["company"],
                notes=lead.get("notes", ""),
            )
            print(f"\n[MAIN] Research for {lead['company']}:")
            print(f"  {summary}")

            # Step 3: Generate email
            email_dict = email_agent.generate_email(lead, summary)
            print(f"\n[MAIN] Email for {lead['contact']}:")
            print(f"  Subject: {email_dict['subject']}")
            print(f"  Body: {email_dict['body']}")

            # Step 4: Send email
            sent = email_agent.send_email(lead["email"], email_dict["subject"], email_dict["body"])
            if sent:
                csv_reader.mark_lead_status(DATA_PATH, lead["email"], "emailed")

    print("\n" + "=" * 60)
    print("[OK] Steps 1-4 complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
