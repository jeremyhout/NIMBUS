"""
test_urns_client.py
Small test client for the URNS microservice.

Demonstrates:
- How to REQUEST data (HTTP calls to /reminders endpoints)
- How to RECEIVE data (JSON responses parsed and printed)
"""

import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "http://127.0.0.1:8081"
APP_KEY = "dev-key"  # must match APP_KEY in urns/app.py

# Convenience headers for authenticated requests
AUTH_HEADERS = {
    "X-App-Key": APP_KEY
}


def pretty_print(title, response: requests.Response):
    """Print status + JSON body in a readable way."""
    print("\n=== " + title + " ===")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print("Body:")
        print(json.dumps(data, indent=2))
    except ValueError:
        print("Non-JSON body:")
        print(response.text)
    print("=" * 40)


def create_sample_cron_reminder():
    """
    Create a recurring (cron) reminder every minute.
    This shows how a client app would REQUEST a reminder to be scheduled.
    """
    url = f"{BASE_URL}/reminders"

    payload = {
        "app_id": "demo-client",        # identifies the calling app
        "type": "cron",                 # "cron" or "time"
        "cron": "*/1 * * * *",          # every minute
        "when": None,                   # unused for cron
        "notify": {
            "webhook": "http://127.0.0.1:8080/hooks/reminder"
        },
        "payload": {
            "title": "Demo Reminder",
            "msg": "This is a test reminder from the demo client."
        },
        "idempotency_key": None
    }

    # Note: we pass JSON + auth header; requests sets Content-Type automatically
    resp = requests.post(url, headers=AUTH_HEADERS, json=payload)
    pretty_print("CREATE /reminders (cron)", resp)

    if resp.ok:
        body = resp.json()
        return body.get("reminder_id")
    return None


def create_sample_one_time_reminder():
    """
    Create a one-time reminder 2 minutes in the future.
    This shows the 'time'-based path of the contract.
    """
    url = f"{BASE_URL}/reminders"

    run_at = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(timespec="seconds")

    payload = {
        "app_id": "demo-client",
        "type": "time",                 # one-time reminder
        "when": run_at,                 # ISO8601 UTC timestamp
        "cron": None,
        "notify": {
            "webhook": "http://127.0.0.1:8080/hooks/reminder"
        },
        "payload": {
            "title": "One-time Reminder",
            "msg": f"Fires at {run_at} (UTC)"
        },
        "idempotency_key": None
    }

    resp = requests.post(url, headers=AUTH_HEADERS, json=payload)
    pretty_print("CREATE /reminders (time)", resp)

    if resp.ok:
        body = resp.json()
        return body.get("reminder_id")
    return None


def list_all_for_app():
    """
    Call GET /reminders?app_id=demo-client and print the list.
    This demonstrates RECEIVING structured data from the microservice.
    """
    url = f"{BASE_URL}/reminders"
    params = {
        "app_id": "demo-client"
    }
    resp = requests.get(url, headers=AUTH_HEADERS, params=params)
    pretty_print("GET /reminders?app_id=demo-client", resp)


def get_single_reminder(reminder_id: str):
    """
    GET /reminders/{id} to show how a client can inspect a single reminder.
    """
    url = f"{BASE_URL}/reminders/{reminder_id}"
    resp = requests.get(url, headers=AUTH_HEADERS)
    pretty_print(f"GET /reminders/{reminder_id}", resp)


def delete_single_reminder(reminder_id: str):
    """
    DELETE /reminders/{id} demonstrates cancelling a reminder.
    """
    url = f"{BASE_URL}/reminders/{reminder_id}"
    resp = requests.delete(url, headers=AUTH_HEADERS)
    pretty_print(f"DELETE /reminders/{reminder_id}", resp)


def delete_all_for_demo_client():
    """
    DELETE /reminders with auth header to clear everything.
    (Good to clean up after the demo.)
    """
    url = f"{BASE_URL}/reminders"
    resp = requests.delete(url, headers=AUTH_HEADERS)
    pretty_print("DELETE /reminders (clear all)", resp)


def main():
    print("=== URNS Demo Client ===")
    print("Assumes URNS is running at http://127.0.0.1:8081")

    # 1) Create a cron reminder
    cron_id = create_sample_cron_reminder()

    # 2) Create a one-time reminder
    time_id = create_sample_one_time_reminder()

    # 3) List all reminders for app_id=demo-client
    list_all_for_app()

    # 4) Inspect one of the reminders in detail (if created successfully)
    if cron_id:
        get_single_reminder(cron_id)

    # 5) Demonstrate delete for that reminder
    if cron_id:
        delete_single_reminder(cron_id)

    # 6) Show list after deletion
    list_all_for_app()

    # 7) (Optional) Clean up everything for demo-client
    # delete_all_for_demo_client()


if __name__ == "__main__":
    main()
