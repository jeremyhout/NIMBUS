from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from .services import geocode_city, fetch_current_weather, fetch_5day_forecast
from .services import fetch_hourly_24
from .errors import ValidationError, UpstreamError
from .cache import cache_get, cache_set
from .auth import router as auth_router


app = FastAPI(title="Weather App (Sprint 1)")
# Add authentication routes
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="weather_app/static"), name="static")
templates = Jinja2Templates(directory="weather_app/templates")


# In-memory banner store for URNS webhooks (demo only)
LATEST_BANNER: Optional[str] = None


class CityQuery(BaseModel):
    city: str | None = None
    lat: float | None = None
    lon: float | None = None

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Render the new Home page (24-hour view)
    return templates.TemplateResponse("home.html", {"request": request, "banner": LATEST_BANNER})

@app.get("/five-day", response_class=HTMLResponse)
async def five_day(request: Request):
    return templates.TemplateResponse("five_day.html", {"request": request, "banner": LATEST_BANNER})

@app.get("/favorites", response_class=HTMLResponse)
async def favorites(request: Request):
    return templates.TemplateResponse("favorites.html", {"request": request, "banner": LATEST_BANNER})

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "banner": LATEST_BANNER})


# ---- NEW: 24-hour hourly API ----
@app.post("/api/hourly")
async def api_hourly(body: CityQuery):
    try:
        if body.lat is not None and body.lon is not None:
            lat, lon = body.lat, body.lon
            norm_city = body.city or "Selected Location"
        else:
            city = (body.city or "").strip()
            if not city:
                raise ValidationError("City name is required.")
            # small cache, optional
            ck = f"hourly24:{city.lower()}"
            cached = cache_get(ck)
            if cached:
                return cached

            matches = await geocode_city(city)
            if len(matches) > 1:
                return {"matches": matches}
            choice = matches[0]
            lat, lon, norm_city = choice["lat"], choice["lon"], choice["name"]

        hourly = await fetch_hourly_24(lat, lon)  # list of next 24 hours, localized
        payload = {"city": norm_city, "lat": lat, "lon": lon, "hourly": hourly}
        if body.lat is None:
            cache_set(f"hourly24:{(body.city or '').lower()}", payload, ttl=300)
        return payload

    except ValidationError as ve:
        return JSONResponse({"error": str(ve)}, status_code=400)
    except UpstreamError as ue:
        return JSONResponse({"error": str(ue)}, status_code=502)

@app.post("/api/current")
async def api_current(body: CityQuery):
    try:
        # If lat/lon provided, skip geocode
        if body.lat is not None and body.lon is not None:
            lat, lon = body.lat, body.lon
            norm_city = body.city or "Selected Location"
        else:
            city = (body.city or "").strip()
            if not city:
                raise ValidationError("City name is required.")
            ck = f"current:{city.lower()}"
            cached = cache_get(ck)
            if cached:
                return cached
            matches = await geocode_city(city)
            if len(matches) > 1:
                return {"matches": matches}
            choice = matches[0]
            lat, lon, norm_city = choice["lat"], choice["lon"], choice["name"]

        current = await fetch_current_weather(lat, lon)
        payload = {"city": norm_city, "lat": lat, "lon": lon, "current": current}
        if body.lat is None:  # only cache city queries
            cache_set(f"current:{(body.city or '').lower()}", payload, ttl=300)
        return payload

    except ValidationError as ve:
        return JSONResponse({"error": str(ve)}, status_code=400)
    except UpstreamError as ue:
        return JSONResponse({"error": str(ue)}, status_code=502)


@app.post("/api/forecast")
async def api_forecast(body: CityQuery):
    try:
        if body.lat is not None and body.lon is not None:
            lat, lon = body.lat, body.lon
            norm_city = body.city or "Selected Location"
        else:
            city = (body.city or "").strip()
            if not city:
                raise ValidationError("City name is required.")
            ck = f"forecast5:{city.lower()}"
            cached = cache_get(ck)
            if cached:
                return cached
            matches = await geocode_city(city)
            if len(matches) > 1:
                return {"matches": matches}
            choice = matches[0]
            lat, lon, norm_city = choice["lat"], choice["lon"], choice["name"]

        forecast = await fetch_5day_forecast(lat, lon)
        payload = {"city": norm_city, "lat": lat, "lon": lon, "forecast": forecast}
        if body.lat is None:
            cache_set(f"forecast5:{(body.city or '').lower()}", payload, ttl=1800)
        return payload

    except ValidationError as ve:
        return JSONResponse({"error": str(ve)}, status_code=400)
    except UpstreamError as ue:
        return JSONResponse({"error": str(ue)}, status_code=502)


# ---- Webhook endpoint for URNS notifications ----
@app.post("/hooks/reminder")
async def reminder_hook(req: Request, x_app_key: str | None = Header(None)):
    global LATEST_BANNER

    # Security: check shared key
    if x_app_key != "dev-key":
        print("[HOOK] Invalid app key, ignored.")
        return {"status": "ignored"}

    try:
        body = await req.json()
        payload = body.get("payload", {})
        title = payload.get("title", "Reminder")
        msg = payload.get("msg", "")
        fired_at = body.get("fired_at", "unknown time")

        LATEST_BANNER = f"🔔 {title}: {msg} (at {fired_at})"
        print(f"[REMINDER] {title}: {msg}")

        return {"status": "ok"}
    except Exception as e:
        print("[HOOK] Error parsing reminder JSON:", e)
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# === Banner API for the UI ===
@app.get("/api/banner")
async def get_banner():
    # Return the latest banner text (or null)
    return {"banner": LATEST_BANNER}

@app.post("/api/banner/clear")
async def clear_banner():
    global LATEST_BANNER
    LATEST_BANNER = None
    return {"status": "cleared"}
