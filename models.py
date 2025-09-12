# backend/models.py
from pydantic import BaseModel
from typing import List, Optional

class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    due: Optional[str] = None

class Meeting(BaseModel):
    summary: str
    decisions: List[str]
    action_items: List[ActionItem]
