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

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["email"].strip() == email:
                row["status"] = new_status
                updated = True
            leads.append(row)

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        print(f"[CSV_READER] OK {email} -> status: {new_status}")
    else:
        print(f"[CSV_READER] WARNING: No lead found with email: {email}")

    return updated


# Quick self-test
if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(__file__), "..", "data", "leads.csv")
    leads = load_leads(test_path)
    for lead in leads:
        print(f"  {lead['company']:12s} | {lead['contact']:8s} | {lead['status']}")
