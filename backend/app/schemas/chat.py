from pydantic import BaseModel, Field
from typing import Optional, List


class MessageSchema(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=32_000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32_000)
    session_id: str = Field(default="default", max_length=120)
    task_type: Optional[str] = Field(default=None, max_length=50)
    auto_route: bool = True
    force_provider: Optional[str] = Field(default=None, max_length=50)
    force_model: Optional[str] = Field(default=None, max_length=100)
    history: List[MessageSchema] = Field(default_factory=list, max_length=100)


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str
    task_type: str
    tokens_used: int = 0
    demo: bool = False
    session_id: str
