import pytest
import anyio
from weather_app.services import fetch_5day_forecast


@pytest.mark.anyio
async def test_fetch_5day_forecast_contract(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "daily": {
                    "time": ["2025-10-30","2025-10-31","2025-11-01","2025-11-02","2025-11-03"],
                    "temperature_2m_max": [20,21,22,23,24],
                    "temperature_2m_min": [10,11,12,13,14],
                    "precipitation_probability_max": [5,10,20,0,15]
                }
            }
    async def fake_get(url, params=None, headers=None):
        return FakeResp()


    import httpx
    monkeypatch.setattr(httpx.AsyncClient, '__aenter__', lambda self: self)
    monkeypatch.setattr(httpx.AsyncClient, '__aexit__', lambda self, exc_type, exc, tb: None)
    monkeypatch.setattr(httpx.AsyncClient, 'get', fake_get)


    result = await fetch_5day_forecast(0,0)
    assert len(result) == 5
    assert result[0]['date'] == "2025-10-30"