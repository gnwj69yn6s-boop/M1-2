
from datetime import date, timedelta
import random

from dotenv import load_dotenv

from services import data_collection, get_db, utc_now

load_dotenv()
random.seed(42)


def main():
    db = get_db()
    collection = data_collection(db)
    today = date.today()
    exercises = [
        ("걷기", 30, 120),
        ("달리기", 40, 350),
        ("자전거", 45, 300),
        ("근력 운동", 50, 250),
        ("요가", 35, 100),
        ("수영", 40, 320),
    ]

    batch = db.batch()
    count = 0

    for i in range(120):
        day = today - timedelta(days=119 - i)
        # 기록이 없는 날도 일부 포함해 실제 데이터처럼 구성합니다.
        if i % 7 == 0:
            continue

        kind, base_minutes, base_calories = exercises[i % len(exercises)]
        minutes = max(10, round(base_minutes + random.randint(-12, 18)))
        calories = max(30, round(base_calories * minutes / base_minutes
                                  + random.randint(-25, 25)))

        ref = collection.document()
        now = utc_now()
        batch.set(ref, {
            "date": day.isoformat(),
            "value": minutes,
            "exercise_type": kind,
            "calories": calories,
            "memo": f"테스트 운동 기록 {i + 1}",
            "created_at": now,
            "updated_at": now,
        })
        count += 1

        if count % 400 == 0:
            batch.commit()
            batch = db.batch()

    if count % 400:
        batch.commit()

    print(f"완료: 테스트 운동 기록 {count}개 생성")


if __name__ == "__main__":
    main()
