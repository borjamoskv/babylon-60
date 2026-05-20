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
    "x-goog-user-project": project
}

sources_to_try = [
    "sources/github/borjamoskv/Cortex-Persist",
    "sources/github/borjamoskv/cortex-persist",
    "sources/github-borjamoskv-Cortex-Persist",
    "sources/github-borjamoskv-cortex-persist"
]

for src in sources_to_try:
    url = f"{base}/{src}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"GET {url} -> Status: {r.status_code}")
        print(r.text[:300])
    except Exception as e:
        print(f"Failed {url}: {e}")
