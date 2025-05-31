import os
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException

# 1. load env
load_dotenv()

# 2. init client
token = os.getenv("HUBSPOT_TOKEN")
if not token:
    raise RuntimeError("HUBSPOT_TOKEN not in .env")
hs = HubSpot(access_token=token)

# 3. fetch up to 5 contacts
try:
    resp = hs.crm.contacts.basic_api.get_page(limit=5)
    print(f"✅ Retrieved {len(resp.results)} contacts:")
    for c in resp.results:
        props = c.properties
        print(f" • {props.get('firstname','(no first)')} {props.get('lastname','')}  –  {props.get('email')}")
except ApiException as e:
    print("❌ HubSpot API error:", e)