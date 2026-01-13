import requests
import json
import base64

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
activation_id = "aea9eb7daa294031a9eb7daa29a03192"
host = "localhost"
port = 31001

url = f"https://{host}:{port}/api/v1/namespaces/guest/activations/{activation_id}"
headers = {
    "Authorization": f"Basic {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers, verify=False)
if response.status_code == 200:
    data = response.json()
    print("Activation Result:")
    print(json.dumps(data.get("response", {}), indent=2))
    print("\nActivation Logs:")
    for line in data.get("logs", []):
        print(line)
else:
    print(f"Error fetching activation: {response.status_code}")
    print(response.text)
