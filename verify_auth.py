import requests
import base64
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
url = "https://localhost:31001/api/v1/namespaces/guest/actions"
headers = {
    "Authorization": f"Basic {AUTH_TOKEN}"
}

try:
    response = requests.get(url, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        actions = response.json()
        print(f"Found {len(actions)} actions.")
        for action in actions:
            print(f"- {action['name']}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
