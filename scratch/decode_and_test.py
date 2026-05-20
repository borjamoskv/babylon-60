import base64
import json
import requests
import subprocess

# Retrieve the credential string from keychain
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
    print("Decoded token data successfully.")
    print("Token keys:", list(token_data.keys()))
    print("Expiry:", token_data.get("expiry"))
    
    access_token = token_data.get("access_token")
    
    # Try calling aida/jules with this access token!
    bases = [
        "https://jules.googleapis.com/v1alpha",
        "https://aida.googleapis.com/v1/swebot",
    ]
    
    for base in bases:
        print(f"\n================ Base URL: {base} ================")
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        # Add user project for jules
        if "jules.googleapis.com" in base:
            headers["x-goog-user-project"] = "forward-tape-489302-m7"
            
        for path in ["sources", "sessions"]:
            url = f"{base}/{path}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                print(f"GET {path} -> Status: {r.status_code}")
                if r.status_code == 200:
                    print("Success! JSON keys:", list(r.json().keys()))
                    # Print list elements count
                    for k, v in r.json().items():
                        if isinstance(v, list):
                            print(f"  {k} count: {len(v)}")
                            if len(v) > 0:
                                print(f"  First {k}: {v[0]}")
                else:
                    print("Error text:", r.text[:300])
            except Exception as e:
                print(f"GET {path} Failed: {e}")
else:
    print(f"Unexpected keychain output: {cmd_out}")
