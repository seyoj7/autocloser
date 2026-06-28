import os
import re
import random
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Nemotron client
client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("NVIDIA_BASE_URL"),
)
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"


def _human_scroll(page) -> None:
    import time as _time
    _time.sleep(random.uniform(1.0, 2.5))
    
    scroll_bursts = random.randint(3, 5)
    for _ in range(scroll_bursts):
        # A quick burst of small scroll ticks
        scroll_ticks = random.randint(5, 12)
        for _ in range(scroll_ticks):
            page.mouse.wheel(0, random.randint(30, 80))
            _time.sleep(random.uniform(0.01, 0.04))
            
        # Pause to "read" or process the page
        _time.sleep(random.uniform(0.4, 1.0))



def _scrape_website(url: str) -> str:
    from playwright.sync_api import sync_playwright

    if not url.startswith("http"):
        url = "https://" + url

    print(f"[RESEARCH] Scraping {url} ...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
            )
            page = context.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")

            page.wait_for_timeout(random.randint(1500, 3000))

            _human_scroll(page)

            page.wait_for_timeout(random.randint(500, 1000))

            text = page.inner_text("body")
            browser.close()

        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = text.strip()

        if len(text) > 2000:
            text = text[:2000]

        print(f"[RESEARCH] Scraped {len(text)} chars from {url}")
        return text

    except Exception as e:
        print(f"[RESEARCH] Scraping failed for {url}: {e}")
        return ""


def _summarize_with_nemotron(text: str, company: str) -> str:
    prompt = f"""Analyze this company homepage text for "{company}".
    Return a concise 2-3 sentence summary covering:
    1. What the company does
    2. Who their target buyers are
    3. Their main pain point they solve

    Homepage text:
    {text}

    Return ONLY the summary, nothing else."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a B2B sales research analyst. Be concise and specific."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=200,
            timeout=30,
        )
        summary = response.choices[0].message.content.strip()
        print(f"[RESEARCH] Nemotron summary for {company}: {summary[:80]}...")
        return summary

    except Exception as e:
        print(f"[RESEARCH] Nemotron API error: {e}")
        return ""


def research_company(website: str, company: str, notes: str = "") -> str:
    print(f"\n[RESEARCH] Researching {company} ({website})...")

    scraped_text = _scrape_website(website)

    if scraped_text:
        summary = _summarize_with_nemotron(scraped_text, company)
        if summary:
            return summary

    if notes:
        print(f"[RESEARCH] Using notes as fallback for {company}")
        fallback = f"{company}: {notes}"
        enriched = _summarize_with_nemotron(notes, company)
        return enriched if enriched else fallback

    return f"{company}: No research data available."


# Quick self-test
if __name__ == "__main__":
    result = research_company("notion.so", "Notion", "Productivity and docs platform")
    print(f"\nFinal result:\n{result}")
