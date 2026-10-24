
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db():
    if firebase_admin._apps:
        return firestore.client()

    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()

    if raw_json:
        info = json.loads(raw_json)
        cred = credentials.Certificate(info)
        project_id = project_id or info.get("project_id")
    elif key_path:
        path = Path(key_path)
        if not path.is_file():
            raise RuntimeError("Firebase 서비스 계정 파일을 찾을 수 없습니다.")
        cred = credentials.Certificate(str(path))
    else:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON 또는 "
            "FIREBASE_SERVICE_ACCOUNT_PATH를 설정해 주세요."
        )

    options = {"projectId": project_id} if project_id else None
    firebase_admin.initialize_app(cred, options=options)
    return firestore.client()


def data_collection(db):
    return db.collection("data")


def conversation_collection(db):
    return db.collection("conversations")


def normalize_record(doc):
    item = doc.to_dict()
    item["id"] = doc.id
    return item


def list_records(db, limit=2000):
    docs = data_collection(db).stream()
    records = [normalize_record(doc) for doc in docs]
    records.sort(key=lambda x: str(x.get("date", "")))
    return records[-limit:]


def calculate_summary(records):
    """운동 시간을 기준으로 시계열 통계를 계산합니다."""
    if not records:
        return {
            "period": None,
            "count": 0,
            "metrics": {
                "total_minutes": 0,
                "average_minutes": 0,
                "max_minutes": 0,
                "min_minutes": 0,
                "total_calories": 0,
                "average_calories": 0,
                "active_days": 0,
            },
            "trend": "데이터 부족",
            "weekly_comparison": None,
            "recent_records": [],
        }

    rows = sorted(records, key=lambda r: str(r["date"]))
    minutes = [float(r.get("value", 0)) for r in rows]
    calories = [float(r.get("calories", 0)) for r in rows]
    dates = [date.fromisoformat(str(r["date"])[:10]) for r in rows]

    today = date.today()
    recent_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    previous_end = today - timedelta(days=7)

    recent = [
        r for r in rows
        if recent_start <= date.fromisoformat(str(r["date"])[:10]) <= today
    ]
    previous = [
        r for r in rows
        if previous_start <= date.fromisoformat(str(r["date"])[:10]) <= previous_end
    ]

    recent_minutes = sum(float(r.get("value", 0)) for r in recent)
    previous_minutes = sum(float(r.get("value", 0)) for r in previous)

    if not previous:
        change_percent = None
        weekly_trend = "비교 데이터 부족"
    elif previous_minutes == 0:
        change_percent = 100.0 if recent_minutes > 0 else 0.0
        weekly_trend = "증가" if recent_minutes > 0 else "유지"
    else:
        change_percent = round(
            (recent_minutes - previous_minutes) / previous_minutes * 100, 1
        )
        weekly_trend = (
            "증가" if change_percent > 0
            else "감소" if change_percent < 0
            else "유지"
        )

    if len(rows) < 2:
        trend = "데이터 부족"
    else:
        # 최근 7개 기록의 평균과 그 이전 7개 기록의 평균 비교
        recent_values = minutes[-7:]
        previous_values = minutes[-14:-7]
        if not previous_values:
            trend = "기록 축적 중"
        else:
            old_avg = mean(previous_values)
            new_avg = mean(recent_values)
            if new_avg > old_avg * 1.05:
                trend = "상승"
            elif new_avg < old_avg * 0.95:
                trend = "하락"
            else:
                trend = "유지"

    return {
        "period": f"{dates[0].isoformat()} ~ {dates[-1].isoformat()}",
        "count": len(rows),
        "metrics": {
            "total_minutes": round(sum(minutes), 1),
            "average_minutes": round(mean(minutes), 1),
            "max_minutes": round(max(minutes), 1),
            "min_minutes": round(min(minutes), 1),
            "total_calories": round(sum(calories), 1),
            "average_calories": round(mean(calories), 1),
            "active_days": len(set(dates)),
        },
        "trend": trend,
        "weekly_comparison": {
            "recent_7_days_minutes": round(recent_minutes, 1),
            "previous_7_days_minutes": round(previous_minutes, 1),
            "change_percent": change_percent,
            "trend": weekly_trend,
        },
        "recent_records": rows[-10:],
    }


def get_openai_client():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=key)


def answer_chat(question, summary, history):
    client = get_openai_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    system_prompt = f"""
당신은 사용자의 운동 기록을 분석하는 친절한 한국어 AI 비서입니다.

아래는 저장된 운동 기록에서 서버가 계산한 요약입니다.
<운동_요약>
{json.dumps(summary, ensure_ascii=False, default=str)}
</운동_요약>

규칙:
- 답변은 위 요약과 대화에 제공된 사실을 근거로 작성합니다.
- 요약에 없는 운동 기록이나 수치를 만들어 내지 않습니다.
- 운동 시간은 분, 칼로리는 kcal로 표시합니다.
- 주간 비교는 요약에 포함된 최근 7일 및 이전 7일 기준임을 명시합니다.
- 데이터가 없거나 부족하면 그 사실을 분명히 설명합니다.
- 의학적 진단이나 개인별 안전을 보장하는 처방은 하지 않습니다.
- 간결하고 실용적인 한국어로 답변합니다.
"""

    messages = [{"role": "system", "content": system_prompt}]
    max_history = int(os.getenv("MAX_CHAT_HISTORY", "12"))
    messages.extend(history[-max_history:])
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "700")),
        temperature=0.3,
    )
    return response.choices[0].message.content or "답변을 생성하지 못했습니다."
