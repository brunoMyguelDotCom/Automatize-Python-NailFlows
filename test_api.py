import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8080"


def test_cors():
    print("Testing CORS...", end=" ")
    response = requests.get(
        f"{BASE_URL}/agendamentos", headers={"Origin": "http://localhost:3000"}
    )
    if "Access-Control-Allow-Origin" in response.headers:
        print("✅")
    else:
        print("❌ CORS header missing")


def test_end_time_json():
    print("Testing end_time in JSON...", end=" ")
    response = requests.get(f"{BASE_URL}/agendamentos")
    data = response.json()
    if len(data) > 0 and "end_time" in data[0]:
        print("✅")
    else:
        print("❌ end_time not found in JSON response")


def test_filtering_and_sorting():
    print("Testing filtering and sorting...", end=" ")
    # Create a few appointments
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # We assume the API is running and can create appointments
    payloads = [
        {
            "client": {"name": "C1", "email": "c1@test.com"},
            "service": "S1",
            "start_time": (today + timedelta(hours=10)).isoformat(),
            "duration_minutes": 60,
        },
        {
            "client": {"name": "C2", "email": "c2@test.com"},
            "service": "S2",
            "start_time": (today + timedelta(hours=8)).isoformat(),
            "duration_minutes": 60,
        },
        {
            "client": {"name": "C3", "email": "c3@test.com"},
            "service": "S3",
            "start_time": (tomorrow + timedelta(hours=10)).isoformat(),
            "duration_minutes": 60,
        },
    ]

    for p in payloads:
        requests.post(f"{BASE_URL}/agendamentos", json=p)

    # Test filter for today
    response = requests.get(
        f"{BASE_URL}/agendamentos",
        params={"start_date": today.isoformat(), "end_date": tomorrow.isoformat()},
    )
    data = response.json()

    # Check if only today's are returned (C1 and C2)
    if len(data) == 2:
        # Check sorting: C2 (8h) should come before C1 (10h)
        if data[0]["start_time"] < data[1]["start_time"]:
            print("✅")
        else:
            print("❌ Not sorted by time")
    else:
        print(f"❌ Filter failed. Expected 2, got {len(data)}")


if __name__ == "__main__":
    try:
        test_cors()
        test_end_time_json()
        test_filtering_and_sorting()
    except Exception as e:
        print(f"Error: {e}")
