import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import text

# If you want real embeddings, uncomment this:
# from utils.embed import get_embedding

load_dotenv()  
db_url = os.getenv("DATABASE_URL")
print("Connecting to:", db_url.split("@")[1])

engine = sqlalchemy.create_engine(db_url)

# Option A — real embedding (requires OpenAI key & network)
# emb = get_embedding("Hello from GTM-agents smoke test")

# Option B — fake embedding for offline PoC
emb = [0.0] * 1536

with engine.begin() as conn:
    conn.execute(text(
        "INSERT INTO agent_memory(role, content, embedding) VALUES (:r, :c, :e)"
    ), {"r": "smoke", "c": "smoke test", "e": emb})
    count = conn.execute(text("SELECT COUNT(*) FROM agent_memory")).scalar_one()

print("✅ Row count now:", count)