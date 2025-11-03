# urns/app.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from dateutil.parser import isoparse
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from contextlib import asynccontextmanager

# ---------------------------- Config ---------------------------------

APP_KEY = "dev-key"  # simple shared secret for Sprint 1
ALLOWED_ORIGINS = ["http://127.0.0.1:8080", "http://localhost:8080"]
DELIVERY_TIMEOUT_SECS = 5
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 8, 30]  # seconds

# ---------------------------- Scheduler -------------------------------

scheduler = AsyncIOScheduler(timezone=timezone.utc)

# ---------------------------- Storage ---------------------------------

# Minimal in-memory storage; fine for Sprint 1.
REMINDERS: Dict[str, Dict[str, Any]] = {}   # reminder_id -> record

# ----------------------------- Models ---------------------------------

class Notify(BaseModel):
    webhook: str  # keep as HttpUrl for stricter check if you want


class ReminderIn(BaseModel):
    app_id: str = Field(..., min_length=1)
    type: str  # "time" or "cron"
    when: Optional[str] = None           # ISO8601 if type == "time"
    cron: Optional[str] = None           # crontab if type == "cron"
    notify: Notify
    payload: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None

    @field_validator("app_id", mode="before")
    @classmethod
    def _strip_app_id(cls, v):
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("app_id must be a non-empty string")
        return v

    @field_validator("type", mode="after")
    @classmethod
    def _v_type(cls, v):
        lv = (v or "").lower()
        if lv not in ("time", "cron"):
            raise ValueError("type must be 'time' or 'cron'")
        return lv

    @model_validator(mode="after")
    def _require_when_or_cron(self):
        # Cross-field rule: enforce when/cron depending on type
        if self.type == "time":
            if not self.when:
                raise ValueError("when is required for type=='time' (ISO8601 UTC)")
        elif self.type == "cron":
            if not self.cron:
                raise ValueError("cron is required for type=='cron'")
        return self


class ReminderOut(BaseModel):
    reminder_id: str
    status: str = "scheduled"


class ReminderRecord(BaseModel):
    reminder_id: str
    app_id: str
    type: str
    when: Optional[str] = None
    cron: Optional[str] = None
    notify: Notify
    payload: Optional[Dict[str, Any]] = None
    status: str = "scheduled"  # scheduled|delivered|cancelled|failed
    attempts: int = 0
    last_error: Optional[str] = None
    next_run_time: Optional[str] = None  # ISO time of next fire (scheduler view)

# ------------------------- Delivery Logic -----------------------------

async def deliver(reminder_id: str) -> None:
    """
    Attempt to deliver the reminder payload to the webhook.
    Implements simple retry with exponential backoff.
    """
    rec = REMINDERS.get(reminder_id)
    if not rec:
        return  # was deleted

    # short-circuit if already cancelled/failed
    if rec.get("status") in ("cancelled", "failed"):
        return

    attempts = rec.get("attempts", 0)

    try:
        async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECS) as client:
            body = {
                "reminder_id": reminder_id,
                "app_id": rec["app_id"],
                "fired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "payload": rec.get("payload") or {},
            }
            headers = {
                "Content-Type": "application/json",
                "X-App-Id": rec["app_id"],
                "X-URNS-Delivery": str(attempts + 1),
                # Echo shared secret for Sprint 1 (receiver can check this)
                "X-App-Key": APP_KEY,
            }
            resp = await client.post(str(rec["notify"]["webhook"]), json=body, headers=headers)
            resp.raise_for_status()

        # success
        rec["attempts"] = 0 if rec["type"] == "cron" else attempts + 1
        rec["last_error"] = None
        if rec["type"] == "time":
            rec["status"] = "delivered"
        else:
            rec["status"] = "scheduled"

    except Exception as e:
        # schedule retry if we have budget
        rec["attempts"] = attempts + 1
        rec["last_error"] = str(e)

        if rec["type"] == "time":
            # For one-off, retry a few times; if exhausted, mark failed
            if attempts < MAX_RETRIES:
                backoff = RETRY_BACKOFF[min(attempts, len(RETRY_BACKOFF)-1)]
                when = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                scheduler.add_job(
                    deliver,
                    trigger=DateTrigger(run_date=when),
                    args=[reminder_id],
                    id=f"retry:{reminder_id}:{attempts+1}",
                    replace_existing=True,
                )
                rec["next_run_time"] = when.isoformat(timespec="seconds")
            else:
                rec["status"] = "failed"
        else:
            # For cron jobs, do NOT change the cron schedule; next tick will retry.
            pass

def schedule_reminder(rec: Dict[str, Any]) -> None:
    """
    Register the reminder with the scheduler.
    For cron: job id = reminder_id (fires repeatedly)
    For time: job id = reminder_id (fires once)
    """
    reminder_id = rec["reminder_id"]
    if rec["type"] == "cron":
        # Validate cron with a friendly 400 on error
        try:
            trigger = CronTrigger.from_crontab(rec["cron"], timezone=timezone.utc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid cron: {e}")
        scheduler.add_job(
            deliver,
            trigger=trigger,
            args=[reminder_id],
            id=reminder_id,
            replace_existing=True,
        )
        # next_run_time will be computed by scheduler; read it via get_next_run_time
    else:
        # one-off time
        try:
            run_at = isoparse(rec["when"])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid 'when' (ISO8601): {e}")
        if run_at.tzinfo is None:
            # assume UTC if no tz
            run_at = run_at.replace(tzinfo=timezone.utc)
        trigger = DateTrigger(run_date=run_at)
        scheduler.add_job(
            deliver,
            trigger=trigger,
            args=[reminder_id],
            id=reminder_id,
            replace_existing=True,
        )
        rec["next_run_time"] = run_at.isoformat(timespec="seconds")

def get_next_run_time(reminder_id: str) -> Optional[str]:
    job = scheduler.get_job(reminder_id)
    if job and job.next_run_time:
        # APScheduler returns aware datetime in scheduler timezone
        return job.next_run_time.astimezone(timezone.utc).isoformat(timespec="seconds")
    return REMINDERS.get(reminder_id, {}).get("next_run_time")

# --------------------------- Lifespan ---------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not scheduler.running:
        scheduler.start()
    try:
        yield
    finally:
        # Shutdown
        if scheduler.running:
            scheduler.shutdown(wait=False)

# ---------------------------- App & CORS ------------------------------

# Create exactly ONE app with lifespan
app = FastAPI(title="Universal Reminder & Notification Service (URNS)", lifespan=lifespan)

# Attach CORS to the SAME app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],   # allow POST/DELETE etc.
    allow_headers=["*"],   # allow X-App-Key, Content-Type
)

# --------------------------- Endpoints --------------------------------

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/reminders", response_model=ReminderOut)
async def create_reminder(body: ReminderIn, x_app_key: Optional[str] = Header(None)):
    if x_app_key != APP_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    reminder_id = str(uuid.uuid4())
    rec: Dict[str, Any] = {
        "reminder_id": reminder_id,
        "app_id": body.app_id,
        "type": body.type,  # "time" | "cron"
        "when": body.when,
        "cron": body.cron,
        "notify": body.notify.dict(),
        "payload": body.payload or {},
        "status": "scheduled",
        "attempts": 0,
        "last_error": None,
        "next_run_time": None,
    }
    REMINDERS[reminder_id] = rec
    schedule_reminder(rec)
    return ReminderOut(reminder_id=reminder_id)

@app.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str, x_app_key: Optional[str] = Header(None)):
    if x_app_key != APP_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    job = scheduler.get_job(reminder_id)
    if job:
        scheduler.remove_job(reminder_id)

    # Also remove any pending retry jobs
    for j in list(scheduler.get_jobs()):
        if j.id.startswith(f"retry:{reminder_id}:"):
            scheduler.remove_job(j.id)

    rec = REMINDERS.get(reminder_id)
    if rec:
        rec["status"] = "cancelled"
    return {"status": "cancelled", "reminder_id": reminder_id}

@app.get("/reminders")
async def list_reminders(
    app_id: Optional[str] = Query(None),
    x_app_key: Optional[str] = Header(None),
):
    if x_app_key != APP_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    items = []
    for rec in REMINDERS.values():
        if app_id and rec["app_id"] != app_id:
            continue
        rr = ReminderRecord(**rec).dict()
        rr["next_run_time"] = get_next_run_time(rec["reminder_id"])
        items.append(rr)
    return items

@app.get("/reminders/{reminder_id}")
async def get_reminder(
    reminder_id: str,
    x_app_key: Optional[str] = Header(None),
):
    if x_app_key != APP_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    rec = REMINDERS.get(reminder_id)
    if not rec:
        raise HTTPException(status_code=404, detail="not found")

    rr = ReminderRecord(**rec).model_dump()
    rr["next_run_time"] = get_next_run_time(reminder_id)
    return rr

@app.delete("/reminders")
async def delete_all_reminders(x_app_key: Optional[str] = Header(None)):
    if x_app_key != APP_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    REMINDERS.clear()
    for job in list(scheduler.get_jobs()):
        scheduler.remove_job(job.id)
    return {"status": "cleared"}
