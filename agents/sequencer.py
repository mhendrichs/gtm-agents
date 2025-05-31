# agents/sequencer.py
"""Send first-touch emails to the top-scored HubSpot contacts and stamp
`last_emailed` (custom date property) so follow-ups know when to trigger.

✦  Uses the same `draft_email()` helper from copy_crafter.py to keep copy logic in one place.
✦  Reads SMTP + HubSpot creds from .env.
✦  Sorts locally by `fit_score` because the HubSpot SDK no longer supports `sorts=`.
✦  Random 1.5–2.5 s pause between sends to stay under Gmail/Mailgun limits.
✦  Marks each contact’s `last_emailed` property to today’s UTC date (YYYY-MM-DD).
"""


from __future__ import annotations

import os
import ssl
import smtplib
import time
import random
import html
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
import importlib.util, sys

from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException, SimplePublicObjectInput

# ── project paths & env ───────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # project root
load_dotenv(ROOT / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

if not (SMTP_USER and SMTP_PASS):
    raise RuntimeError("SMTP_USER / SMTP_PASS not set in .env")

# ── HubSpot client ────────────────────────────────────────────────
hs = HubSpot(access_token=os.getenv("HUBSPOT_TOKEN"))

# ── import draft_email from copy_crafter.py -----------------------
spec = importlib.util.spec_from_file_location(
    "copy_crafter", ROOT / "agents" / "copy_crafter.py"
)
copy_crafter = importlib.util.module_from_spec(spec)  # type: ignore
sys.modules[spec.name] = copy_crafter  # type: ignore
spec.loader.exec_module(copy_crafter)  # type: ignore

draft_email = copy_crafter.draft_email  # type: ignore

# ── helpers -------------------------------------------------------

def send_email(to_addr: str, body_plain: str, subject_hint: str = "") -> None:
    """Send HTML + plain-text email via SSL SMTP."""
    # Split off pixel (if present)
    if "<img" in body_plain:
        txt_part, pixel = body_plain.rsplit("\n\n", 1)
    else:
        txt_part, pixel = body_plain, ""

    # 1️⃣  Detect tracker URL in the *raw* plain-text
    url_match = re.search(r"https://tracker[^\s]+/c/\d+", txt_part)
    if url_match:
        url = url_match.group(0)
        anchor_html = f'<a href="{url}">here is a link to my calendar</a>'
        # keep plain-text unchanged; swap only in HTML later
    else:
        url = anchor_html = None

    # 2️⃣  Build HTML from txt_part *after* escaping
    html_body = (
        "<p>"
        + html.escape(txt_part)
              .replace("\n\n", "</p><p>")
              .replace("\n", "<br>")
        + "</p>"
    )

    # 3️⃣  Insert friendly anchor (if we found a URL)
    if url:
        html_body = html_body.replace(html.escape(url), anchor_html)

    # 4️⃣  Append pixel (no leading newlines)
    if pixel:
        html_body += pixel.lstrip("\n")

    # assemble multipart email
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject_hint or "Quick idea on policy-driven alpha"
    msg.set_content(txt_part)                   # text/plain
    msg.add_alternative(html_body, subtype="html")  # text/html

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(f"✉️  Sent to {to_addr}")


def stamp_last_emailed(contact_id: str):
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    obj = SimplePublicObjectInput(
        properties={
            "last_emailed": datetime.now(timezone.utc).strftime("%Y-%m-%d"),  # keep date
            "last_emailed_at": str(now_ms),                                   # new datetime
        }
    )
    hs.crm.contacts.basic_api.update(contact_id, simple_public_object_input=obj)

# ── main ----------------------------------------------------------

def main() -> None:
    try:
        page = hs.crm.contacts.basic_api.get_page(
            limit=100,
            properties=[
                "email",
                "firstname",
                "lastname",
                "jobtitle",
                "company",
                "fit_score",
                "last_emailed",
            ],
        )
    except ApiException as e:
        print("❌ HubSpot API error:", e)
        return

    # sort contacts locally by fit_score desc and pick top-5
    leads = sorted(
        page.results,
        key=lambda c: int(c.properties.get("fit_score") or 0),
        reverse=True,
    )[:5]

    for c in leads:
        email = c.properties.get("email")
        if not email:
            continue

        body = draft_email(c.properties, template=tmpl)
        send_email(email, body)
        stamp_last_emailed(c.id)
        time.sleep(random.uniform(1.5, 2.5))  # gentle throttling


if __name__ == "__main__":
    main()
