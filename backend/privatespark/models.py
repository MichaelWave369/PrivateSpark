from pydantic import BaseModel, Field


class PullRequest(BaseModel):
    model: str = Field(min_length=1)


class MessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    project_id: int
    model: str | None = None
    messages: list[MessageIn]
    temperature: float = 0.2
    system_prompt: str | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WipeRequest(BaseModel):
    confirm_token: str
