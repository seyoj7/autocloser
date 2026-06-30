---
name: autocloser
description: >
  Autonomous B2B sales pipeline agent. Researches companies, sends personalized
  cold emails, monitors replies, schedules meetings, and sends invoices.
  Trigger this skill when the user asks to run the sales pipeline, manage leads,
  check pipeline status, or change agent settings.
version: 1.0.0
platforms: [windows, linux, macos]
requires_tools: [terminal]
metadata:
  hermes:
    category: sales-automation
    tags: [b2b, email, crm, pipeline, outreach, sales]
---

# AutoCloser — Autonomous B2B Sales Agent

## IMPORTANT — Read Before Running ANY Command

**If this is the first run or venv is missing**, run setup first:

```bash
cd ~/.hermes/skills/autocloser && bash scripts/setup.sh
```

This creates the venv and installs all dependencies. It is safe to re-run.

**After setup is done**, every command MUST be run exactly like this (single line):

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 <command>
```

**If any command fails with "No such file: venv"**, run `bash scripts/setup.sh` first.

The `.env` file is already configured. Do NOT try to read or cat the `.env` file.
Do NOT reinstall packages or recreate the venv unless setup.sh is used.

## When to Use

Trigger this skill when the user asks to:
- **Run the sales pipeline** — "run AutoCloser", "start outreach", "process leads"
- **Add or manage leads** — "add a lead", "remove lead", "update lead", "show leads"
- **Check pipeline status** — "pipeline status", "show funnel", "how are my leads doing"
- **Change settings** — "change sender name", "set email tone", "show settings"
- **Manage services** — "list services", "add a service"

## Commands

### Run the Pipeline (single cycle)

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/main.py --single-cycle --no-input
```

This processes all leads once and exits without asking for interactive confirmation. Takes ~15s per lead.

### Run the Pipeline (continuous loop)

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/main.py --no-input
```

Loops every 15 minutes automatically.


### List Leads

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py list-leads
```

### Add a Lead

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py add-lead --company "CompanyName" --contact "PersonName" --email "person@company.com" --website "company.com" --notes "Optional notes"
```

### Update a Lead

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py update-lead --email "person@company.com" --field status --value meeting_sent
```

Valid fields: `company`, `contact`, `email`, `website`, `notes`, `status`
Valid statuses: `new`, `emailed`, `followup_sent`, `meeting_sent`, `meeting_booked`, `meeting_completed`, `invoiced`, `closed_won`, `not_interested`

### Remove a Lead

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py remove-lead --email "person@company.com"
```

### Pipeline Status

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py pipeline-status
```

### List Services

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py list-services
```

### Add a Service

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py add-service --id 5 --name "workshop" --description "Half-day workshop" --amount 75000
```

Amount is in cents (75000 = $750.00).

### Show Settings

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py show-settings
```

### Update a Setting

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py set --key SETTING_KEY --value NEW_VALUE
```

Available settings:

| Key | Type | Description |
|-----|------|-------------|
| `sender_name` | string | Name in email signatures |
| `company_name` | string | Company name in email copy |
| `calendly_link` | string | Public Calendly booking URL |
| `cycle_interval_minutes` | int | Pipeline loop interval (default 15) |
| `email_tone` | string | Tone: "conversational", "formal", "friendly" |
| `auto_confirm_meetings` | bool | Auto-confirm meetings (true/false) |
| `auto_create_invoices` | bool | Auto-create invoices (true/false) |
| `default_service_id` | string | Default service ID for auto-invoicing |
| `max_email_words` | int | Max word count for generated emails |
| `notifications_enabled` | bool | Enable/disable notifications |

### Reset Settings

```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py reset-settings
```

## Lead Status Flow

```
new → emailed → meeting_sent → meeting_booked → meeting_completed → invoiced → closed_won
         ↓
    followup_sent → (re-enters at emailed flow)
         ↓
    not_interested (can recover if they reply later)
```

## Notifications

The pipeline prints emoji notifications for every status change:
📧 emailed, 📨 followup_sent, 📅 meeting_sent, ✅ meeting_booked,
🤝 meeting_completed, 💰 invoiced, 🎉 closed_won, ❌ not_interested

## Verification

After any command, check results with:
```bash
cd ~/.hermes/skills/autocloser && source venv/bin/activate && python3 scripts/cli.py list-leads
```
