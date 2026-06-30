import csv
import os


def load_leads(path: str) -> list[dict]:
    leads = []
    if not os.path.exists(path):
        print(f"[CSV_READER] File not found: {path}")
        return leads

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace from keys and values
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            leads.append(clean_row)

    print(f"[CSV_READER] Loaded {len(leads)} leads from {path}")
    return leads


def load_services(path: str) -> list[dict]:
    services = []
    if not os.path.exists(path):
        print(f"[CSV_READER] Services file not found: {path}")
        return services

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            clean_row["amount_cents"] = int(clean_row["amount_cents"])
            services.append(clean_row)

    return services


def mark_lead_status(path: str, email: str, new_status: str) -> bool:
    if not os.path.exists(path):
        print(f"[CSV_READER] File not found: {path}")
        return False

    leads = []
    updated = False
    lead_data = None

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["email"].strip() == email:
                row["status"] = new_status
                updated = True
                lead_data = dict(row)
            leads.append(row)

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        print(f"[CSV_READER] OK {email} -> status: {new_status}")

        # Fire notification for status change
        try:
            from . import notifications
            if lead_data:
                notifications.notify(lead_data, new_status)
        except ImportError:
            pass  # notifications module not available (standalone mode)
    else:
        print(f"[CSV_READER] WARNING: No lead found with email: {email}")

    return updated


def add_lead(path: str, company: str, contact: str, email: str,
             website: str, notes: str = "", status: str = "new") -> bool:
    fieldnames = ["company", "contact", "email", "website", "notes", "status"]

    # Check for duplicate email
    if os.path.exists(path):
        existing = load_leads(path)
        for lead in existing:
            if lead["email"].strip().lower() == email.strip().lower():
                print(f"[CSV_READER] Lead already exists: {email}")
                return False

    # If file doesn't exist, create it with headers
    file_exists = os.path.exists(path)

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "company": company,
            "contact": contact,
            "email": email,
            "website": website,
            "notes": notes,
            "status": status,
        })

    print(f"[CSV_READER] Added lead: {contact} at {company} ({email})")
    return True


def update_lead_field(path: str, email: str, field: str, value: str) -> bool:
    if not os.path.exists(path):
        print(f"[CSV_READER] File not found: {path}")
        return False

    leads = []
    updated = False

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["email"].strip() == email:
                if field in row:
                    old_value = row[field]
                    row[field] = value
                    updated = True
                    print(f"[CSV_READER] Updated {email}: {field} '{old_value}' -> '{value}'")
                else:
                    print(f"[CSV_READER] Field '{field}' not found in CSV")
                    return False
            leads.append(row)

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)

        # If status was updated, fire notification
        if field == "status":
            try:
                from . import notifications
                lead_data = next((l for l in leads if l["email"].strip() == email), {})
                notifications.notify(lead_data, value)
            except ImportError:
                pass
    else:
        print(f"[CSV_READER] WARNING: No lead found with email: {email}")

    return updated


def remove_lead(path: str, email: str) -> bool:
    if not os.path.exists(path):
        print(f"[CSV_READER] File not found: {path}")
        return False

    leads = []
    removed = False

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["email"].strip() == email:
                removed = True
                print(f"[CSV_READER] Removed lead: {row.get('contact', '?')} at {row.get('company', '?')} ({email})")
                continue  # Skip this row (don't add to list)
            leads.append(row)

    if removed:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
    else:
        print(f"[CSV_READER] WARNING: No lead found with email: {email}")

    return removed


def add_service(path: str, service_id: str, name: str,
                description: str, amount_cents: int) -> bool:
    fieldnames = ["id", "name", "description", "amount_cents"]

    # Check for duplicate ID
    if os.path.exists(path):
        existing = load_services(path)
        for svc in existing:
            if svc["id"] == service_id:
                print(f"[CSV_READER] Service ID already exists: {service_id}")
                return False

    file_exists = os.path.exists(path)

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "id": service_id,
            "name": name,
            "description": description,
            "amount_cents": amount_cents,
        })

    print(f"[CSV_READER] Added service: [{service_id}] {name} — ${amount_cents / 100:.2f}")
    return True


# Quick self-test
if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(__file__), "..", "data", "leads.csv")
    leads = load_leads(test_path)
    for lead in leads:
        print(f"  {lead['company']:12s} | {lead['contact']:8s} | {lead['status']}")
