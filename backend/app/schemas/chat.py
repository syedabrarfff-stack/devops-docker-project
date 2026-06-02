from pydantic import BaseModel, Field
from typing import Optional, List


class MessageSchema(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    task_type: Optional[str] = None
    auto_route: bool = True
    force_provider: Optional[str] = None
    force_model: Optional[str] = None
    history: List[MessageSchema] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str
    task_type: str
    tokens_used: int = 0
    demo: bool = False
    session_id: str
