import os
import requests
from pathlib import Path

# Load from .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with env_path.open() as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, val = stripped.split("=", 1)
                os.environ[key] = val

token = os.environ.get("JULES_API_KEY", "")
print(f"Loaded Token: {token[:20]}...")

base_urls = [
    "https://jules.googleapis.com/v1alpha",
]

headers_variations = [
    # Variation 1: Authorization Bearer
    {
        "Authorization": f"Bearer {token}",
    },
    # Variation 2: Authorization Bearer + user project
    {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": "forward-tape-489302-m7",
    },
    # Variation 3: X-Goog-Api-Key
    {
        "X-Goog-Api-Key": token,
    },
    # Variation 4: x-goog-api-key + user project
    {
        "X-Goog-Api-Key": token,
        "x-goog-user-project": "forward-tape-489302-m7",
    },
]

for base in base_urls:
    for i, headers in enumerate(headers_variations, 1):
        print(f"\n--- Variation {i}: Headers: {list(headers.keys())} ---")
        for path in ["sources", "sessions"]:
            url = f"{base}/{path}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                print(f"GET {path} -> Status: {r.status_code}")
                if r.status_code == 200:
                    print("Success! Response JSON:", r.json())
                else:
                    print("Error JSON:", r.json())
            except Exception as e:
                print(f"GET {path} Failed: {e}")
