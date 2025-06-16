 
from pydantic import BaseModel
from datetime import datetime

class StatusRecord(BaseModel):
    store_id: str
    timestamp_utc: datetime
    status: str 

class BusinessHour(BaseModel):
    store_id: str
    dayOfWeek: int
    start_time_local: str  
    end_time_local: str   

class StoreTimezone(BaseModel):
    store_id: str
    timezone_str: str
    