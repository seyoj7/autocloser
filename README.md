# AutoCloser — Autonomous B2B Sales Agent Skill for Hermes

> **Submission for the Hermes Agent Accelerated Business Hackathon**
> Presented by NVIDIA · Stripe · Nous Research

AutoCloser is a **Hermes Agent skill** that turns a CSV of leads into closed deals — fully autonomously. It is powered by **NVIDIA Nemotron 3 Ultra** as the agent brain, uses **Playwright** for deep company research, **Gmail** for outreach, **Calendly** for scheduling, and **Stripe** for billing.

Drop in a CSV of leads. AutoCloser does the rest.

---

## 🤖 How It Works: Hermes Agent Loop

AutoCloser is **not a traditional script**. It is a Hermes-compatible agent that uses **Nemotron's tool-calling capabilities** to autonomously decide what to do next for each lead. Every 15 minutes, the agent wakes up, loads the current lead list, and runs a full reasoning cycle:

```
Nemotron "thinks" → picks a tool → executes it → sees the result → picks the next tool → ...
                    until all leads are processed → CYCLE COMPLETE → sleeps 15 min
```

The model drives the entire pipeline. The code provides the tools. Nemotron decides the order.

---

## 🔁 Agent Pipeline

Each lead progresses through these stages. Nemotron decides the action at every step:

```
new
 │
 ├─ research_company()      → scrape website + summarize with Nemotron
 ├─ generate_email()        → write hyper-personalized cold email
 ├─ send_email()            → send via Gmail SMTP
 └─► emailed
      │
      ├─ check_replies()    → poll Gmail IMAP for replies
      ├─ analyze_reply()    → classify: interested / needs_more_info / not_interested / unsubscribe
      │
      ├─ needs_more_info → generate_followup() → send_email() ──► followup_sent
      │                                                              │
      ├─ interested ──────────────────────────────────────────────┘ │
      │                                                              ▼
      ├─ qualify_lead()     → confirm lead is worth pursuing
      ├─ schedule_meeting() → send Calendly booking link ──────► meeting_sent
      │                                                              │
      │                                                    (lead books meeting)
      │                                                              ▼
      │                                                       meeting_booked
      │                                                              │
      │                                                  confirm_meeting() [human-in-loop]
      │                                                              │
      │                                                       meeting_completed
      │                                                              │
      ├─ create_invoice()   → Stripe invoice created + emailed ─► invoiced
      │                                                              │
      └─ check_payment_status() → Stripe confirms payment ──────► closed_won 🎉
```

---

## 🧠 NVIDIA Nemotron Integration

**Model:** `nvidia/llama-3.3-nemotron-super-49b-v1`

Nemotron is the brain of the agent. It is used for:

| Task | How Nemotron Is Used |
|---|---|
| **Agentic reasoning** | Drives the entire pipeline by choosing and sequencing tool calls |
| **Company research** | Summarizes scraped homepage text into sales-relevant intel |
| **Email generation** | Writes hyper-personalized cold emails from research context |
| **Follow-up drafting** | Crafts context-aware replies to leads' questions |
| **Reply classification** | Classifies inbound replies as `interested`, `needs_more_info`, `not_interested`, or `unsubscribe` |

The agent connects to Nemotron via the OpenAI-compatible API with `tool_choice="auto"`, meaning Nemotron decides each action without hardcoded branching.

---

## 💳 Stripe Integration

AutoCloser uses Stripe to **autonomously close the financial loop**:

- **Provisions Stripe customers** from lead data (company name, email)
- **Creates itemized invoices** from a configurable `services.csv` menu
- **Emails the hosted invoice link** directly to the lead
- **Polls payment status** and advances the lead to `closed_won` upon payment

This makes AutoCloser a true **earn-and-operate** agent — it can generate real revenue without human intervention.

---

## 🛠️ Tool Definitions (Hermes Skill API)

The agent exposes these tools to Nemotron:

| Tool | Description |
|---|---|
| `load_leads` | Load all leads and their current pipeline status from CSV |
| `research_company` | Scrape website with Playwright + summarize with Nemotron |
| `generate_email` | Write a personalized cold email using research intel |
| `generate_followup` | Write a follow-up addressing a lead's specific question |
| `send_email` | Send email via Gmail SMTP (auto-threads replies) |
| `check_replies` | Poll Gmail IMAP for replies from a specific lead |
| `analyze_reply` | Classify reply sentiment with Nemotron |
| `qualify_lead` | Determine if a lead is worth pursuing |
| `schedule_meeting` | Send Calendly booking link to a qualified lead |
| `confirm_meeting` | Human-in-the-loop: confirm meeting completion |
| `create_invoice` | Present service menu, create & send Stripe invoice |
| `check_payment_status` | Poll Stripe for invoice payment status |
| `mark_lead_status` | Persist lead stage to CSV |

---

## 📁 Project Structure

```
Autocloser/
├── .env                    # Secret credentials (never commit)
├── .env.example            # Template for all required env vars
├── requirements.txt        # Python dependencies
├── data/
│   ├── leads.csv           # Lead database — status tracked here
│   └── services.csv        # Billable services menu (Stripe)
├── scripts/
│   ├── main.py             # Hermes Agent loop + Nemotron tool executor
│   ├── csv_reader.py       # Load leads, update statuses, load services
│   ├── research.py         # Playwright scrape + Nemotron summarization
│   ├── email_agent.py      # Email generation, SMTP send, IMAP reply check
│   ├── scheduler.py        # Lead qualification + Calendly scheduling
│   └── billing.py          # Stripe invoice creation & payment polling
└── .agents/
    └── skills/
        └── saleshermes/
            └── SKILL.md    # Hermes skill manifest (auto-loaded by Hermes)
```

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.9+
- A Gmail account with 2FA enabled (for App Password)
- An NVIDIA NIM API key ([cloud.nvidia.com](https://cloud.nvidia.com))
- A Stripe account (test or live)
- A Calendly account with a public booking link

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
# NVIDIA Nemotron — the agent brain
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Gmail SMTP/IMAP — outreach + reply monitoring
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password   # myaccount.google.com/apppasswords

# Scheduling
CALENDLY_LINK=https://calendly.com/yourname/15min
CALENDLY_API_KEY=your_calendly_api_key

# Billing
STRIPE_SECRET_KEY=sk_test_...

# Identity
SENDER_NAME=Your Name
COMPANY_NAME=Your Company Name
```

> **Gmail App Password**: Enable 2FA at [myaccount.google.com](https://myaccount.google.com), then generate an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Use that as `SMTP_PASSWORD`.

### 3. Prepare Leads

Create `data/leads.csv`:

```csv
company,contact,email,website,status,notes
Notion,John,john@notion.so,notion.so,new,
Linear,Sara,sara@linear.app,linear.app,new,Interested in automation
```

### 4. Prepare Services (Stripe billing menu)

Create `data/services.csv`:

```csv
id,name,amount_cents,description
1,Discovery Call,0,Free 15-min intro call
2,Consulting Session,200000,2-hour deep-dive consulting ($2000)
3,Retainer,500000,Monthly retainer ($5000)
```

---

## ▶️ Running the Agent

```bash
python scripts/main.py
```

The agent runs in a **15-minute loop**. Each cycle:
1. Nemotron loads all leads
2. Processes every lead based on its current status
3. Prints `CYCLE COMPLETE`
4. Sleeps 15 minutes, then repeats

**Sample console output:**

```
############################################################
  CYCLE 1 — 2026-06-30 00:45:12
############################################################

  [TOOL] load_leads()
  [TOOL] research_company(lead_email='john@notion.so')
  [TOOL] generate_email(lead_email='john@notion.so', research_summary='Notion is...')
  [TOOL] send_email(to='john@notion.so', subject='Quick question about Notion's docs')
  [TOOL] mark_lead_status(lead_email='john@notion.so', new_status='emailed')

[AGENT] CYCLE COMPLETE

--- FINAL STATUS ---
  Notion       | emailed
  Linear       | emailed

[LOOP] Next cycle at 01:00:12 (15 min). Press Ctrl+C to stop.
```

Press `Ctrl+C` to stop the loop.

---

## 🏆 Hackathon Fit

AutoCloser was built specifically for the **Hermes Agent Accelerated Business Hackathon**. It demonstrates:

- **Agents that earn**: Nemotron drives outreach; Stripe closes the financial loop — real invoices, real payments.
- **Agents that run real operations**: Full B2B sales cycle (research → outreach → qualification → scheduling → billing) runs autonomously.
- **Agents at scale**: Stateless pipeline via CSV means you can drop in 1000 leads and walk away.
- **Hermes Skill architecture**: AutoCloser is packaged as a proper Hermes skill (`.agents/skills/saleshermes/SKILL.md`), making it composable with other Hermes agents and skills.

---

## 🐛 Common Issues

| Symptom | Fix |
|---|---|
| `SMTP auth failed` | Use a Gmail App Password, not your account password. Enable 2FA first. |
| `Playwright returns empty text` | Run `python -m playwright install chromium`. For bot-protected sites, add a `wait_for_timeout`. |
| `Nemotron returns empty email` | Check `NVIDIA_BASE_URL` and confirm the model ID matches your NIM endpoint. |
| `check_replies() finds nothing` | Enable IMAP in Gmail Settings → Forwarding and POP/IMAP. |
| `Stripe: No such customer` | `billing.py` searches by email first; ensure email casing is consistent in CSV. |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `openai` | ≥ 1.0.0 | OpenAI-compatible client for Nemotron tool-calling API |
| `python-dotenv` | ≥ 1.0.0 | Load credentials from `.env` |
| `playwright` | ≥ 1.40.0 | Headless browser for company website scraping |
| `stripe` | ≥ 7.0.0 | Stripe invoice creation and payment status polling |
| `requests` | ≥ 2.31.0 | HTTP client (Calendly API, etc.) |

---

## License

MIT License
