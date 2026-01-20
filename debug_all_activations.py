import requests
import json
import warnings
import time
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

AUTH_TOKEN = "MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
OW_HOST = "localhost"
OW_PORT = 31001

def check_recent_activations(hours=1):
    url = f"https://{OW_HOST}:{OW_PORT}/api/v1/namespaces/guest/activations"
    headers = {
        "Authorization": f"Basic {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Current time in ms since epoch
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (hours * 3600 * 1000)
    
    print(f"Checking ALL activations since: {time.ctime(since_ms / 1000)}")
    
    try:
        params = {
            "limit": 50,
            "since": since_ms
        }
        response = requests.get(url, headers=headers, verify=False, params=params)
        
        if response.status_code == 200:
            activations = response.json()
            if not activations:
                print(f"No activations found in the last {hours} hour(s).")
                return

            print(f"{'Activation ID':<35} | {'Action':<20} | {'Status':<10} | {'Start Time':<25}")
            print("-" * 100)
            
            for act in activations:
                act_id = act.get('activationId')
                name = act.get('name')
                start_time = time.ctime(act.get('start', 0) / 1000)
                
                # We can deduce status from 'statusCode' in the summary if present, 
                # but usually it needs a detail call. Let's do a detail call for the first few.
                status = "Wait..."
                print(f"{act_id:<35} | {name:<20} | {status:<10} | {start_time:<25}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_recent_activations(1)
    print("\n" + "="*50 + "\n")
    check_recent_activations(24) # Let's also check last 24h
