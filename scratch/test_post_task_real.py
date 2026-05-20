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
        "Content-Type": "application/json",
    }
    
    payload = {
        "title": "C4-SIMULATION connection check",
        "description": "Please run a simple verification that you can read this prompt and reply with success. Do not make any edits.",
        "sourceId": "github/borjamoskv/Cortex-Persist"
    }
    
    url = f"{base}/tasks"
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"POST tasks -> Status: {r.status_code}")
        print("Response JSON:", r.json() if r.status_code in (200, 201) else r.text)
    except Exception as e:
        print(f"POST tasks Failed: {e}")
else:
    print("Keychain entry not found or invalid.")
