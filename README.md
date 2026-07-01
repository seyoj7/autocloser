# AutoCloser

> **Autonomous B2B Sales Pipeline Agent** — From cold lead to paid invoice, zero manual work.
>
> Built for the [Hermes Agent Accelerated Business Hackathon](https://github.com/NousResearch/hermes-agent) presented by **NVIDIA**, **Stripe**, and **Nous Research**.

AutoCloser is a fully autonomous sales agent that runs as a [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill. Give it a CSV of leads and it will:

1. **Research** each company by scraping their website with Playwright
2. **Write** hyper-personalized cold emails using NVIDIA Nemotron
3. **Send** them via Gmail SMTP with automatic email threading
4. **Monitor** replies and classify sentiment (interested / not interested / needs more info)
5. **Follow up** intelligently when a lead asks questions
6. **Schedule** meetings by sending Calendly links to warm leads
7. **Invoice** closed deals via Stripe — creating customers, generating invoices, and tracking payment
8. **Repeat** every 15 minutes, 24/7, completely hands-free

---

## Why AutoCloser?

| Traditional Sales Tools | AutoCloser |
|---|---|
| Generates emails, human sends them | Generates **and sends** emails autonomously |
| Human reads replies, decides next step | AI classifies replies and acts instantly |
| Human books meetings manually | Auto-sends Calendly links to interested leads |
| Separate invoicing workflow | Creates and sends Stripe invoices in the same pipeline |
| Requires constant babysitting | Runs 24/7 as a background Hermes Agent skill |
| Fixed templates | Dynamic: tone, word count, sender name — all configurable via CLI or settings |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent Orchestration | Hermes (tool-calling loop) |
| LLM | NVIDIA Nemotron 3 Ultra (`nvidia/llama-3.3-nemotron-super-49b-v1`) via OpenAI-compatible API |
| Web Scraping | Playwright Chromium (headless, with human-like scrolling) |
| Email (Outbound) | Gmail SMTP (TLS on port 587) |
| Email (Inbound) | Gmail IMAP (SSL) |
| Scheduling | Calendly API + booking links |
| Payments | Stripe API (customers, invoices, payment status) |
| Runtime | Python 3.10+ |

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Gmail account** with [App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled)
- **[NVIDIA NIM API key](https://build.nvidia.com/)** for Nemotron
- **[Stripe API key](https://dashboard.stripe.com/apikeys)** (use `sk_test_...` for demo)
- **[Calendly](https://calendly.com/)** booking link + API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AutoCloser.git
   cd AutoCloser
   ```

2. **Configure your environment:**
   ```bash
   cp .env.example .env
   ```
   Fill in `.env` with your credentials:
   ```env
   NVIDIA_API_KEY=nvapi-...
   NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
   SMTP_USER=you@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   CALENDLY_LINK=https://calendly.com/yourname/15min
   CALENDLY_API_KEY=eyJ...
   STRIPE_SECRET_KEY=sk_test_...
   ```

3. **Set up the virtual environment & dependencies:**

   **Linux / macOS:**
   ```bash
   bash scripts/setup.sh
   ```

   **Windows (manual):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

4. **Seed your leads:**

   Copy the example data to get started:
   ```bash
   cp data/example/leads.csv data/leads.csv
   cp data/example/services.csv data/services.csv
   cp data/example/settings.json data/settings.json
   ```
   Then edit `data/leads.csv` with your actual prospects:
   ```csv
   company,contact,email,website,notes,status
   Notion,Jane,jane@notion.so,notion.so,Productivity and docs platform,new
   Linear,Tom,tom@linear.app,linear.app,Issue tracking for dev teams,new
   ```

5. **Run the pipeline:**
   ```bash
   # Interactive mode (prompts for meeting confirmation / invoicing)
   python scripts/main.py

   # Fully autonomous (no prompts)
   python scripts/main.py --no-input

   # Single cycle, then exit
   python scripts/main.py --single-cycle --no-input
   ```

---

## Project Structure

```
AutoCloser/
│
├── .env.example          # Template for API keys and credentials
├── .gitignore
├── README.md
├── requirements.txt      # Python dependencies
│
├── scripts/
│   ├── __init__.py
│   ├── main.py           # Central orchestrator — runs the pipeline loop
│   ├── csv_reader.py     # Lead & service state management (CSV database)
│   ├── research.py       # Scrapes websites + summarizes with Nemotron
│   ├── email_agent.py    # Generates, sends, and monitors emails via SMTP/IMAP
│   ├── scheduler.py      # Qualifies leads and sends Calendly meeting links
│   ├── billing.py        # Stripe integration — invoices and payment tracking
│   ├── cli.py            # Command-line interface for managing leads/services/settings
│   ├── settings.py       # Runtime-configurable settings (JSON-backed)
│   ├── notifications.py  # Real-time pipeline event notifications + logging
│   └── setup.sh          # One-time environment setup script
│
├── data/
│   ├── leads.csv         # Active lead database (gitignored)
│   ├── services.csv      # Billable services catalog (gitignored)
│   ├── settings.json     # User configuration (gitignored)
│   ├── notifications.log # Event log (gitignored)
│   └── example/          # Example seed data (committed)
│       ├── leads.csv
│       ├── services.csv
│       └── settings.json
│
└── .agents/
    └── skills/
        └── autocloser/   # Hermes Agent skill definition
```

---

## Pipeline Flow

AutoCloser advances each lead through a state machine stored in the `status` column of `leads.csv`:

```
new → emailed → followup_sent ─┐
                                ├→ meeting_sent → meeting_booked → meeting_completed → invoiced → closed_won
                 emailed ───────┘
                                └→ not_interested (can be re-qualified if lead replies again)
```

### Step-by-Step Breakdown

| Step | Status Trigger | What Happens |
|---|---|---|
| **1. Research** | `new` | Playwright scrapes the lead's website, extracts visible text (2000 chars max), sends it to Nemotron for a 2–3 sentence business summary |
| **2. Generate Email** | `new` | Nemotron writes a personalized cold email using the research context, respecting the configured tone and word limit |
| **3. Send Email** | `new` | Email is sent via Gmail SMTP. If a prior thread exists for this lead, the email is threaded as a reply. Status → `emailed` |
| **4. Check Replies** | `emailed` | IMAP polls the inbox for replies from this lead (matched by thread subject, then by References header, then by sender address) |
| **5. Analyze Reply** | `emailed` | Nemotron classifies the reply as `interested`, `not_interested`, `needs_more_info`, or `unsubscribe` |
| **6. Follow Up** | `emailed` | If `needs_more_info`: Nemotron generates a helpful follow-up email answering their question. Status → `followup_sent` |
| **7. Qualify & Schedule** | `emailed` / `followup_sent` | If `interested`: a Calendly booking link is sent. Status → `meeting_sent` |
| **8. Meeting Booking** | `meeting_sent` | Checks for a reply to the meeting link. If received, status → `meeting_booked` |
| **9. Meeting Completion** | `meeting_booked` | In interactive mode, prompts to confirm meeting completion. In `--no-input` mode, auto-confirms. Status → `meeting_completed` |
| **10. Invoice** | `meeting_completed` | Selects a service from `services.csv`, creates a Stripe customer (or finds existing), generates an invoice, finalizes it, and emails the hosted invoice URL. Status → `invoiced` |
| **11. Payment Check** | `invoiced` | Queries Stripe for the latest invoice status. If `paid`, status → `closed_won` 🎉 |

**Re-engagement:** Leads marked `not_interested` are still checked for new replies each cycle. If they reply positively, they re-enter the pipeline.

---

## CLI Reference

The CLI (`scripts/cli.py`) lets you manage leads, services, and settings without editing files directly.

```bash
python scripts/cli.py <command> [options]
```

### Lead Management

```bash
# List all leads with status
python scripts/cli.py list-leads

# Add a new lead
python scripts/cli.py add-lead \
  --company "Notion" \
  --contact "Jane" \
  --email "jane@notion.so" \
  --website "notion.so" \
  --notes "Productivity platform"

# Update a lead's field
python scripts/cli.py update-lead \
  --email "jane@notion.so" \
  --field status \
  --value new

# Remove a lead
python scripts/cli.py remove-lead --email "jane@notion.so"
```

**Valid status values:** `new`, `emailed`, `followup_sent`, `meeting_sent`, `meeting_booked`, `meeting_completed`, `invoiced`, `closed_won`, `not_interested`

**Updatable fields:** `company`, `contact`, `email`, `website`, `notes`, `status`

### Service Management

Services define what you invoice leads for. They live in `data/services.csv`.

```bash
# List all services
python scripts/cli.py list-services

# Add a new service (amount is in cents: 15000 = $150.00)
python scripts/cli.py add-service \
  --id "5" \
  --name "onboarding" \
  --description "Full onboarding session" \
  --amount 25000
```

### Pipeline Status

```bash
# Show a visual pipeline funnel
python scripts/cli.py pipeline-status
```

Output:
```
══════════════════════════════════════════════════
  📊 PIPELINE FUNNEL — 3 leads
══════════════════════════════════════════════════
  📧 emailed              ██████░░░░░░░░ 2 (67%)
  🎉 closed_won           ███░░░░░░░░░░░ 1 (33%)
══════════════════════════════════════════════════
```

### Settings

```bash
# Show all settings
python scripts/cli.py show-settings

# Update a setting
python scripts/cli.py set --key sender_name --value "Alice"
python scripts/cli.py set --key email_tone --value "professional"
python scripts/cli.py set --key max_email_words --value 150

# Reset all settings to defaults
python scripts/cli.py reset-settings
```

---

## Settings Reference

Settings are stored in `data/settings.json` and can be changed at runtime via the CLI. All modules read from this file dynamically.

| Setting | Type | Default | Description |
|---|---|---|---|
| `sender_name` | string | `"Alex"` | Name used to sign off emails |
| `company_name` | string | `"Autocloser"` | Your company name in email signatures |
| `calendly_link` | string | `"https://calendly.com/yourname/15min"` | Calendly booking URL sent to qualified leads |
| `cycle_interval_minutes` | int | `15` | Minutes between pipeline cycles in loop mode |
| `pipeline_mode` | string | `"ai"` | Pipeline mode (`ai` for Nemotron-powered) |
| `email_tone` | string | `"conversational"` | Tone for generated emails (e.g., `conversational`, `professional`, `casual`) |
| `auto_confirm_meetings` | bool | `false` | Auto-mark meetings as completed (skips prompt) |
| `auto_create_invoices` | bool | `false` | Auto-create invoices after meetings (skips prompt) |
| `default_service_id` | string | `"2"` | Default service ID when invoicing in `--no-input` mode |
| `max_email_words` | int | `100` | Maximum word count for generated cold emails |
| `notifications_enabled` | bool | `true` | Enable/disable real-time pipeline notifications |

---

## Data Files

### `data/leads.csv`

The lead database. Each row is a prospect tracked through the pipeline.

| Column | Description |
|---|---|
| `company` | Company name |
| `contact` | Contact person's first name |
| `email` | Contact email address (used as unique identifier) |
| `website` | Company website URL (scraped for research) |
| `notes` | Optional notes — used as fallback if scraping fails |
| `status` | Current pipeline status (see status flow above) |

### `data/services.csv`

The catalog of billable services offered during invoicing.

| Column | Description |
|---|---|
| `id` | Unique service identifier |
| `name` | Short name (e.g., `strategy_session`) |
| `description` | Human-readable description shown on the invoice |
| `amount_cents` | Price in cents (e.g., `15000` = $150.00) |

### `data/settings.json`

Runtime configuration. See the [Settings Reference](#settings-reference) above.

### `data/notifications.log`

Append-only log of all pipeline events. Each line records a timestamped status change:
```
[2026-07-01 14:30:00] 📧 Cold email sent to Jane at Notion | jane@notion.so | emailed
[2026-07-01 15:15:00] 📅 Meeting link sent to Jane at Notion | jane@notion.so | meeting_sent
```

---

## Module API Reference

### `csv_reader.py` — State Management

| Function | Signature | Description |
|---|---|---|
| `load_leads` | `(path: str) → list[dict]` | Reads all leads from CSV into a list of dicts |
| `load_services` | `(path: str) → list[dict]` | Reads all services (auto-casts `amount_cents` to int) |
| `mark_lead_status` | `(path, email, new_status) → bool` | Updates a lead's status in-place and fires a notification |
| `add_lead` | `(path, company, contact, email, website, notes, status) → bool` | Appends a new lead (duplicate emails are rejected) |
| `update_lead_field` | `(path, email, field, value) → bool` | Updates any field for a lead identified by email |
| `remove_lead` | `(path, email) → bool` | Removes a lead from the CSV |
| `add_service` | `(path, service_id, name, description, amount_cents) → bool` | Appends a new service (duplicate IDs are rejected) |

### `research.py` — Company Research

| Function | Signature | Description |
|---|---|---|
| `research_company` | `(website, company, notes) → str` | Scrapes the website with Playwright, summarizes with Nemotron. Falls back to `notes` if scraping fails |

Internally uses `_scrape_website()` (Playwright with human-like scrolling to avoid bot detection) and `_summarize_with_nemotron()`.

### `email_agent.py` — Email Generation & Monitoring

| Function | Signature | Description |
|---|---|---|
| `generate_email` | `(lead, research_summary) → dict` | Returns `{subject, body}` — a personalized cold email |
| `generate_followup` | `(lead, reply_body) → dict` | Returns `{subject, body}` — a follow-up answering the lead's question |
| `send_email` | `(to, subject, body) → bool` | Sends via Gmail SMTP. Auto-threads if a prior conversation exists |
| `check_replies` | `(leads: list) → list[dict]` | Polls IMAP inbox for replies matching the given leads. Returns `[{sender, subject, body}]` |
| `analyze_reply` | `(reply_body) → str` | Classifies a reply as `interested`, `not_interested`, `needs_more_info`, or `unsubscribe` |

**Email threading:** `send_email` searches the Gmail Sent Mail folder for prior messages to the same address. If found, it sets `In-Reply-To` and `References` headers so replies appear in the same Gmail thread.

**Reply matching:** `check_replies` matches incoming mail by thread subject first, then by `References` header, and finally by sender `FROM` address as a fallback.

### `scheduler.py` — Lead Qualification & Meeting Scheduling

| Function | Signature | Description |
|---|---|---|
| `qualify_lead` | `(lead, reply_analysis) → bool` | Returns `True` if the reply is `interested` or `needs_more_info` |
| `schedule_meeting` | `(lead) → str` | Sends an email with the Calendly booking link |
| `check_meeting_completed` | `(lead_email) → bool` | Queries the Calendly API to check if a scheduled event has ended |

### `billing.py` — Stripe Invoicing

| Function | Signature | Description |
|---|---|---|
| `create_invoice` | `(lead, amount, description) → str` | Creates a Stripe customer (or finds existing), attaches an invoice item, finalizes the invoice, emails the hosted URL, and returns it |
| `check_payment_status` | `(lead_email) → str` | Looks up the customer by email on Stripe and returns the latest invoice status (`paid`, `open`, `void`, `unknown`) |

### `notifications.py` — Event System

| Function | Signature | Description |
|---|---|---|
| `notify` | `(lead, new_status, detail) → None` | Prints a formatted notification to stdout and appends to `notifications.log` |
| `notify_summary` | `(leads: list) → None` | Prints a full pipeline funnel summary with emoji status bars |

Notifications are automatically triggered by `csv_reader.mark_lead_status()` — no manual calls needed.

### `settings.py` — Configuration

| Function | Signature | Description |
|---|---|---|
| `load_settings` | `() → dict` | Loads `data/settings.json` merged with defaults |
| `save_settings` | `(settings) → None` | Writes settings to disk |
| `get` | `(key, default) → any` | Gets a setting value (lazy-loads on first access) |
| `update` | `(key, value) → bool` | Updates a setting with automatic type coercion |
| `reset` | `() → dict` | Resets all settings to defaults |
| `display` | `() → str` | Returns a formatted settings table string |

---

## Running Modes

### Interactive (Default)
```bash
python scripts/main.py
```
Prompts you to confirm meeting completion and invoice creation. Useful when you want human-in-the-loop control.

### Autonomous
```bash
python scripts/main.py --no-input
```
Fully hands-free. Auto-confirms meetings, auto-selects the default service for invoicing, and loops every 15 minutes.

### Single Cycle
```bash
python scripts/main.py --single-cycle --no-input
```
Runs the pipeline exactly once and exits. Ideal for cron jobs or testing.

### Hermes Agent Integration
AutoCloser is natively designed to run as a Hermes Agent skill under `.agents/skills/autocloser/`. When triggered, Hermes executes `main.py --no-input` on a schedule, monitoring your inbox, qualifying leads, booking meetings, and sending invoices — all in the background.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | ✅ | NVIDIA NIM API key for Nemotron |
| `NVIDIA_BASE_URL` | ✅ | API endpoint (e.g., `https://integrate.api.nvidia.com/v1`) |
| `SMTP_USER` | ✅ | Gmail address for sending and receiving email |
| `SMTP_PASSWORD` | ✅ | Gmail App Password (16-character, spaces included) |
| `STRIPE_SECRET_KEY` | ⬚ | Stripe secret key (`sk_test_...` for demo, `sk_live_...` for production) |
| `CALENDLY_LINK` | ⬚ | Your Calendly booking URL |
| `CALENDLY_API_KEY` | ⬚ | Calendly API key (for meeting completion checks) |
| `SENDER_NAME` | ⬚ | Fallback sender name if `settings.json` is unavailable |
| `COMPANY_NAME` | ⬚ | Fallback company name if `settings.json` is unavailable |

> ✅ = Required for core functionality. ⬚ = Optional / required only for specific features.

---

## Demo Tips

- Seed `data/leads.csv` with 3–5 leads using Gmail `+alias` addresses (e.g., `you+test1@gmail.com`, `you+test2@gmail.com`) so you can reply to yourself and watch the pipeline advance.
- Use **Stripe test mode** (`sk_test_...`) — invoices are created in the Stripe dashboard without real charges.
- Run with `--single-cycle --no-input` for a quick end-to-end demo (~30–60 seconds per lead).
- Check `data/notifications.log` for a complete audit trail of every pipeline event.
- Use `python scripts/cli.py pipeline-status` to see a visual funnel at any time.

---

## License

MIT License