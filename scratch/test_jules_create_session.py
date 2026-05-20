import subprocess
import requests

try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
except Exception as e:
    print("Could not get gcloud token:", e)
    token = ""

base = "https://jules.googleapis.com/v1alpha"
project = "forward-tape-489302-m7"

headers = {
    "Authorization": f"Bearer {token}",
    "x-goog-user-project": project,
    "Content-Type": "application/json"
}

payload = {
    "title": "SEO Dry Test Run",
    "prompt": "Identify any SEO problems on https://naroagutierrezgil.com.",
    "sourceContext": {
        "source": "sources/github/borjamoskv/Cortex-Persist",
        "githubRepoContext": {
            "startingBranch": "main"
        }
    },
    "automationMode": "AUTO_CREATE_PR"
}

url = f"{base}/sessions"
try:
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print("Status Code:", r.status_code)
    print("Response JSON:")
    print(r.json())
except Exception as e:
    print("Failed POST:", e)
