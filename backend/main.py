
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore
from google.api_core.exceptions import GoogleAPICallError
from openai import OpenAIError

from schemas import (
    ChatRequest,
    ConversationCreate,
    ExerciseCreate,
    ExerciseUpdate,
)
from services import (
    answer_chat,
    calculate_summary,
    conversation_collection,
    data_collection,
    get_db,
    list_records,
    normalize_record,
    utc_now,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Firebase는 첫 요청에서 초기화해 환경 설정 오류를 명확하게 처리합니다.
    yield


app = FastAPI(
    title="MyData AI - Exercise Assistant",
    description="운동 시계열 데이터 관리 및 AI 분석 API",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    x.strip()
    for x in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if x.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def db_or_503():
    try:
        return get_db()
    except Exception as exc:
        # 자격 증명이나 내부 설정값은 클라이언트에 노출하지 않습니다.
        print(f"Database initialization error: {type(exc).__name__}")
        raise HTTPException(
            status_code=503,
            detail="데이터베이스에 연결할 수 없습니다. 서버 설정을 확인해 주세요.",
        ) from exc


def db_error(exc):
    print(f"Firestore error: {type(exc).__name__}")
    raise HTTPException(status_code=503, detail="데이터베이스 요청에 실패했습니다.")


@app.get("/")
def root():
    return {
        "name": "MyData AI",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------- Exercise data CRUD --------------------

@app.post("/api/data", status_code=201)
def create_data(payload: ExerciseCreate):
    db = db_or_503()
    now = utc_now()
    item = payload.model_dump(mode="json")
    item["created_at"] = now
    item["updated_at"] = now
    try:
        ref = data_collection(db).document()
        ref.set(item)
        return {"id": ref.id, **item}
    except Exception as exc:
        db_error(exc)


@app.get("/api/data")
def get_data(limit: int = 2000):
    if not 1 <= limit <= 5000:
        raise HTTPException(status_code=422, detail="limit은 1~5000이어야 합니다.")
    db = db_or_503()
    try:
        records = list_records(db, limit=limit)
        return {"items": records, "count": len(records)}
    except Exception as exc:
        db_error(exc)


@app.put("/api/data/{record_id}")
def update_data(record_id: str, payload: ExerciseUpdate):
    db = db_or_503()
    ref = data_collection(db).document(record_id)
    try:
        if not ref.get().exists:
            raise HTTPException(status_code=404, detail="운동 기록을 찾을 수 없습니다.")
        item = payload.model_dump(mode="json")
        item["updated_at"] = utc_now()
        ref.update(item)
        return {"id": record_id, **item}
    except HTTPException:
        raise
    except Exception as exc:
        db_error(exc)


@app.delete("/api/data/{record_id}", status_code=204)
def delete_data(record_id: str):
    db = db_or_503()
    ref = data_collection(db).document(record_id)
    try:
        if not ref.get().exists:
            raise HTTPException(status_code=404, detail="운동 기록을 찾을 수 없습니다.")
        ref.delete()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as exc:
        db_error(exc)


@app.get("/api/data/summary")
def get_summary():
    db = db_or_503()
    try:
        records = list_records(db)
        return calculate_summary(records)
    except Exception as exc:
        db_error(exc)


# -------------------- Conversation history --------------------

@app.post("/api/conversations", status_code=201)
def save_conversation(payload: ConversationCreate):
    db = db_or_503()
    now = utc_now()
    item = {
        "title": payload.title,
        "messages": [m.model_dump() for m in payload.messages],
        "created_at": now,
        "updated_at": now,
    }
    try:
        ref = conversation_collection(db).document()
        ref.set(item)
        return {"id": ref.id, **item}
    except Exception as exc:
        db_error(exc)


@app.get("/api/conversations")
def get_conversations():
    db = db_or_503()
    try:
        docs = conversation_collection(db).stream()
        items = []
        for doc in docs:
            row = doc.to_dict()
            items.append({
                "id": doc.id,
                "title": row.get("title", "새 대화"),
                "created_at": row.get("created_at", ""),
                "updated_at": row.get("updated_at", ""),
                "message_count": len(row.get("messages", [])),
            })
        items.sort(key=lambda x: x["updated_at"], reverse=True)
        return {"items": items}
    except Exception as exc:
        db_error(exc)


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    db = db_or_503()
    try:
        doc = conversation_collection(db).document(conversation_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        return {"id": doc.id, **doc.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        db_error(exc)


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    db = db_or_503()
    ref = conversation_collection(db).document(conversation_id)
    try:
        if not ref.get().exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        ref.delete()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as exc:
        db_error(exc)


# -------------------- AI chat with automatic persistence --------------------

@app.post("/api/chat")
def chat(payload: ChatRequest):
    db = db_or_503()
    conversations = conversation_collection(db)
    ref = None

    try:
        if payload.conversation_id:
            ref = conversations.document(payload.conversation_id)
            snap = ref.get()
            if not snap.exists:
                raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
            conversation = snap.to_dict()
        else:
            now = utc_now()
            title = payload.message.strip().replace("\n", " ")[:40]
            ref = conversations.document()
            conversation = {
                "title": title or "새 대화",
                "messages": [],
                "created_at": now,
                "updated_at": now,
            }
            ref.set(conversation)

        history = conversation.get("messages", [])
        # 클라이언트가 아닌 서버에 저장된 대화 기록을 사용합니다.
        safe_history = [
            {"role": m["role"], "content": m["content"]}
            for m in history[-int(os.getenv("MAX_CHAT_HISTORY", "12")):]
            if m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
        ]

        summary = calculate_summary(list_records(db))
        answer = answer_chat(payload.message, summary, safe_history)

        updated_messages = history + [
            {"role": "user", "content": payload.message},
            {"role": "assistant", "content": answer},
        ]
        now = utc_now()
        ref.update({
            "messages": updated_messages,
            "updated_at": now,
        })

        return {
            "conversation_id": ref.id,
            "answer": answer,
            "summary": summary,
        }

    except HTTPException:
        raise
    except OpenAIError as exc:
        print(f"OpenAI error: {type(exc).__name__}")
        raise HTTPException(
            status_code=502,
            detail="AI 응답을 생성하지 못했습니다. API 키와 사용량을 확인해 주세요.",
        ) from exc
    except Exception as exc:
        print(f"Chat error: {type(exc).__name__}")
        raise HTTPException(
            status_code=503,
            detail="채팅 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc
