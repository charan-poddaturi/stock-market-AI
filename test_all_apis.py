import requests
import sys

BASE_URL = 'http://localhost:8000'
endpoints = [
    ('/stocks/AAPL', 'Stock Data'),
    ('/predict', 'Prediction', 'POST', {'ticker': 'AAPL', 'days': 30, 'model': 'ensemble'}),
    ('/sentiment/AAPL', 'Sentiment'),
    ('/portfolio', 'Portfolio', 'POST', {'initial_capital': 10000, 'positions': [{'ticker': 'AAPL', 'shares': 10}], 'risk_tolerance': 'medium'}),
    ('/backtest', 'Backtest', 'POST', {'ticker': 'AAPL', 'strategy': 'sma_crossover', 'initial_capital': 10000, 'start_date': '2023-01-01', 'end_date': '2023-12-31', 'params': {}}),
    ('/screen', 'Screener', 'POST', {'filters': {'rsi_max': 30}, 'limit': 10}),
    ('/insights/AAPL', 'Insights')
]

print("Starting API tests...")
errors = ()
for ep in endpoints:
    url = BASE_URL + ep[0]
    name = ep[1]
    method = ep[2] if len(ep) > 2 else 'GET'
    data = ep[3] if len(ep) > 3 else None
    
    try:
        print(f"Testing {name} ({method} {ep[0]})...", end=" ")
        if method == 'GET':
            res = requests.get(url)
        else:
            res = requests.post(url, json=data)
            
        if res.status_code == 200:
            print("OK")
        else:
            print(f"FAILED (Status {res.status_code})")
            print(res.text)
            
    except Exception as e:
        print(f"ERROR: {e}")

print("Done.")
