import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Explicitly load the .env in this directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Loading env file from: {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# 2. Confirm .env variables are present
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("❌ DATABASE_URL not found in env")

print("✅ DATABASE_URL loaded:", db_url)

# 3. Test DB connection
engine = create_engine(db_url)
with engine.begin() as conn:
    # simple read to test connectivity
    result = conn.execute(text("SELECT version();")).scalar_one()
    print("✅ Connected to Postgres version:", result)