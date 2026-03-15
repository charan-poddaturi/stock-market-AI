import httpx
import requests
from typing import Optional
from config import settings

def get_exchange_rate_sync(from_currency: str = "USD", to_currency: str = settings.target_currency) -> Optional[float]:
    """Sync version for non-async contexts."""
    if from_currency == to_currency:
        return 1.0
    try:
        response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["rates"].get(to_currency)
    except Exception:
        pass
    return None

async def get_exchange_rate(from_currency: str = "USD", to_currency: str = settings.target_currency) -> Optional[float]:
    """Fetch exchange rate from exchangerate-api.com (free tier)."""
    if from_currency == to_currency:
        return 1.0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
            if response.status_code == 200:
                data = response.json()
                return data["rates"].get(to_currency)
    except Exception:
        pass
    return None

async def convert_price(price: float, from_currency: str = "USD") -> float:
    """Convert price to target currency."""
    rate = await get_exchange_rate(from_currency)
    if rate:
        return price * rate
    return price  # fallback to original if conversion fails

def convert_price_sync(price: float, from_currency: str = "USD") -> float:
    """Sync version of convert_price. Converts from_currency to target_currency."""
    if from_currency == settings.target_currency:
        return price
    rate = get_exchange_rate_sync(from_currency, settings.target_currency)
    if rate:
        return price * rate
    return price  # fallback