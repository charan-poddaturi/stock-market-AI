from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class StockCreate(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

class StockResponse(StockCreate):
    id: int
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PredictionResponse(BaseModel):
    id: int
    ticker: str
    model: str
    predicted_direction: str
    probability_up: float
    confidence_score: float
    price_target_1d: Optional[float]
    price_target_5d: Optional[float]
    price_target_30d: Optional[float]
    signal: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
