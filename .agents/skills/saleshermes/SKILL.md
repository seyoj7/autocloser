---
name: AutoCloser
description: >
  AutoCloser is an autonomous B2B sales pipeline agent. Given a CSV of leads,
  it researches each company's website with Playwright, generates hyper-personalized
  cold emails via NVIDIA Nemotron, sends them over Gmail SMTP, monitors the inbox
  for replies, classifies sentiment, dispatches Calendly meeting links to warm leads,
  and creates & delivers Stripe invoices — updating lead status in the CSV at every step.
  Trigger this skill when the user asks to run, fix, extend, or debug any part of
  the AutoCloser outreach pipeline (research, email, scheduling, billing, lead status).
---

# AutoCloser — Hermes Skill

## Overview

AutoCloser exposes every pipeline action as an **individual callable tool** via
`scripts/skill_api.py`. You call one tool at a time, inspect the JSON result,
then decide the next step.

> **DO NOT** run `main.py`. That file runs its own internal Nemotron agent loop
> and will conflict with Hermes. Always use `skill_api.py` instead.

---

## How to Call a Tool

Every tool call follows this pattern:

```bash
python scripts/skill_api.py '{"tool": "<tool_name>", "args": {...}}'
```

Every call:
- Prints **one JSON object** to stdout
- Returns `{"ok": true, ...result fields...}` on success
- Returns `{"ok": false, "error": "..."}` on failure
- Exits with code `0` (success) or `1` (error)

---

## Tool Reference

### `load_leads`
Load all leads from `data/leads.csv` with their current pipeline status.
**Always call this first** so you know what needs to be done.

```bash
python scripts/skill_api.py '{"tool": "load_leads"}'
```
Returns: `{"ok": true, "leads": [...], "count": N}`

---

### `research_company`
Scrape a lead's website with Playwright and summarize it using Nemotron.

```bash
python scripts/skill_api.py '{"tool": "research_company", "args": {"lead_email": "john@notion.so"}}'
```
Returns: `{"ok": true, "summary": "...", "company": "Notion"}`

---

### `generate_email`
Generate a personalized cold email using the research summary.

```bash
python scripts/skill_api.py '{
  "tool": "generate_email",
  "args": {
    "lead_email": "john@notion.so",
    "research_summary": "Notion is a productivity tool..."
  }
}'
```
Returns: `{"ok": true, "subject": "...", "body": "..."}`

---

### `generate_followup`
Write a follow-up email addressing a lead's specific question or objection.

```bash
python scripts/skill_api.py '{
  "tool": "generate_followup",
  "args": {
    "lead_email": "john@notion.so",
    "reply_body": "Can you tell me more about pricing?"
  }
}'
```
Returns: `{"ok": true, "subject": "...", "body": "..."}`

---

### `send_email`
Send an email via Gmail SMTP. Auto-threads into existing conversations.

```bash
python scripts/skill_api.py '{
  "tool": "send_email",
  "args": {
    "to": "john@notion.so",
    "subject": "Quick question about Notion docs",
    "body": "Hi John, ..."
  }
}'
```
Returns: `{"ok": true, "sent": true, "to": "john@notion.so"}`

---

### `check_replies`
Poll Gmail IMAP for any replies from a specific lead (last 2 days).

```bash
python scripts/skill_api.py '{"tool": "check_replies", "args": {"lead_email": "john@notion.so"}}'
```
Returns: `{"ok": true, "replies": [...], "count": N}`

---

### `analyze_reply`
Classify a reply body with Nemotron into one of:
`interested` | `not_interested` | `needs_more_info` | `unsubscribe`

```bash
python scripts/skill_api.py '{
  "tool": "analyze_reply",
  "args": {"reply_body": "Hi, we're interested! Tell me more."}
}'
```
Returns: `{"ok": true, "classification": "interested"}`

---

### `qualify_lead`
Determine if a lead is worth pursuing based on their reply classification.

```bash
python scripts/skill_api.py '{
  "tool": "qualify_lead",
  "args": {"lead_email": "john@notion.so", "reply_analysis": "interested"}
}'
```
Returns: `{"ok": true, "qualified": true, "company": "Notion"}`

---

### `schedule_meeting`
Send a Calendly booking link to a qualified lead via email.

```bash
python scripts/skill_api.py '{"tool": "schedule_meeting", "args": {"lead_email": "john@notion.so"}}'
```
Returns: `{"ok": true, "result": "Meeting link sent to John at john@notion.so"}`

---

### `create_invoice`
Create and email a Stripe invoice to the lead. If `amount_cents` is omitted or 0,
the first service in `data/services.csv` is used automatically.

```bash
python scripts/skill_api.py '{
  "tool": "create_invoice",
  "args": {
    "lead_email": "john@notion.so",
    "amount_cents": 200000,
    "description": "2-hour consulting session"
  }
}'
```
Returns: `{"ok": true, "invoice_url": "https://invoice.stripe.com/...", "invoiced": true}`

---

### `check_payment_status`
Check Stripe payment status for a lead's latest invoice.
Automatically marks lead as `closed_won` if paid.

```bash
python scripts/skill_api.py '{"tool": "check_payment_status", "args": {"lead_email": "john@notion.so"}}'
```
Returns: `{"ok": true, "payment_status": "paid", "lead_email": "john@notion.so"}`

---

### `mark_lead_status`
Update a lead's pipeline stage in `data/leads.csv`.

Valid statuses: `emailed` | `followup_sent` | `meeting_sent` | `meeting_booked` |
`meeting_completed` | `invoiced` | `closed_won` | `not_interested`

```bash
python scripts/skill_api.py '{
  "tool": "mark_lead_status",
  "args": {"lead_email": "john@notion.so", "new_status": "emailed"}
}'
```
Returns: `{"ok": true, "updated": true, "lead_email": "john@notion.so", "new_status": "emailed"}`

---

## Full Pipeline Workflow

Process leads one at a time. For each lead, follow its current `status`:

### status = `new`
1. `research_company` → get intel
2. `generate_email` with research summary → get `{subject, body}`
3. `send_email` with those values
4. `mark_lead_status` → `emailed`

### status = `emailed` or `followup_sent`
1. `check_replies` → inspect replies
2. For each reply: `analyze_reply`
   - `interested` → `qualify_lead` → `schedule_meeting` → `mark_lead_status` → `meeting_sent`
   - `needs_more_info` → `generate_followup` → `send_email` → `mark_lead_status` → `followup_sent`
   - `not_interested` / `unsubscribe` → `mark_lead_status` → `not_interested`
3. No replies → do nothing, check next cycle

### status = `meeting_sent`
1. `check_replies` → if lead confirms meeting: `mark_lead_status` → `meeting_booked`

### status = `meeting_booked` or `meeting_completed`
1. `create_invoice` → Stripe invoice created and emailed
2. Status auto-advances to `invoiced`

### status = `invoiced`
1. `check_payment_status`
2. If `paid` → status auto-advances to `closed_won`

### status = `closed_won` or `not_interested`
→ Skip

---

## Lead Status Flow

```
new → emailed → meeting_sent → meeting_booked → meeting_completed → invoiced → closed_won
         ↓
    followup_sent → (same as emailed)
         ↓
    not_interested (dead end, unless they reply again)
```

---

## Required Environment Variables

Set in `.env` (copy from `.env.example`):

| Variable            | Purpose                                        |
|---------------------|------------------------------------------------|
| `NVIDIA_API_KEY`    | NVIDIA NIM API key for Nemotron                |
| `NVIDIA_BASE_URL`   | Base URL for NVIDIA NIM API                    |
| `SMTP_USER`         | Gmail address for sending/receiving email      |
| `SMTP_PASSWORD`     | Gmail App Password (not account password)      |
| `STRIPE_SECRET_KEY` | Stripe secret key for invoice creation         |
| `CALENDLY_LINK`     | Public Calendly booking URL                    |
| `CALENDLY_API_KEY`  | Calendly API key                               |
| `SENDER_NAME`       | Your name (used in email signatures)           |
| `COMPANY_NAME`      | Your company name (used in email copy)         |

---

## Setup (One-Time)

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# Fill in .env values
```

---

## Common Pitfalls

| Symptom | Fix |
|---------|-----|
| `SMTP auth failed` | Use a Gmail App Password (myaccount.google.com/apppasswords), not your account password |
| `Playwright returns empty` | Run `python -m playwright install chromium` |
| `No lead found with email` | Check email casing matches exactly what's in `data/leads.csv` |
| `Stripe invoice failed` | Verify `STRIPE_SECRET_KEY` is set and valid |
| `check_replies finds nothing` | Enable IMAP in Gmail Settings → Forwarding and POP/IMAP |
