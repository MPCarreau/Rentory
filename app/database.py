import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL in .env")
    return psycopg.connect(url)
