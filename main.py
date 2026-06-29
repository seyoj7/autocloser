import os
import sys
import json
import time
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import csv_reader, research, email_agent, scheduler, billing

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "leads.csv")
SERVICES_PATH = os.path.join(os.path.dirname(__file__), "data", "services.csv")

# Nemotron client for agent reasoning
client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("NVIDIA_BASE_URL"),
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"

# ── Agent state ──────────────────────────────────────────────
_leads_cache = []


def _get_lead(email: str) -> dict:
    for lead in _leads_cache:
        if lead["email"] == email:
            return lead
    return {}


# ── System prompt ────────────────────────────────────────────
SYSTEM_PROMPT = """You are AutoCloser, an autonomous Hermes B2B sales agent powered by NVIDIA Nemotron.
You manage a pipeline of leads through these stages:

  new → emailed → followup_sent → meeting_sent → meeting_booked → meeting_completed → invoiced → closed_won
  (leads can also be "not_interested" but may recover if they reply later)

WORKFLOW — process each lead based on its current status:

STATUS "new":
  1. research_company(lead_email) → get intel
  2. generate_email(lead_email, research_summary) → write cold email
  3. send_email(to, subject, body) → send it
  4. mark_lead_status(lead_email, "emailed")

STATUS "emailed":
  1. check_replies(lead_email)
  2. If replies found → analyze_reply(reply_body)
     - "interested" → schedule_meeting(lead_email) → mark_lead_status(lead_email, "meeting_sent")
     - "needs_more_info" → generate_followup(lead_email, reply_body) → send_email(to, subject, body) → mark_lead_status(lead_email, "followup_sent")
     - "not_interested"/"unsubscribe" → mark_lead_status(lead_email, "not_interested")
  3. If no replies → skip, check next cycle

STATUS "followup_sent":
  1. check_replies(lead_email)
  2. If replies → analyze_reply → qualify_lead → if qualified, schedule_meeting + mark "meeting_sent"; else mark "not_interested"
  3. If no replies → skip

STATUS "meeting_sent":
  1. check_replies(lead_email)
  2. If replies → mark_lead_status(lead_email, "meeting_booked")
  3. If no replies → skip

STATUS "meeting_booked":
  1. confirm_meeting(lead_email) — asks the human operator
  2. If confirmed → mark_lead_status(lead_email, "meeting_completed") → create_invoice(lead_email)
  3. If not → skip, check next cycle

STATUS "meeting_completed":
  1. create_invoice(lead_email)

STATUS "invoiced":
  1. check_payment_status(lead_email)
  2. If "paid" → mark_lead_status(lead_email, "closed_won")

STATUS "closed_won": skip

STATUS "not_interested":
  1. check_replies(lead_email) for change of heart
  2. If reply → analyze + qualify → if qualified, schedule_meeting + mark "meeting_sent"

INSTRUCTIONS:
- Start by calling load_leads
- Process leads ONE AT A TIME, in order
- Use results from previous tools (e.g., pass research summary to generate_email)
- After ALL leads are processed, respond with text "CYCLE COMPLETE" and no tool calls
- Do NOT skip any lead — process every one based on its status
"""

# ── Tool definitions ─────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "load_leads",
            "description": "Load all leads from CSV with their current pipeline status. Call this first at the start of every cycle.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "research_company",
            "description": "Scrape a lead's company website and summarize with AI for sales intel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"}
                },
                "required": ["lead_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_email",
            "description": "Generate a personalized cold B2B email for a lead using research intel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"},
                    "research_summary": {"type": "string", "description": "Research summary from research_company"}
                },
                "required": ["lead_email", "research_summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_followup",
            "description": "Generate a follow-up email answering a lead's question or concern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"},
                    "reply_body": {"type": "string", "description": "The lead's reply text to respond to"}
                },
                "required": ["lead_email", "reply_body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email via Gmail SMTP. Automatically threads with existing conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_lead_status",
            "description": "Update a lead's pipeline status in the CSV file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"},
                    "new_status": {
                        "type": "string",
                        "description": "New pipeline status",
                        "enum": ["emailed", "followup_sent", "meeting_sent", "meeting_booked", "meeting_completed", "invoiced", "closed_won", "not_interested"]
                    }
                },
                "required": ["lead_email", "new_status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_replies",
            "description": "Check Gmail inbox for replies from a specific lead. Returns list of replies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email to check replies for"}
                },
                "required": ["lead_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_reply",
            "description": "Classify a lead's email reply into: interested, not_interested, needs_more_info, or unsubscribe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply_body": {"type": "string", "description": "The text of the lead's reply email"}
                },
                "required": ["reply_body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "qualify_lead",
            "description": "Determine if a lead is qualified to pursue based on their reply analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"},
                    "reply_analysis": {"type": "string", "description": "Classification from analyze_reply"}
                },
                "required": ["lead_email", "reply_analysis"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_meeting",
            "description": "Send a Calendly booking link to a qualified lead via email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"}
                },
                "required": ["lead_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_meeting",
            "description": "Ask the human operator if a meeting with a lead has been completed. Returns whether the meeting is done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"}
                },
                "required": ["lead_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_invoice",
            "description": "Show service menu, let operator pick a service, then create and send a Stripe invoice to the lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"}
                },
                "required": ["lead_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_payment_status",
            "description": "Check Stripe payment status for a lead's latest invoice. Returns: paid, open, void, draft, uncollectible, or unknown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_email": {"type": "string", "description": "The lead's email address"}
                },
                "required": ["lead_email"]
            }
        }
    },
]


# ── Tool executor ────────────────────────────────────────────
def execute_tool(name: str, args: dict) -> str:
    global _leads_cache

    print(f"\n  🔧 {name}({', '.join(f'{k}={repr(v)[:60]}' for k, v in args.items())})")

    try:
        # ── load_leads ──
        if name == "load_leads":
            _leads_cache = csv_reader.load_leads(DATA_PATH)
            summary = [
                {"company": l["company"], "contact": l["contact"],
                 "email": l["email"], "website": l.get("website", ""),
                 "notes": l.get("notes", ""), "status": l["status"]}
                for l in _leads_cache
            ]
            return json.dumps(summary)

        # ── research_company ──
        elif name == "research_company":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            summary = research.research_company(
                lead.get("website", ""), lead["company"], lead.get("notes", "")
            )
            return json.dumps({"summary": summary})

        # ── generate_email ──
        elif name == "generate_email":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            email_dict = email_agent.generate_email(lead, args["research_summary"])
            return json.dumps(email_dict)

        # ── generate_followup ──
        elif name == "generate_followup":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            followup = email_agent.generate_followup(lead, args["reply_body"])
            return json.dumps(followup)

        # ── send_email ──
        elif name == "send_email":
            success = email_agent.send_email(args["to"], args["subject"], args["body"])
            return json.dumps({"sent": success})

        # ── mark_lead_status ──
        elif name == "mark_lead_status":
            success = csv_reader.mark_lead_status(DATA_PATH, args["lead_email"], args["new_status"])
            for lead in _leads_cache:
                if lead["email"] == args["lead_email"]:
                    lead["status"] = args["new_status"]
            return json.dumps({"updated": success, "new_status": args["new_status"]})

        # ── check_replies ──
        elif name == "check_replies":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            replies = email_agent.check_replies([lead])
            return json.dumps({"replies": replies or [], "count": len(replies)})

        # ── analyze_reply ──
        elif name == "analyze_reply":
            classification = email_agent.analyze_reply(args["reply_body"])
            return json.dumps({"classification": classification})

        # ── qualify_lead ──
        elif name == "qualify_lead":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            qualified = scheduler.qualify_lead(lead, args["reply_analysis"])
            return json.dumps({"qualified": qualified})

        # ── schedule_meeting ──
        elif name == "schedule_meeting":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            result = scheduler.schedule_meeting(lead)
            return json.dumps({"result": result})

        # ── confirm_meeting (human-in-the-loop) ──
        elif name == "confirm_meeting":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})
            done = input(
                f"  Has the meeting with {lead['contact']} at {lead['company']} been completed? (y/n): "
            ).strip().lower()
            return json.dumps({"completed": done == "y"})

        # ── create_invoice (human-in-the-loop service picker) ──
        elif name == "create_invoice":
            lead = _get_lead(args["lead_email"])
            if not lead:
                return json.dumps({"error": f"Lead not found: {args['lead_email']}"})

            confirm = input(
                f"  Create & send Stripe invoice to {lead['contact']} at {lead['company']}? (y/n): "
            ).strip().lower()
            if confirm != "y":
                return json.dumps({"invoiced": False, "skipped": True})

            services = csv_reader.load_services(SERVICES_PATH)
            if not services:
                return json.dumps({"error": "No services in data/services.csv"})

            print(f"\n  Available services:")
            for s in services:
                print(f"    [{s['id']}] {s['name']:25s}  ${s['amount_cents'] / 100:.2f}  —  {s['description']}")

            choice = input(f"  Select service ID to invoice [default=2]: ").strip() or "2"
            service = next((s for s in services if s["id"] == choice), services[0])
            invoice_url = billing.create_invoice(lead, service["amount_cents"], service["description"])

            if invoice_url:
                csv_reader.mark_lead_status(DATA_PATH, lead["email"], "invoiced")
                for l in _leads_cache:
                    if l["email"] == lead["email"]:
                        l["status"] = "invoiced"
                return json.dumps({"invoice_url": invoice_url, "invoiced": True})
            else:
                return json.dumps({"error": "Invoice creation failed", "invoiced": False})

        # ── check_payment_status ──
        elif name == "check_payment_status":
            status = billing.check_payment_status(args["lead_email"])
            return json.dumps({"payment_status": status})

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        print(f"  ❌ Tool error: {e}")
        return json.dumps({"error": str(e)})


# ── Agent cycle ──────────────────────────────────────────────
def run_agent_cycle():
    print("=" * 60)
    print("  AutoCloser — Hermes Agent Cycle")
    print("=" * 60)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Start a new pipeline cycle. Load leads and process each one based on their current status."},
    ]

    MAX_STEPS = 100
    step = 0

    while step < MAX_STEPS:
        step += 1

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=1024,
                timeout=60,
            )
        except Exception as e:
            print(f"\n[AGENT] ❌ Nemotron API error: {e}")
            break

        choice = response.choices[0]
        msg = choice.message

        # Add assistant message to history
        messages.append(msg)

        # If no tool calls → agent is done
        if choice.finish_reason == "stop" or not msg.tool_calls:
            if msg.content:
                print(f"\n[AGENT] {msg.content}")
            break

        # Execute each tool call
        for tc in msg.tool_calls:
            fn_args = json.loads(tc.function.arguments)
            result = execute_tool(tc.function.name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    if step >= MAX_STEPS:
        print(f"\n[AGENT] ⚠️ Hit max steps ({MAX_STEPS}), ending cycle.")

    # Final status
    print("\n--- FINAL STATUS ---")
    leads = csv_reader.load_leads(DATA_PATH)
    for lead in leads:
        print(f"  {lead['company']:12s} | {lead['status']}")

    print("\n" + "=" * 60)
    print("[OK] Agent cycle complete!")
    print("=" * 60)


# ── Main loop (15-min interval) ──────────────────────────────
if __name__ == "__main__":
    INTERVAL = 15 * 60  # 15 minutes

    cycle = 1
    try:
        while True:
            print(f"\n{'#' * 60}")
            print(f"  CYCLE {cycle} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'#' * 60}")

            run_agent_cycle()

            cycle += 1
            next_run = datetime.now() + timedelta(seconds=INTERVAL)
            print(f"\n[LOOP] Next cycle at {next_run.strftime('%H:%M:%S')} (15 min). Press Ctrl+C to stop.")
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n[LOOP] Stopped after {cycle - 1} cycle(s). Goodbye!")
