# URNS – Universal Reminder & Notification Service

URNS is a standalone microservice that lets any **client application** schedule reminders and receive them later through **webhook callbacks**.

## 1. Overview

**Workflow:**

1. A client app calls **POST `/reminders`** and includes:
   - The reminder type (`time` or `cron`)
   - When it fires (ISO time or cron syntax)
   - A webhook URL to POST back to
   - Optional payload data

2. URNS schedules the reminder.

3. When the scheduled moment arrives, URNS sends a **POST** to the provided webhook URL.

4. Clients can:
   - **List reminders** → GET `/reminders`
   - **Get a reminder** → GET `/reminders/{id}`
   - **Delete one** → DELETE `/reminders/{id}`
   - **Delete all** → DELETE `/reminders`

**Important:**  
URNS stores reminders **in memory only** (no database). Restarting the process clears all reminders. This is acceptable for the class project.

---

## 2. Running the Microservice

### Install Requirements

```bash
pip install fastapi uvicorn httpx apscheduler pydantic python-dateutil
```

### Start URNS

```bash
uvicorn urns.app:app --reload --port 8081
```

URNS will run at:

```text
http://127.0.0.1:8081
```

---

## 3. Authentication

All endpoints (except `/healthz`) require:

```http
X-App-Key: dev-key
```

Without it, URNS returns:

```json
{ "detail": "invalid api key" }
```

---

## 4. Data Model – Communication Contract

### 4.1. `ReminderIn` (Request Body)

```json
{
  "app_id": "string (required)",
  "type": "time | cron",
  "when": "ISO8601 datetime or null",
  "cron": "cron syntax or null",
  "notify": {
    "webhook": "string URL"
  },
  "payload": {
    "...": "optional JSON data"
  },
  "idempotency_key": "optional string"
}
```

Rules:

- `type == "time"` → must include `"when"`
- `type == "cron"` → must include `"cron"`
- `notify.webhook` → where URNS will POST the reminder

---

### 4.2. `ReminderOut` (Response Body for POST)

```json
{
  "reminder_id": "string",
  "status": "scheduled"
}
```

---

### 4.3. `ReminderRecord` (Returned by GET Endpoints)

```json
{
  "reminder_id": "string",
  "app_id": "string",
  "type": "time | cron",
  "when": "string or null",
  "cron": "string or null",
  "notify": { "webhook": "URL string" },
  "payload": { "...": "JSON" },
  "status": "scheduled | delivered | cancelled | failed",
  "attempts": 0,
  "last_error": null,
  "next_run_time": "ISO8601 string or null"
}
```

---

## 5. Endpoints

### 5.1. Health Check

```http
GET /healthz
```

Response:

```json
{ "status": "ok" }
```

---

### 5.2. Create a Reminder

```http
POST /reminders
X-App-Key: dev-key
Content-Type: application/json
```

Example request:

```json
{
  "app_id": "weather-app",
  "type": "cron",
  "cron": "0 7 * * *",
  "when": null,
  "notify": { "webhook": "http://127.0.0.1:8080/hooks/reminder" },
  "payload": {
    "title": "Daily Forecast",
    "msg": "Check today's weather!"
  }
}
```

Example response:

```json
{
  "reminder_id": "8049e7a9-284d-44aa-a067-390ed2b5f145",
  "status": "scheduled"
}
```

---

### 5.3. List Reminders

```http
GET /reminders?app_id=weather-app
X-App-Key: dev-key
```

Returns a list of `ReminderRecord`.

---

### 5.4. Get One Reminder

```http
GET /reminders/{id}
X-App-Key: dev-key
```

Returns the `ReminderRecord`.

---

### 5.5. Delete a Reminder

```http
DELETE /reminders/{id}
X-App-Key: dev-key
```

Response:

```json
{
  "status": "cancelled",
  "reminder_id": "{id}"
}
```

---

### 5.6. Delete All Reminders

```http
DELETE /reminders
X-App-Key: dev-key
```

Response:

```json
{ "status": "cleared" }
```

---

## 6. Webhook Callback Contract (How Clients Receive Data)

When the reminder fires, URNS calls:

```http
POST {your_webhook_url}
Content-Type: application/json
X-App-Id: {your app_id}
X-URNS-Delivery: 1
X-App-Key: dev-key
```

Payload sent to your app:

```json
{
  "reminder_id": "string",
  "app_id": "string",
  "fired_at": "ISO8601 timestamp",
  "payload": {
    "title": "Daily Forecast",
    "msg": "Check today's weather!"
  }
}
```

Your app should respond:

```json
{ "ok": true }
```

with `HTTP 200`.

---

## 7. Example Test Program

```python
import httpx

URNS = "http://127.0.0.1:8081"
API_KEY = "dev-key"

def test_schedule():
    body = {
        "app_id": "demo-client",
        "type": "time",
        "when": "2025-11-02T07:00:00Z",
        "notify": { "webhook": "http://127.0.0.1:8000/hooks/reminder" },
        "payload": { "msg": "Test reminder" }
    }
    r = httpx.post(
        f"{URNS}/reminders",
        headers={"X-App-Key": API_KEY},
        json=body
    )
    print(r.status_code, r.json())

if __name__ == "__main__":
    test_schedule()
```

---

## 8. UML Sequence Diagram

Below is the UML diagram describing the communication flow between a Client App and the URNS microservice:

<p align="center">
  <img src="./uml_sequence.png" width="700">
  <br>
  <em>Figure 1 — URNS Microservice Communication Flow</em>
</p>


```

---

## 9. How To Integrate URNS

1. Run URNS on port **8081**.
2. Add a webhook endpoint in your app:
   - Example: `POST /hooks/reminder`
3. Use `POST /reminders` to schedule callbacks.
4. Always send header:

   ```http
   X-App-Key: dev-key
   ```

5. Use GET/DELETE endpoints to manage reminders.

---

## 10. Notes

- URNS stores reminders **in-memory only**.
- URNS retries failed webhooks (for time-based reminders).
- All clients must follow the communication contract exactly.

---

**End of README**
