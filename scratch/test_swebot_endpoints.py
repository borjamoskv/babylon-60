import base64
import json
import requests
import subprocess

try:
    cmd_out = subprocess.check_output(
        ["security", "find-generic-password", "-s", "jules-cli", "-a", "default", "-w"],
        text=True
    ).strip()
except Exception as e:
    print("Failed to get keychain password:", e)
    cmd_out = ""

if cmd_out.startswith("go-keyring-base64:"):
    b64_part = cmd_out.split("go-keyring-base64:")[1]
    decoded_bytes = base64.b64decode(b64_part)
    token_data = json.loads(decoded_bytes.decode("utf-8"))
    access_token = token_data.get("access_token")
    
    base = "https://aida.googleapis.com/v1/swebot"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    endpoints = [
        "tasks",
        "sessions",
        "sources/github/borjamoskv/Cortex-Persist",
        "sources/github/borjamoskv/Cortex-Persist/tasks",
        "sources/github/borjamoskv/Cortex-Persist/sessions",
    ]
    
    for ep in endpoints:
        url = f"{base}/{ep}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"GET {ep} -> Status: {r.status_code}")
            if r.status_code == 200:
                print("Success JSON keys:", list(r.json().keys()))
                # If there are items, print them
                for k, v in r.json().items():
                    if isinstance(v, list):
                        print(f"  {k} count: {len(v)}")
                        if len(v) > 0:
                            print(f"  First {k}:", v[0])
            else:
                print("Error text:", r.text[:300])
        except Exception as e:
            print(f"GET {ep} Failed: {e}")
else:
    print("Keychain entry not found or invalid.")
