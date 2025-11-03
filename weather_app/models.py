
from pydantic import BaseModel
from typing import Optional, List


class CurrentWeather(BaseModel):
    temperature_c: Optional[float]
    windspeed: Optional[float]
    weathercode: Optional[int]
    time: Optional[str]


class DailyForecast(BaseModel):
    date: str
    temp_max_c: float
    temp_min_c: float
    precip_prob: Optional[float]
