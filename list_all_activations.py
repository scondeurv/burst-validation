import requests
import base64
from urllib3.exceptions import InsecureRequestWarning
import json

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
url = "https://localhost:31001/api/v1/namespaces/guest/activations?limit=100"
headers = {
    "Authorization": f"Basic {AUTH_TOKEN}"
}

try:
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        activations = response.json()
        print(f"Found {len(activations)} recent activations.")
        for act in activations:
            start_time = act.get('start', 0) / 1000.0
            from datetime import datetime
            dt = datetime.fromtimestamp(start_time)
            print(f"ID: {act['activationId']}, Action: {act['name']}, Status: {act.get('statusCode', 'N/A')}, Time: {dt}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
