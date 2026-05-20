import subprocess
import requests

try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    print(f"Loaded fresh gcloud token prefix: {token[:20]}...")
except Exception as e:
    print("Could not get gcloud token:", e)
    token = ""

base = "https://jules.googleapis.com/v1alpha"

# Try GET /v1alpha/sources and /v1alpha/sessions with different header combinations using fresh token
header_options = [
    # 1. Bearer token + user project
    {"Authorization": f"Bearer {token}", "x-goog-user-project": "forward-tape-489302-m7"},
    # 2. Bearer token only
    {
        "Authorization": f"Bearer {token}",
    },
    # 3. OAuth2 Bearer token in x-goog-api-key? (unlikely but let's test)
    {"X-Goog-Api-Key": token, "x-goog-user-project": "forward-tape-489302-m7"},
]

for i, headers in enumerate(header_options, 1):
    print(f"\n=== Option {i} (headers: {list(headers.keys())}) ===")
    for path in ["sources", "sessions"]:
        url = f"{base}/{path}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"GET {url} -> Status: {r.status_code}")
            print(r.text[:300])
        except Exception as e:
            print(f"Failed: {e}")
