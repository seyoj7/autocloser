# AutoCloser - Autonomous B2B Sales Pipeline Agent

> Built for the **Hermes Agent Accelerated Business Hackathon** presented by **NVIDIA**, **Stripe**, and **Nous Research**.

AutoCloser is a **fully autonomous B2B sales pipeline agent** that runs as a [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill. Give it a CSV of leads, and it will:

1. **Research** each company by scraping their website with Playwright
2. **Write** hyper-personalized cold emails using NVIDIA Nemotron
3. **Send** them via Gmail SMTP (with automatic email threading)
4. **Monitor** replies and classify sentiment (interested / needs more info / not interested)
5. **Schedule** meetings by sending Calendly links to warm leads
6. **Invoice** closed deals via Stripe — creating customers, generating invoices, and tracking payment
7. **Repeat** every 15 minutes, 24/7, completely hands-free

**From cold lead → signed deal → paid invoice. Zero manual work.**

---

## 🧠 Why AutoCloser?

Most "AI sales tools" are glorified mail-merge with an LLM wrapper. AutoCloser is different:

| Traditional Tools | AutoCloser |
|---|---|
| Generates emails, human sends them | Generates **and sends** emails autonomously |
| Human reads replies, decides next step | AI classifies replies and acts instantly |
| Human books meetings manually | Auto-sends Calendly links to interested leads |
| Separate invoicing workflow | Creates and sends Stripe invoices in the same pipeline |
| Requires constant babysitting | Runs 24/7 as a Hermes Agent background skill |
| Fixed templates | Dynamic: tone, word count, sender name all configurable via chat |

**AutoCloser is not a tool. It's your entire sales team.**

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Gmail account with [App Password](https://myaccount.google.com/apppasswords) (2FA required)
- [NVIDIA NIM API key](https://build.nvidia.com/) for Nemotron
- [Stripe API key](https://dashboard.stripe.com/apikeys)
- [Calendly](https://calendly.com/) booking link + API key

### Installation

1. **Clone the repository** (or install as a Hermes skill):
```bash
git clone https://github.com/yourusername/AutoCloser.git
cd AutoCloser
```

2. **Configure your environment**:
```bash
cp .env.example .env
```
Fill out `.env` with your API keys, SMTP credentials, and Stripe secrets.

3. **Set up the virtual environment & dependencies**:
```bash
bash scripts/setup.sh
```

4. **Add Leads**:
Populate `data/leads.csv` with your initial prospects:
```csv
company,contact,email,website,status,notes
Notion,Jane,jane@notion.so,notion.so,new,Productivity docs
```

5. **Run the Pipeline**:
To run it interactively (will prompt for meeting completion/invoicing):
```bash
source venv/bin/activate
python3 scripts/main.py
```

To run it autonomously (e.g., inside Hermes Agent):
```bash
source venv/bin/activate
python3 scripts/main.py --no-input
```

To run it exactly once without looping:
```bash
source venv/bin/activate
python3 scripts/main.py --single-cycle --no-input
```

---

## 🛠 Architecture

- **`main.py`**: The central orchestrator. Loops through all leads, checking statuses and advancing the pipeline.
- **`csv_reader.py`**: Handles all state management in the `leads.csv` database.
- **`research.py`**: Scrapes websites with Playwright and extracts actionable intel via Nemotron.
- **`email_agent.py`**: Generates and sends personalized emails, checks IMAP for replies, and classifies sentiment.
- **`scheduler.py`**: Manages the qualification and sending of Calendly links.
- **`billing.py`**: Integrates with Stripe to create customers and send invoices.
- **`cli.py`**: Provides command-line utilities to add, list, and update leads manually.

---

## 🤖 Hermes Agent Integration

AutoCloser is natively designed to be dropped into a Hermes Agent workspace under `.agents/skills/autocloser/`. 

When triggered, Hermes will execute `main.py --no-input` on a schedule, monitoring your inbox, answering questions, booking meetings, and sending invoices completely in the background without getting stuck on interactive prompts.

---

## License

MIT License