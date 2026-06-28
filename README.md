# AutoCloser — Autonomous B2B Sales Agent

> **Built for the [Hermes Agent Accelerated Business Hackathon](http://discord.gg/nousresearch/PFbQZMesC)**  
> Powered by NVIDIA Nemotron 3 Ultra · Stripe · Nous Research Hermes

AutoCloser is a fully autonomous B2B sales pipeline agent. Drop in a CSV of leads and watch it research companies, write personalized cold emails, handle replies, qualify interest, book meetings, issue invoices, and confirm payment — all without human input.

---

## What It Does

```
Lead CSV  →  Research  →  Cold Email  →  Reply Analysis  →  Meeting  →  Invoice  →  Closed Won
```

The agent runs a 10-step pipeline for every lead:

| Step | Skill | What Happens |
|------|-------|--------------|
| 1 | `csv_reader` | Load all leads and their current pipeline status |
| 2 | `research` | Playwright scrapes company homepage (human-like scroll) |
| 3 | `research` | NVIDIA Nemotron summarizes the page into a 2-3 sentence business intel brief |
| 4 | `email_agent` | Nemotron writes a short, hyper-personalized cold email |
| 5 | `email_agent` | Email sent via Gmail SMTP; thread-aware (replies stay in same thread) |
| 6 | `email_agent` | Gmail IMAP polled for replies matched by subject + sender |
| 7 | `email_agent` | Nemotron classifies reply: `interested / not_interested / needs_more_info / unsubscribe` |
| 8 | `scheduler` | Qualify lead → send Calendly booking link if interested |
| 9 | `billing` | Create Stripe invoice, email the hosted payment link |
| 10 | `billing` | Check payment status → mark `closed_won` when paid |

---

## Lead Status Flow

```
new
 └─→ emailed
      └─→ meeting_sent
           └─→ invoiced
                └─→ closed_won
           └─→ not_interested  (can recover if they reply later)
```

Status is written back to `data/leads.csv` after every action so the pipeline is resumable — run `main.py` again at any time and it picks up exactly where it left off.

---

## Tech Stack

| Layer | Tool |
|---|---|
| LLM / AI | NVIDIA Nemotron 3 Ultra (`llama-3.3-nemotron-super-49b-v1`) |
| Web Scraping | Playwright (Chromium, human scroll simulation) |
| Email (SMTP) | Gmail SMTP + App Password |
| Email (IMAP) | Gmail IMAP — thread-aware reply matching |
| Payments | Stripe Python SDK — invoices, customer lookup, payment status |
| Scheduling | Calendly link delivery via email |
| Language | Python 3.11+ |

---

## Project Structure

```
AutoCloser/
│
├── main.py              # Orchestrator — runs the full 10-step pipeline
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
│
├── data/
│   └── leads.csv        # Your lead list (edit this!)
│
└── skills/
    ├── csv_reader.py    # Load leads; update status in CSV
    ├── research.py      # Scrape + Nemotron summarize company website
    ├── email_agent.py   # Generate, send, receive, and classify emails
    ├── scheduler.py     # Qualify leads and send meeting links
    └── billing.py       # Stripe invoice creation and payment tracking
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourname/autocloser
cd autocloser
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
NVIDIA_API_KEY=nvapi-...          # Get at: https://build.nvidia.com
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

SMTP_USER=you@gmail.com           # Gmail address
SMTP_PASSWORD=xxxx xxxx xxxx xxxx # Gmail App Password (not your login password)

STRIPE_SECRET_KEY=sk_test_...     # Stripe test key: https://dashboard.stripe.com/apikeys
CALENDLY_LINK=https://calendly.com/yourname/15min
```

> **Gmail App Password**: Go to myaccount.google.com/apppasswords → create a password for "Mail".

### 3. Add your leads

Edit `data/leads.csv`:

```csv
company,contact,email,website,notes,status
Acme Corp,Alice,alice@acme.com,acme.com,SaaS for HR teams,new
Globex,Bob,bob@globex.io,globex.io,Enterprise analytics,new
```

### 4. Run

```bash
python main.py
```

Logs print to stdout in real time. The CSV is updated after each action.

---

## Skills API

### `csv_reader.py`

```python
load_leads(path: str) -> list[dict]
# Reads leads.csv, returns list of lead dicts

mark_lead_status(path: str, email: str, new_status: str) -> bool
# Updates the status field for a specific lead by email
```

### `research.py`

```python
research_company(website: str, company: str, notes: str = "") -> str
# Scrapes homepage with Playwright, summarizes with Nemotron
# Returns 2-3 sentence business intel brief
# Falls back to notes field if website unreachable
```

### `email_agent.py`

```python
generate_email(lead: dict, research_summary: str) -> dict
# Uses Nemotron to write personalized cold email
# Returns {"subject": "...", "body": "..."}

send_email(to: str, subject: str, body: str) -> bool
# Sends via Gmail SMTP; detects existing thread and replies in-thread

check_replies(leads: list) -> list[dict]
# Polls Gmail IMAP; matches replies by subject thread
# Returns [{"sender": "...", "subject": "...", "body": "..."}]

analyze_reply(reply_body: str) -> str
# Classifies reply via Nemotron
# Returns one of: interested | not_interested | needs_more_info | unsubscribe
```

### `scheduler.py`

```python
qualify_lead(lead: dict, reply_analysis: str) -> bool
# Returns True if analysis is "interested" or "needs_more_info"

schedule_meeting(lead: dict) -> str
# Sends Calendly booking link via email; returns confirmation string
```

### `billing.py`

```python
create_invoice(lead: dict, amount: int, description: str) -> str
# Creates Stripe customer + invoice item + finalizes invoice
# Emails hosted_invoice_url to lead; returns URL

check_payment_status(lead_email: str) -> str
# Looks up latest Stripe invoice for customer
# Returns: paid | open | void | draft | uncollectible | unknown
```

---

## How NVIDIA Nemotron Powers This

Nemotron 3 Ultra (`nvidia/llama-3.3-nemotron-super-49b-v1`) is called 3x per lead:

1. **Research** — Converts raw homepage HTML into structured business intel
2. **Email Generation** — Writes concise, personalized B2B cold emails (<=100 words)
3. **Reply Classification** — Classifies incoming emails into 4 intent categories with near-zero latency

The model is accessed via the NVIDIA API using an OpenAI-compatible client.

---

## How Stripe Powers This

- **Customer creation** — finds or creates a Stripe customer by email
- **Invoice items** — line-item descriptions attached to the customer
- **Invoice finalization** — generates a hosted payment page
- **Payment status polling** — queries the latest invoice status per customer

Use `sk_test_...` keys during development. Switch to live keys for production.

---

## Demo Tips

- Seed `data/leads.csv` with 3 real-ish companies (set status to `new`)
- Use Gmail `+alias` trick (`you+test1@gmail.com`) so you can be both sender and "recipient" in a demo
- Use Stripe test mode — payments can be simulated with card `4242 4242 4242 4242`
- The full pipeline for one lead runs in ~30-60 seconds end to end
- Re-running `main.py` is safe — it skips already-processed leads based on status

---

## Hackathon Context

Built for the **Hermes Agent Accelerated Business Hackathon** presented by:

- **NVIDIA** — Nemotron 3 Ultra for reasoning, research, and copywriting
- **Stripe** — Autonomous invoicing and payment verification
- **Nous Research** — Hermes agent framework and tool-calling loop

> *"We want to see what kind of business tooling you can build on top of this foundation, whether it's a fully automated company or a framework to accelerate enterprise functions."*

AutoCloser demonstrates a **fully automated sales company** that can close deals without a human ever touching the keyboard.

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `NVIDIA_API_KEY` | NVIDIA API key for Nemotron |
| `NVIDIA_BASE_URL` | API base URL, e.g. `https://integrate.api.nvidia.com/v1` |
| `SMTP_USER` | Gmail address used to send/receive email |
| `SMTP_PASSWORD` | Gmail App Password (16-char, not your account password) |
| `STRIPE_SECRET_KEY` | Stripe secret key — use `sk_test_...` for testing |
| `CALENDLY_LINK` | Your Calendly booking URL |

---

## License

MIT — build on it, fork it, ship it.
