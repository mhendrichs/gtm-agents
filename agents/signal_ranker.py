import os
import json
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException, SimplePublicObjectInput

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Initialize HubSpot client
hs = HubSpot(access_token=os.getenv("HUBSPOT_TOKEN"))

# Load ICP configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'icp.json')
with open(config_path) as f:
    config = json.load(f)
signals = [s.lower().replace(" ", "") for s in config["companySignals"]]


def update_score(contact_id: str, score: int):
    """
    Update the HubSpot contact's fit_score property.
    """
    props = {"fit_score": str(score)}
    obj = SimplePublicObjectInput(properties=props)
    try:
        hs.crm.contacts.basic_api.update(
            contact_id,
            simple_public_object_input=obj
        )
        print(f"✔ Updated contact {contact_id} → score {score}")
    except ApiException as e:
        print(f"❌ Failed to update {contact_id}: {e}")


def main():
    """
    Fetch contacts from HubSpot and assign fit_score based on email domain matching.
    """
    try:
        page = hs.crm.contacts.basic_api.get_page(limit=100)
    except ApiException as e:
        print(f"❌ Failed to fetch contacts: {e}")
        return

    for c in page.results:
        props = c.properties
        email = props.get("email", "").lower()
        domain = email.split("@")[-1] if "@" in email else ""

        # Determine score by matching domain against signals
        score = 0
        for idx, sig in enumerate(signals):
            if sig in domain:
                score = 100 - idx * 10
                break

        update_score(c.id, score)


if __name__ == "__main__":
    main()
