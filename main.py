from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import crud
from models import Meeting
from dotenv import load_dotenv
import json
import re

# Load environment variables from .env
load_dotenv()

# Setup FastAPI app
app = FastAPI(title="Meeting Minutes Agent")

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ OPENAI_API_KEY not set. Please configure it in Render/Deta environment.")
client = OpenAI(api_key=api_key)


@app.get("/")   # ✅ root route
def home():
    return {"message": "Meeting Minutes Agent is running 🚀"}


@app.post("/summarize")
async def summarize_meeting(file: UploadFile = File(...)):
    try:
        text = (await file.read()).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File error: {str(e)}")

    # Build prompt for OpenAI
    prompt = f"""
    You are a Meeting Minutes Agent.
    Summarize the transcript and return ONLY valid JSON.
    Schema:

    {{
      "summary": "string",
      "decisions": ["string"],
      "action_items": [
        {{"task": "string", "owner": "string", "due": "string"}}
      ]
    }}

    Transcript:
    {text}
    """

    # 🔹 Try OpenAI first
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()

        # Try parsing JSON
        parsed = json.loads(content)

        # Validate against Pydantic model
        meeting = Meeting(**parsed)

        # Save to DB
        crud.save_meeting(meeting)

        return meeting.model_dump()

    except Exception as e:
        print("⚠️ OpenAI failed, using fallback:", str(e))

        # ---- Simple regex-based fallback ----
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        decisions = re.findall(r"Decision:\s*(.+)", text, re.IGNORECASE)
        action_items = []
        ai_block = re.search(r"Action Items:(.*)", text, flags=re.IGNORECASE | re.DOTALL)

        if ai_block:
            for line in ai_block.group(1).splitlines():
                m = re.match(r"\d+\.\s*(.+?)\s*-\s*(.+?)\s*-\s*Due:\s*(.+)", line)
                if m:
                    owner, task, due = m.groups()
                    action_items.append({
                        "task": task.strip(),
                        "owner": owner.strip(),
                        "due": due.strip()
                    })

        # Build fallback summary
        summary_lines = [
            ln for ln in lines
            if any(word in ln.lower() for word in ["update", "ready", "complete", "issue", "decide", "decision"])
        ]
        summary = " ".join(summary_lines[:3]) or "Meeting transcript processed, but no summary extracted."

        return {
            "summary": summary,
            "decisions": decisions,
            "action_items": action_items
        }
