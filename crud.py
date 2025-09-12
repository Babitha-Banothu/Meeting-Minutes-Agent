# backend/crud.py
import json
import os
from datetime import datetime
from models import Meeting

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def save_meeting(meeting: Meeting):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"meeting_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meeting.model_dump(), f, indent=2)
    return path
