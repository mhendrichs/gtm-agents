#!/usr/bin/env python3
"""
Send follow-up emails:
  • D+3  → prompts/followup_1.md
  • D+7  → prompts/followup_2.md
"""

import os, time, json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException

from sequencer import send_email, stamp_last_emailed      # helpers you already have
from copy_crafter import draft_email, split_subject

load_dotenv()
hs = HubSpot(access_token=os.getenv("HUBSPOT_TOKEN"))

STEPS = [
    (3, "followup_1.md"),
    (7, "followup_2.md"),
]

def cutoff_date(days: int) -> str:
    """YYYY-MM-DD in UTC for 'days' ago."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

def search_contacts(days: int):
    """HubSpot sometimes rejects date EQ; fall back to paginated get_page."""
    date_str = cutoff_date(days)

    # 1️⃣ try Search API with plain dict
    body = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "last_emailed",
                        "operator": "EQ",
                        "value": date_str,
                    }
                ]
            }
        ],
        "properties": ["email", "firstname", "jobtitle", "company", "fit_score"],
        "limit": 100,
    }

    try:
        res = hs.crm.contacts.search_api.do_search(body)
        return res.results
    except ApiException as e:
        if e.status != 400:
            raise
        print("⚠️  HubSpot search 400 – falling back to paginated get_page")

    # 2️⃣ fallback: pull pages of 100 until exhausted
    all_results = []
    after = None
    while True:
        page = hs.crm.contacts.basic_api.get_page(
            limit=100,
            after=after,
            properties=[
                "email", "firstname", "jobtitle",
                "company", "fit_score", "last_emailed"
            ],
        )
        all_results.extend(page.results)

        next_page = getattr(page.paging, "next", None)
        if next_page and next_page.after:
            after = next_page.after
        else:
            break

    # 3️⃣ filter to target date
    return [
        c for c in all_results
        if c.properties.get("last_emailed") == date_str
    ]

def main():
    for days, tmpl in STEPS:
        contacts = search_contacts(days)
        print(f"🛈 {len(contacts)} contacts due for day +{days}")

        for c in contacts:
            email = c.properties.get("email")
            if not email:
                continue

            raw  = draft_email(c.properties, template=tmpl)   # full text from GPT
            subject, body = split_subject(raw)                # strip Subject: line
            send_email(email, body, subject_hint=subject) 
            stamp_last_emailed(c.id)
            time.sleep(2)

if __name__ == "__main__":
    main()