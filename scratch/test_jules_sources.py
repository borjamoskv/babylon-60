import subprocess
import requests

try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
except Exception:
    token = ""

api_key = "AIzaSyCAo_HMT3iW9RuxEHdG5owL5klTMYUMh9M"

# Combinations of headers
auth_headers = [
    (
        "Bearer token",
        {"Authorization": f"Bearer {token}", "x-goog-user-project": "forward-tape-489302-m7"},
    ),
    ("X-Goog-Api-Key", {"X-Goog-Api-Key": api_key}),
    ("Bearer token as x-goog-api-key", {"X-Goog-Api-Key": token}),
]

# Combinations of base URLs
base_urls = [
    "https://jules.googleapis.com/v1alpha",
    "https://jules.google.com/api/v1alpha",
]

for base in base_urls:
    for name, headers in auth_headers:
        if not headers.get("Authorization") and not headers.get("X-Goog-Api-Key"):
            continue
        for endpoint in ["sources", "sessions"]:
            url = f"{base}/{endpoint}"
            print(f"\n--- GET {url} ({name}) ---")
            try:
                r = requests.get(url, headers=headers, timeout=10)
                print("Status code:", r.status_code)
                try:
                    print("JSON:", r.json())
                except Exception:
                    print("Text:", r.text[:200])
            except Exception as e:
                print("Error:", e)
