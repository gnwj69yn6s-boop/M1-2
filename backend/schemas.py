
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExerciseBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date: date
    value: float = Field(ge=0, le=1440, description="운동 시간(분)")
    exercise_type: str = Field(default="기타", min_length=1, max_length=50)
    calories: float = Field(default=0, ge=0, le=50000)
    memo: str = Field(default="", max_length=1000)

    @field_validator("exercise_type")
    @classmethod
    def validate_exercise_type(cls, value: str) -> str:
        if not value:
            raise ValueError("운동 종류를 입력해 주세요.")
        return value


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(ExerciseBase):
    pass


class ExerciseOut(ExerciseBase):
    id: str


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ConversationCreate(BaseModel):
    title: str = Field(default="새 대화", max_length=200)
    messages: list[Message] = Field(default_factory=list, max_length=200)


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[Message] = Field(default_factory=list)
