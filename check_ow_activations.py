import requests
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
OW_HOST = "localhost"
OW_PORT = 31001

def check_activations():
    url = f"https://{OW_HOST}:{OW_PORT}/api/v1/namespaces/guest/activations"
    headers = {
        "Authorization": f"Basic {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, params={"limit": 20})
        if response.status_code == 200:
            activations = response.json()
            print(f"{'Activation ID':<35} | {'Action':<25} | {'Status':<15} | {'Duration':<10}")
            print("-" * 95)
            for act in activations:
                # To get more details like status, we might need to fetch the activation itself or check the summary
                # The summary list usually has 'statusCode' in some versions or we might need to fetch details
                act_id = act.get('activationId')
                name = act.get('name')
                
                # Fetch details for status
                detail_url = f"{url}/{act_id}"
                detail_resp = requests.get(detail_url, headers=headers, verify=False)
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    status = "Success" if detail.get('response', {}).get('success') else "Failure"
                    duration = detail.get('duration', 'N/A')
                    print(f"{act_id:<35} | {name:<25} | {status:<15} | {duration:<10}")
                else:
                    print(f"{act_id:<35} | {name:<25} | {'Unknown':<15} | {'N/A':<10}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_activations()
