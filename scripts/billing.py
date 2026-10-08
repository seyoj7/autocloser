import os
import stripe
from dotenv import load_dotenv
from . import email_agent

# Explicit .env path — works regardless of CWD (needed for Hermes)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_ENV_PATH)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_invoice(lead: dict, amount: int, description: str) -> str:
    print(f"[BILLING] Creating invoice for {lead['contact']} at {lead['company']}...")
    print(f"  Amount: ${amount / 100:.2f} | {description}")

    if not stripe.api_key:
        print("[BILLING] WARNING: No STRIPE_SECRET_KEY set, skipping invoice creation")
        return ""

    try:
        # Search for existing customer
        customers = stripe.Customer.list(email=lead["email"], limit=1)
        if customers.data:
            customer = customers.data[0]
            print(f"[BILLING] Found existing customer: {customer.id}")
        else:
            customer = stripe.Customer.create(
                email=lead["email"],
                name=f"{lead['contact']} ({lead['company']})",
            )
            print(f"[BILLING] Created customer: {customer.id}")

        # Create invoice item
        stripe.InvoiceItem.create(
            customer=customer.id,
            amount=amount,
            currency="usd",
            description=description,
        )

        # Create and finalize invoice
        invoice = stripe.Invoice.create(
            customer=customer.id,
            collection_method="send_invoice",
            days_until_due=7,
            auto_advance=False,
        )
        invoice = stripe.Invoice.finalize_invoice(invoice.id)

        invoice_url = invoice.hosted_invoice_url
        if invoice_url is None:
            raise ValueError("Stripe finalized the invoice without a hosted URL")
        print(f"[BILLING] Invoice created: {invoice_url}")

        email_content = email_agent.generate_invoice_email(lead, invoice_url, description)
        if not email_content:
            print("[BILLING] LLM invoice email generation failed; skipping email")
            return ""

        if not email_agent.send_email(lead["email"], email_content["subject"], email_content["body"]):
            print("[BILLING] Invoice email send failed")
            return ""

        return invoice_url

    except Exception as e:
        print(f"[BILLING] Error creating invoice: {e}")
        return ""


def check_payment_status(lead_email: str) -> str:
    print(f"[BILLING] Checking payment status for {lead_email}...")

    if not stripe.api_key:
        print("[BILLING] WARNING: No STRIPE_SECRET_KEY set")
        return "unknown"

    try:
        customers = stripe.Customer.list(email=lead_email, limit=1)
        if not customers.data:
            print(f"[BILLING] No customer found for {lead_email}")
            return "unknown"

        customer = customers.data[0]
        invoices = stripe.Invoice.list(customer=customer.id, limit=1)

        if not invoices.data:
            print(f"[BILLING] No invoices found for {lead_email}")
            return "unknown"

        latest = invoices.data[0]
        status = latest.status  # paid, open, void, draft, uncollectible
        if status is None:
            print(f"[BILLING] Invoice status is unavailable for {lead_email}")
            return "unknown"
        print(f"[BILLING] Invoice status for {lead_email}: {status}")
        return status

    except Exception as e:
        print(f"[BILLING] Error checking payment: {e}")
        return "unknown"


