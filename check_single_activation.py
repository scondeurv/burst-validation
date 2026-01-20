import requests
import base64
from urllib3.exceptions import InsecureRequestWarning
import json

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
activation_id = "58a288b2bc364fd9a288b2bc366fd96a"
url = f"https://localhost:31001/api/v1/namespaces/guest/activations/{activation_id}"
headers = {
    "Authorization": f"Basic {AUTH_TOKEN}"
}

try:
    response = requests.get(url, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
