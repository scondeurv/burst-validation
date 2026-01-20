import requests
import json
import warnings
import time
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
OW_HOST = "localhost"
OW_PORT = 31001

def check_recent_lp_activations():
    url = f"https://{OW_HOST}:{OW_PORT}/api/v1/namespaces/guest/activations"
    headers = {
        "Authorization": f"Basic {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Current time in ms since epoch
    now_ms = int(time.time() * 1000)
    one_hour_ago_ms = now_ms - (3600 * 1000)
    
    print(f"Checking labelpropagation activations since: {time.ctime(one_hour_ago_ms / 1000)}")
    
    try:
        # OpenWhisk API supports 'since' parameter in ms
        params = {
            "limit": 50,
            "since": one_hour_ago_ms
        }
        response = requests.get(url, headers=headers, verify=False, params=params)
        
        if response.status_code == 200:
            activations = response.json()
            # Filter by name
            lp_activations = [a for a in activations if a.get('name') == 'labelpropagation']
            
            if not lp_activations:
                print("No labelpropagation activations found in the last hour.")
                return

            print(f"{'Activation ID':<35} | {'Status':<15} | {'Start Time':<25} | {'Duration':<10}")
            print("-" * 95)
            
            for act in lp_activations:
                act_id = act.get('activationId')
                start_time = time.ctime(act.get('start', 0) / 1000)
                
                # Fetch details for status
                detail_url = f"{url}/{act_id}"
                detail_resp = requests.get(detail_url, headers=headers, verify=False)
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    status = "Success" if detail.get('response', {}).get('success') else "Failure"
                    duration = detail.get('duration', 'N/A')
                    print(f"{act_id:<35} | {status:<15} | {start_time:<25} | {duration:<10}")
                else:
                    print(f"{act_id:<35} | {'Unknown':<15} | {start_time:<25} | {'N/A':<10}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_recent_lp_activations()
