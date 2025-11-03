# Sprint 1 – Weather App + URNS


## Run services


# Terminal 1 – Weather App
uvicorn weather_app.app:app --reload --port 8080


# Terminal 2 – URNS
uvicorn urns.app:app --reload --port 8081


Open http://127.0.0.1:8080


## Demo flow
1) Enter a city (e.g., Long Beach) and click **Get Weather** → shows current.
2) Click **5‑Day Forecast** → shows forecast.
3) Click **Schedule Daily Reminder (7:00)** → creates cron job in URNS.
- When the job fires, URNS POSTs to `/hooks/reminder` and a banner shows on the Weather UI.


## User Stories mapping
- **US1 View Current Weather**: `/api/current`, UI form submit. Testability via `services.py` seams + unit test.
- **US2 5‑Day Forecast**: `/api/forecast` + caching and error messages; Availability via retry-attempts (add later) & non-blank states.
- **US3 Handle Invalid Inputs**: Required `<input>` + inline error, backend 400 with clear message; Maintainability via centralized `errors.py` and form validator in `script.js`.


## Inclusivity Heuristics (examples)
- **IH#1 Provide choice**: Current vs 5‑day buttons; optional schedule button; progressive disclosure in copy.
- **IH#2 Use plain language**: Helper text, clear error copy, ‘Schedule Daily Reminder’ explicit.
- **IH#3 Let users gather as much or as little info**: The forecast panel is separate; users choose what to open; errors are inline, non-modal.
- **Accessibility**: Labels, `aria-live` for errors and banner, keyboard-friendly form, sufficient contrast.


## Quality Attributes
- **Testability**: `services.py` has standalone async functions; `tests/test_services.py` shows mocking pattern.
- **Availability**: Caching (`cache.py`) prevents blank screens during transient upstream hiccups; UI shows helpful messages instead of failing silently.
- **Maintainability**: Centralized `errors.py`; thin handlers; clear separation of concerns (UI template, static JS, services, cache).