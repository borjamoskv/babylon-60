import subprocess
import requests

try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
except Exception as e:
    print("Could not get gcloud token:", e)
    token = ""

base = "https://jules.googleapis.com"
project = "forward-tape-489302-m7"

paths = [
    "/v1alpha/sources",
    "/v1alpha/sessions",
    f"/v1alpha/projects/{project}/sources",
    f"/v1alpha/projects/{project}/sessions",
    f"/v1alpha/projects/{project}/locations/global/sources",
    f"/v1alpha/projects/{project}/locations/global/sessions",
    f"/v1alpha/projects/{project}/locations/us-central1/sources",
    f"/v1alpha/projects/{project}/locations/us-central1/sessions",
]

headers = {
    "Authorization": f"Bearer {token}",
    "x-goog-user-project": project
}

for path in paths:
    url = f"{base}{path}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"\nGET {url} -> Status: {r.status_code}")
        print(r.text[:300])
    except Exception as e:
        print(f"Failed {url}: {e}")
