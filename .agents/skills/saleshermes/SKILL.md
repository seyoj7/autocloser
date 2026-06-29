---
name: AutoCloser
description: >
  AutoCloser is an autonomous B2B sales pipeline agent. Given a CSV of leads,
  it researches each company's website with Playwright, generates hyper-personalized
  cold emails via NVIDIA Nemotron, sends them over Gmail SMTP, monitors the inbox
  for replies, classifies sentiment, dispatches Calendly meeting links to warm leads,
  and creates & delivers Stripe invoices � updating lead status in the CSV at every step.
  Trigger this skill when the user asks to run, fix, extend, or debug any part of
  the SalesHermes outreach pipeline (main.py, email_agent.py, research.py,
  scheduler.py, billing.py, csv_reader.py).
---

# SalesHermes � Autonomous B2B Sales Agent

## Overview

SalesHermes automates the full outbound sales loop:

```
CSV Leads ? Research ? Personalized Email ? Send ? Check Replies
         ? Classify ? Follow-up / Calendly Link ? Stripe Invoice ? CSV Update
```

All scripts live in `scripts/`. The orchestrator is `scripts/main.py`.

---

## When to Use This Skill

Use SalesHermes when the user wants to:

- Run the full outreach pipeline end-to-end
- Add, remove, or modify a pipeline stage (research, email, billing, etc.)
- Debug a failing step (SMTP auth, Playwright scrape, Stripe API, IMAP check)
- Extend the agent with new reply classifications or follow-up logic
- Inspect or update lead statuses in `data/leads.csv`

---

## Project Layout

```
Autocloser/
+-- .env                    # Secret env vars (never commit)
+-- .env.example            # Template for required env vars
+-- requirements.txt        # Python dependencies
+-- data/
�   +-- leads.csv           # Lead database (status tracked here)
+-- scripts/
    +-- main.py             # Pipeline orchestrator (entry point)
    +-- csv_reader.py       # Load leads, mark statuses
    +-- research.py         # Playwright scrape + Nemotron summary
    +-- email_agent.py      # Generate, send, check replies, analyze
    +-- scheduler.py        # Qualify leads, send Calendly links
    +-- billing.py          # Create & send Stripe invoices
```

---

## Required Environment Variables

Set these in `.env` (copy from `.env.example`):

| Variable            | Purpose                                          |
|---------------------|--------------------------------------------------|
| `SMTP_USER`         | Gmail address used to send emails                |
| `SMTP_PASSWORD`     | Gmail App Password (not your account password)   |
| `NVIDIA_API_KEY`    | API key for NVIDIA NIM / Nemotron endpoint       |
| `NVIDIA_BASE_URL`   | Base URL for the NVIDIA API                      |
| `STRIPE_SECRET_KEY` | Stripe secret key for invoice creation           |
| `CALENDLY_API_KEY`  | Calendly API key for scheduling links            |
| `CALENDLY_LINK`     | Your public Calendly booking URL                 |
| `SENDER_NAME`       | Your full name (used in email signatures)        |
| `COMPANY_NAME`      | Your company name (used in email copy)           |

> **Gmail SMTP Note**: You must enable 2FA on your Google account and generate a
> dedicated **App Password** at https://myaccount.google.com/apppasswords.
> Using your normal password will cause authentication failures.

---

## Dependencies

Install all dependencies with:

```bash
pip install -r requirements.txt
# Then install Playwright browsers (one-time setup):
python -m playwright install chromium
```

| Package          | Version    | Purpose                                    |
|------------------|------------|--------------------------------------------|
| `openai`         | >= 1.0.0   | OpenAI-compatible client for Nemotron API  |
| `python-dotenv`  | >= 1.0.0   | Load env vars from `.env`                  |
| `playwright`     | >= 1.40.0  | Headless browser for website research      |
| `stripe`         | >= 7.0.0   | Stripe invoice creation & payment tracking |
| `requests`       | >= 2.31.0  | HTTP requests (Calendly API, etc.)         |

---

## Step-by-Step Usage

### Step 1 � Prepare your leads CSV

`data/leads.csv` must have these columns:

```csv
company,contact,email,website,status,notes
Notion,John,john@notion.so,notion.so,new,
Linear,Sara,sara@linear.app,linear.app,new,
```

- `status` must be `new` for the pipeline to process a lead.
- `notes` is optional context passed to the research stage.

### Step 2 � Configure `.env`

```bash
cp .env.example .env
# Fill in all required variables
```

### Step 3 � Run the pipeline

```bash
cd e:/Programs/Autocloser
python scripts/main.py
```

The orchestrator loops every hour. For a one-shot test run, interrupt after the
first cycle with `Ctrl+C`.

### Step 4 � Monitor output

Watch the console for status messages at each stage:

```
[RESEARCH]   ? Scraping notion.so...
[EMAIL GEN]  ? Generating email for John @ Notion...
[EMAIL SENT] ? you+test1@gmail.com
[REPLY]      ? Received reply from john@notion.so ? classified: interested
[CALENDLY]   ? Meeting link sent to john@notion.so
[INVOICE]    ? Stripe invoice created ? https://invoice.stripe.com/...
[STATUS]     ? Lead john@notion.so marked as invoiced
```

---

## Pipeline Stage Reference

### `csv_reader.py`
- `load_leads(path)` � returns list of lead dicts
- `mark_lead_status(path, email, status)` � updates CSV in-place

### `research.py`
- `research_company(website, company, notes)` � returns 2-3 sentence Nemotron summary

### `email_agent.py`
- `generate_email(lead, research_summary)` � returns `{subject, body}` dict
- `send_email(to, subject, body)` � sends via Gmail SMTP
- `check_replies(leads)` � polls IMAP, returns list of reply dicts
- `analyze_reply(body)` � returns one of: `interested` | `not_interested` | `needs_more_info` | `unsubscribe`

### `scheduler.py`
- `qualify_lead(lead, analysis)` � returns `True` if worth pursuing
- `schedule_meeting(lead)` � sends Calendly link via email

### `billing.py`
- `create_invoice(lead, amount_cents, description)` � creates Stripe invoice, returns hosted URL
- `check_payment_status(email)` � returns `"paid"` or current invoice status

---

## Lead Status Flow

```
new ? emailed ? meeting_sent ? invoiced ? closed_won
                      |
               (not_interested ? stopped)
               (unsubscribe    ? stopped)
```

---

## How to Verify It Worked

1. **Emails sent**: Check your Gmail Sent folder for outgoing emails.
2. **CSV updated**: Open `data/leads.csv` � status should change from `new` ? `emailed`.
3. **Reply detection**: Send a test reply from a lead email address; check console output for `[REPLY]`.
4. **Calendly link**: Verify the lead received a meeting email with your Calendly URL.
5. **Stripe invoice**: Log into your Stripe dashboard ? Invoices tab; confirm the invoice exists and was emailed.
6. **Final status**: After payment, `data/leads.csv` should show `closed_won` for that lead.

For quick smoke testing without real leads, use Gmail `+alias` addresses
(e.g., `you+test1@gmail.com`) � they deliver to your inbox but register as
distinct senders/recipients.

---

## Common Pitfalls

### Gmail SMTP authentication fails
- **Cause**: Using your Google account password instead of an App Password.
- **Fix**: Generate an App Password at https://myaccount.google.com/apppasswords and set it as `SMTP_PASSWORD`.

### Playwright scraping returns empty text
- **Cause**: Playwright browsers not installed, or site blocks headless browsers.
- **Fix**: Run `python -m playwright install chromium`. For bot-protected sites, add a realistic `user_agent` and `page.wait_for_timeout(2000)` before extracting text.

### Nemotron returns empty or malformed email
- **Cause**: `NVIDIA_BASE_URL` is wrong, or the model name does not match your endpoint.
- **Fix**: Verify the base URL and model identifier in your NVIDIA NIM dashboard. Check `NVIDIA_API_KEY` has sufficient credits.

### Stripe invoice creation fails with `No such customer`
- **Cause**: `billing.py` tries to fetch a customer before creating one.
- **Fix**: Ensure `billing.create_invoice()` checks for an existing customer by email first; if absent, creates one before attaching the invoice item.

### IMAP check_replies() finds no emails
- **Cause**: Gmail IMAP is disabled, or the App Password does not have IMAP scope.
- **Fix**: Enable IMAP in Gmail Settings ? See all settings ? Forwarding and POP/IMAP.

### Lead status not updating in CSV
- **Cause**: `mark_lead_status()` uses email as the key; if the email in the CSV does not exactly match the `to` address used to send, no row is updated.
- **Fix**: Ensure email casing and formatting are consistent throughout the pipeline.

### Calendly API key errors
- **Cause**: `CALENDLY_API_KEY` is missing or expired.
- **Fix**: If you only need to send the link (not create events via API), bypass the API and use the static `CALENDLY_LINK` env var directly in `scheduler.schedule_meeting()`.

---

## Extending the Pipeline

To add a new pipeline stage:

1. Create your function in the relevant script (or a new `scripts/my_stage.py`).
2. Import it in `scripts/main.py`.
3. Add a new `elif lead["status"] == "your_status":` branch in the main loop.
4. Call `csv_reader.mark_lead_status()` at the end to advance the status.
5. Update `data/leads.csv` column docs and this SKILL.md accordingly.
