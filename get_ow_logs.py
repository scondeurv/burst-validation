import requests
import json
import warnings
import sys
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
OW_HOST = "localhost"
OW_PORT = 31001

def get_activation_logs(activation_id):
    url = f"https://{OW_HOST}:{OW_PORT}/api/v1/namespaces/guest/activations/{activation_id}"
    headers = {
        "Authorization": f"Basic {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            print(f"Activation: {activation_id}")
            print(f"Action: {data.get('name')}")
            print(f"Status: {'Success' if data.get('response', {}).get('success') else 'Failure'}")
            print(f"Response: {json.dumps(data.get('response', {}).get('result'), indent=2)}")
            print("\nLogs:")
            for log in data.get('logs', []):
                print(log)
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_activation_logs(sys.argv[1])
    else:
        print("Please provide an activation ID")
