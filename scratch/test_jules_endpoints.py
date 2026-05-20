import os
import requests
import subprocess

# Get dynamic gcloud access token
try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    print("Fetched active gcloud token successfully.")
except Exception as e:
    token = os.environ.get("JULES_API_KEY", "")
    print(f"Failed to fetch gcloud token, using fallback from env: {e}")

bases = [
    "https://jules.googleapis.com/v1alpha",
    "https://aida.googleapis.com/v1/swebot",
]

headers_variations = [
    {
        "Authorization": f"Bearer {token}",
    },
    {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": "forward-tape-489302-m7",
    },
]

for base in bases:
    print(f"\n================ Base URL: {base} ================")
    for i, headers in enumerate(headers_variations, 1):
        print(f"\n--- Variation {i}: Headers: {list(headers.keys())} ---")
        for path in ["sources", "sessions"]:
            url = f"{base}/{path}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                print(f"GET {path} -> Status: {r.status_code}")
                if r.status_code == 200:
                    print("Success! Response keys:", list(r.json().keys()))
                    # Print first item summary if available
                    data = r.json()
                    if path in data and len(data[path]) > 0:
                        print(f"First {path} item:", data[path][0])
                else:
                    print("Error JSON:", r.json())
            except Exception as e:
                print(f"GET {path} Failed: {e}")
