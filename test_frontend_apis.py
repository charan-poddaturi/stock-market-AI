import requests
import time

urls = [
    "http://localhost:3000/explorer",
    "http://localhost:3000/prediction",
    "http://localhost:3000/portfolio",
    "http://localhost:3000/ai-insights",
    "http://localhost:3000/strategy-lab",
]

print("Testing frontend page routes to ensure NextJS SSR functions without bugs")
for u in urls:
    try:
        t0 = time.time()
        print(f"Fetching {u}...")
        r = requests.get(u)
        print(f"Code: {r.status_code} in {time.time()-t0:.2f}s")
        if r.status_code != 200:
            print("Error rendering:", r.text[:200])
    except Exception as e:
        print(f"Exception for {u}: {e}")
