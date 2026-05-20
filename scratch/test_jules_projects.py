import os
import requests
import subprocess

# Get dynamic gcloud access token
try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    print("Fetched active gcloud token successfully.")
except Exception as e:
    token = os.environ.get("JULES_API_KEY", "")
    print(f"Failed to fetch gcloud token, using fallback: {e}")

project = "forward-tape-489302-m7"
locations = ["global", "us-central1"]

headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project}

for loc in locations:
    print(f"\n================ Location: {loc} ================")
    for resource in ["sources", "sessions"]:
        url = f"https://jules.googleapis.com/v1alpha/projects/{project}/locations/{loc}/{resource}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"GET {url} -> Status: {r.status_code}")
            if r.status_code == 200:
                print("Success! JSON keys:", list(r.json().keys()))
                print("Response JSON:", r.json())
            else:
                print("Error JSON:", r.json())
        except Exception as e:
            print(f"GET {url} Failed: {e}")
