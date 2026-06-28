import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import csv_reader
from skills import research
from skills import email_agent
from skills import scheduler
from skills import billing

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "leads.csv")


def main():
    print("=" * 60)
    print("  SalesHermes -- Full Pipeline (Steps 1-10)")
    print("=" * 60)

    # Step 1: Load leads
    print("\n--- STEP 1: Load Leads ---")
    leads = csv_reader.load_leads(DATA_PATH)

    if not leads:
        print("[MAIN] No leads found. Add leads to data/leads.csv")
        return

    print(f"[MAIN] Found {len(leads)} leads:")
    for i, lead in enumerate(leads, 1):
        print(f"  {i}. {lead['company']:12s} | {lead['contact']:8s} | status: {lead['status']}")

    for lead in leads:

        # Steps 2-4: Research -> Generate -> Send (for "new" leads)
        if lead["status"] == "new":
            print(f"\n--- STEPS 2-4: Research & Email ({lead['company']}) ---")

            summary = research.research_company(
                website=lead["website"],
                company=lead["company"],
                notes=lead.get("notes", ""),
            )
            print(f"[MAIN] Research: {summary[:100]}...")

            email_dict = email_agent.generate_email(lead, summary)
            print(f"[MAIN] Subject: {email_dict['subject']}")

            sent = email_agent.send_email(lead["email"], email_dict["subject"], email_dict["body"])
            if sent:
                csv_reader.mark_lead_status(DATA_PATH, lead["email"], "emailed")

        # Steps 5-8: Check replies -> Analyze -> Qualify -> Schedule (for "emailed" leads)
        elif lead["status"] == "emailed":
            print(f"\n--- STEPS 5-8: Reply Check ({lead['company']}) ---")

            replies = email_agent.check_replies([lead])

            if replies:
                for reply in replies:
                    print(f"[MAIN] Reply from {reply['sender']}: {reply['body'][:80]}...")

                    analysis = email_agent.analyze_reply(reply["body"])

                    if scheduler.qualify_lead(lead, analysis):
                        result = scheduler.schedule_meeting(lead)
                        csv_reader.mark_lead_status(DATA_PATH, lead["email"], "meeting_sent")
                        print(f"[MAIN] {result}")
                    else:
                        csv_reader.mark_lead_status(DATA_PATH, lead["email"], "not_interested")
                        print(f"[MAIN] {lead['company']} marked as not interested")
            else:
                print(f"[MAIN] No reply yet from {lead['company']}")

        # Step 9: meeting_sent -> check if they replied -> create invoice
        elif lead["status"] == "meeting_sent":
            print(f"\n--- STEP 9: Meeting Follow-up ({lead['company']}) ---")

            # Check if they replied to the meeting link
            replies = email_agent.check_replies([lead])

            if replies:
                print(f"[MAIN] {lead['contact']} responded to meeting link")
                # They engaged -> send invoice
                invoice_url = billing.create_invoice(lead, 2000, "15-min consulting call")
                if invoice_url:
                    csv_reader.mark_lead_status(DATA_PATH, lead["email"], "invoiced")
                    print(f"[MAIN] Invoice sent: {invoice_url}")
                else:
                    print(f"[MAIN] Invoice creation skipped (no Stripe key?)")
            else:
                print(f"[MAIN] No response yet to meeting link from {lead['company']}")

        # Step 10: invoiced -> check payment
        elif lead["status"] == "invoiced":
            print(f"\n--- STEP 10: Payment Check ({lead['company']}) ---")

            status = billing.check_payment_status(lead["email"])
            if status == "paid":
                csv_reader.mark_lead_status(DATA_PATH, lead["email"], "closed_won")
                print(f"[MAIN] {lead['company']} -- CLOSED WON!")
            else:
                print(f"[MAIN] {lead['company']} invoice status: {status}")

        elif lead["status"] == "closed_won":
            print(f"\n[MAIN] {lead['company']} -- already closed. Nothing to do.")

        elif lead["status"] == "not_interested":
            print(f"\n--- Re-check: {lead['company']} (not_interested) ---")

            replies = email_agent.check_replies([lead])
            if replies:
                for reply in replies:
                    print(f"[MAIN] New reply from {reply['sender']}: {reply['body'][:80]}...")
                    analysis = email_agent.analyze_reply(reply["body"])

                    if scheduler.qualify_lead(lead, analysis):
                        result = scheduler.schedule_meeting(lead)
                        csv_reader.mark_lead_status(DATA_PATH, lead["email"], "meeting_sent")
                        print(f"[MAIN] {lead['company']} changed their mind! {result}")
                    else:
                        print(f"[MAIN] {lead['company']} still not interested")
            else:
                print(f"[MAIN] No new reply from {lead['company']}")

    # Final status
    print("\n--- FINAL STATUS ---")
    leads = csv_reader.load_leads(DATA_PATH)
    for lead in leads:
        print(f"  {lead['company']:12s} | {lead['status']}")

    print("\n" + "=" * 60)
    print("[OK] Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
