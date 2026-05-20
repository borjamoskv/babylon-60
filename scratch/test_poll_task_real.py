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
    
    task_id = "1016391831427191244"
    url = f"{base}/tasks/{task_id}"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"GET task -> Status: {r.status_code}")
        if r.status_code == 200:
            print("Response JSON:")
            print(json.dumps(r.json(), indent=2))
        else:
            print("Error text:", r.text)
    except Exception as e:
        print(f"GET task Failed: {e}")
else:
    print("Keychain entry not found or invalid.")
