import requests
try:
    print(requests.get('http://localhost:8000/insights/AAPL').json())
except Exception as e:
    print(f"Error: {e}")
