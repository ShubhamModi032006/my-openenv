from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class Email(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    timestamp: str

class Observation(BaseModel):
    current_email: Optional[Email] = Field(None, description="The email currently being triaged")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="History of past processed emails")
    steps_taken: int = Field(0, description="Steps taken in this episode")
    remaining_emails: int = Field(..., description="Number of emails left")
    emails_processed: int = Field(0, description="Emails processed in this episode")
    task_description: str = Field(..., description="Instructions for the current task")

class Action(BaseModel):
    priority: Optional[str] = Field(None, description="Priority classification: 'high', 'medium', 'low'")
    department: Optional[str] = Field(None, description="Department assignment: 'support', 'sales', 'hr'")
    reply_draft: Optional[str] = Field(None, description="Draft reply text")
    final_action: Optional[str] = Field(None, description="Final action: 'archive' or 'escalate'")

class Reward(BaseModel):
    score: float = Field(..., description="The reward score for the current step (0.0 to 1.0)")
    message: str = Field(..., description="Explanation of the reward")
