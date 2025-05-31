# agents/prospect_scout.py
import os, json
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

# 1) load credentials & config
load_dotenv(dotenv_path=".env")
hs = HubSpot(access_token=os.getenv("HUBSPOT_TOKEN"))
config = json.load(open("config/icp.json"))

def upsert_contact(email, first, last, title, company):
    props = {
        "email": email,
        "firstname": first,
        "lastname": last,
        "jobtitle": title,
        "company": company,
        "fit_score": "0"
    }
    obj = SimplePublicObjectInput(properties=props)
    hs.crm.contacts.basic_api.create(
        simple_public_object_input_for_create=obj
    )
    print(f"✔ Created contact: {email}")

def main():
    for company in config["companySignals"]:
        # derive a fake email
        domain = company.replace(" ", "").lower() + ".com"
        email = f"info@{domain}"
        parts = company.split()
        first, last = parts[0], parts[-1]
        # pick first title from config
        title = config["contactTitles"][0]
        upsert_contact(email, first, last, title, company)

if __name__ == "__main__":
    main()