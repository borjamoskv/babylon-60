import requests

url = "http://127.0.0.0:8000/millennium-hit"

try:
    response = requests.post(
        "http://localhost:8000/millennium-hit",
        json={"id": 123, "t": 0.5, "magnitude": 0.05}
    )
    print(response.json())
except Exception as e:
    print(e)
