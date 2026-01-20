import requests
import base64
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime, timedelta

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
# Check last 2 hours
since = int((datetime.now() - timedelta(hours=2)).timestamp() * 1000)
url = f"https://localhost:31001/api/v1/namespaces/guest/activations?since={since}&limit=200"
headers = {
    "Authorization": f"Basic {AUTH_TOKEN}"
}

try:
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        activations = response.json()
        print(f"Found {len(activations)} activations since {datetime.fromtimestamp(since/1000.0)}")
        for act in activations:
            start_time = act.get('start', 0) / 1000.0
            dt = datetime.fromtimestamp(start_time)
            print(f"ID: {act['activationId']}, Action: {act['name']}, Status: {act.get('statusCode', 'N/A')}, Time: {dt}")
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
