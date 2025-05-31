#!/usr/bin/env python3
"""Poll Cloudflare KV for open:/click: keys and alert Slack."""

import os, time, json, requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT   = os.getenv("CF_ACCOUNT_ID")
NS_ID     = os.getenv("CF_KV_NS")
TOKEN     = os.getenv("CF_API_TOKEN")
SLACK_URL = os.getenv("SLACK_WEBHOOK")
INTERVAL  = 60   # seconds between polls

HEAD = {"Authorization": f"Bearer {TOKEN}"}

def slack(msg: str):
    if SLACK_URL:
        requests.post(SLACK_URL, json={"text": msg})

def list_keys(prefix: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/storage/kv/namespaces/{NS_ID}/keys"
    r = requests.get(url, params={"prefix": prefix, "limit": 100}, headers=HEAD, timeout=10)
    r.raise_for_status()
    return [k["name"] for k in r.json()["result"]]

def delete_key(key: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/storage/kv/namespaces/{NS_ID}/values/{key}"
    requests.delete(url, headers=HEAD, timeout=10)

def handle_event(key: str):
    _, ts, cid = key.split(":")        # open:17485…:134368…
    emoji = "👀" if key.startswith("open:") else "🔗"
    msg   = f"{emoji} {key.split(':')[0].title()} by CID {cid}"
    slack(msg)
    print(msg) 
    delete_key(key)

if __name__ == "__main__":
    print("Open/Click watcher started …")
    while True:
        try:
            for ev_prefix in ("open:", "click:"):
                for k in list_keys(ev_prefix):
                    handle_event(k)
            print("✓ poll", time.strftime("%H:%M:%S"))
        except Exception as e:
            print("⚠️  watcher error:", e)
            slack(f"⚠️ watcher error: {e}")
        time.sleep(INTERVAL)