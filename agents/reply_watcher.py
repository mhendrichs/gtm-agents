#!/usr/bin/env python3
"""
Poll Gmail every 60 s for messages that carry the label gtm/replied.
For each new match:
  • post a Slack alert
  • print to stdout
"""

import imaplib
import email
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = "imap.gmail.com"
USER      = os.getenv("SMTP_USER")
PW        = os.getenv("SMTP_PASS")          # same app-password as SMTP
SLACK_URL = os.getenv("SLACK_WEBHOOK")

def slack(msg: str):
    if SLACK_URL:
        requests.post(SLACK_URL, json={"text": msg})

def fetch_replies():
    """Yield dicts for every unread ‘gtm/replied’ message."""
    with imaplib.IMAP4_SSL(IMAP_HOST) as M:
        M.login(USER, PW)
        # All Mail lets us search by label
        M.select('"[Gmail]/All Mail"')
        typ, data = M.search(
            None,
            'X-GM-LABELS "gtm/replied" UNSEEN'
        )
        for num in data[0].split():
            typ, raw = M.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(raw[0][1])
            frm = email.utils.parseaddr(msg["From"])[1]
            subj = msg["Subject"]
            # mark as seen so we don't alert again
            M.store(num, "+FLAGS", "\\Seen")
            yield {"from": frm, "subject": subj}

if __name__ == "__main__":
    while True:
        new_msgs = list(fetch_replies())

        if new_msgs:
            for m in new_msgs:
                line = f"↩️  Reply from {m['from']} – {m['subject']}"
                print(line)
                slack(f"📬 {line}")
        else:
            print("⏳ No replies yet")

        time.sleep(60)