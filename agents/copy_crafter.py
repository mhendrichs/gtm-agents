"""Generate email copy (first-touch or follow-ups) for HubSpot contacts.

Features
• Accepts a template filename, defaulting to first_touch_email.md
• Cleans any sender-name placeholders thoroughly
• Guarantees exactly one tracked Calendly link
• Appends an invisible tracking-pixel
"""

import os, json, random, re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException

# ── env & clients ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent           # project root
load_dotenv(ROOT / ".env")

SENDER_NAME    = os.getenv("SENDER_NAME", "Matthias")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai = OpenAI(api_key=OPENAI_API_KEY)
hs     = HubSpot(access_token=os.getenv("HUBSPOT_TOKEN"))

PROMPT_DIR = ROOT / "prompts"          # e.g. prompts/first_touch_email.md
WORKER_URL = "https://tracker.matthias-hendrichs.workers.dev"

# ── helper -------------------------------------------------------
def split_subject(body: str) -> tuple[str, str]:
    """
    If the first line starts 'Subject:', return (subject, rest_of_body).
    Otherwise return ('', original_body).
    """
    if body.lower().startswith("subject:"):
        first, *rest = body.splitlines()
        # strip leading 'Subject:' and any spaces
        subj = first.partition(":")[2].strip()
        return subj, "\n".join(rest).lstrip()
    return "", body


def draft_email(props: dict, template: str = "first_touch_email.md") -> str:
    """
    Build prompt, call OpenAI, clean placeholders, guarantee ONE Calendly
    link, append pixel, return the finished body (plain-text + HTML img tag).
    """
    # 1) build prompt & call OpenAI --------------------------------
    prompt_raw = (PROMPT_DIR / template).read_text(encoding="utf-8")
    prompt = prompt_raw.format(
        first_name  = props.get("firstname", "there"),
        job_title   = props.get("jobtitle",  ""),
        company     = props.get("company",   "your firm"),
        sender_name = SENDER_NAME,
        desk_type   = random.choice(["Asia Macro", "China Research"]),
    )
    
    MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-0125")

    resp  = openai.chat.completions.create(
        model       = MODEL,
        messages    = [{"role": "user", "content": prompt}],
        temperature = 0.7,
        max_tokens  = 180,
    )
    body: str = resp.choices[0].message.content.strip()

    subject, body = split_subject(body)

    # 2) nuke any sender-name placeholders -------------------------
    body = re.sub(
        r"(?:\{|\[|\()(?:\s*sender[\s_]*name|\s*your[\s_]*name)(?:\s*)(?:\}|\]|\))",
        SENDER_NAME,
        body,
        flags=re.I,
    ).replace("\\1", "")      # remove stray back-refs if any

    # 3) guarantee one Calendly link -------------------------------
    cid        = props.get("hs_object_id") or "unknown"
    link_plain = f"{WORKER_URL}/c/{cid}"

    if "{cal}" in body:                       # token survived
        body = body.replace("{cal}", link_plain)
    if link_plain not in body:                # token gone → append CTA
        body += f"\n\nSchedule a quick chat: {link_plain}"

    # 4) append 1×1 tracking pixel ---------------------------------
    pixel = (
        f'<img src="{WORKER_URL}/p.gif?cid={cid}" '
        f'width="1" height="1" style="display:none;" />'
    )
    body += "\n\n" + pixel

    return body

# ── demo run (top-3 contacts) ------------------------------------

def main():
    try:
        page = hs.crm.contacts.basic_api.get_page(
            limit=100,
            properties=["email", "firstname", "lastname",
                        "jobtitle", "company", "fit_score"],
        )
    except ApiException as e:
        print("❌ HubSpot API error:", e)
        return

    contacts = sorted(
        page.results,
        key=lambda c: int(c.properties.get("fit_score") or 0),
        reverse=True,
    )[:3]

    for c in contacts:
        body = draft_email(c.properties)          # default first-touch
        print("---\nTo:", c.properties.get("email"))
        print(body)
        print()

if __name__ == "__main__":
    main()