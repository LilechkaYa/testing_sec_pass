import requests
import json
import os
import sys
import re
from dotenv import load_dotenv
import urllib3
# Ensure this import matches your file structure
from sec_pass.portal_data import fetch_portal_config, get_secret 

# Suppress the SSL warning for development/testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# --- 1. API CREDENTIALS (REVISED FOR SWARM) ---
def get_api_credentials():
    """
    Uses the shared get_secret logic to fetch WHMCS keys 
    from either Docker Secrets or Environment Variables.
    """
    creds = {
        "WHMCS_API_URL": get_secret("WHMCS_API_URL"),
        "API_IDENTIFIER": get_secret("WHMCS_API_IDENTIFIER"),
        "API_SECRET": get_secret("WHMCS_API_SECRET"),
    }
    
    # Check if any critical values are missing
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"FATAL ERROR: The following credentials are missing: {', '.join(missing)}")
        print("Ensure you have run 'docker secret create' for each or have a .env file.")
        sys.exit(1)
        
    return creds

API_CREDENTIALS = get_api_credentials()
WHMCS_API_URL = API_CREDENTIALS["WHMCS_API_URL"]
API_IDENTIFIER = API_CREDENTIALS["API_IDENTIFIER"]
API_SECRET = API_CREDENTIALS["API_SECRET"]

# Global payload - we use these variables rather than hardcoding
server_id = None
API_PAYLOAD = {
    'action': 'GetClientsProducts',
    'identifier': API_IDENTIFIER,
    'secret': API_SECRET,
    'responsetype': 'json',
    'domain': server_id
}

# ... [normalize_ns1, normalize_ram, normalize_cpu, normalize_disks remain the same] ...

# ... [get_config_option_value and analyze_and_compare remain the same] ...

def make_whmcs_request():
    if not server_id: 
        print("❌ No Server ID (Domain) provided.")
        return
        
    try:
        # verify=False used here as per your original code for internal/dev certs
        response = requests.post(WHMCS_API_URL, data=API_PAYLOAD, timeout=20, verify=False)
        data = response.json()
        
        if data.get('result') == 'error' or data.get('totalresults', 0) == 0:
            print(f"❌ API Error or No Results for Domain: {server_id}")
            return

        local_config = fetch_portal_config(server_id)
        if local_config:
            analyze_and_compare(data, local_config)
            
    except Exception as e:
        print(f"🚨 CONNECTION ERROR: {e}")

if __name__ == "__main__":
    # Example usage: check if an ID was passed via command line, otherwise use a placeholder
    # This makes it easier for DevOps to test the container manually
    target_id = sys.argv[1] if len(sys.argv) > 1 else "TEST_DOMAIN_OR_ID"
    set_server_id(target_id)
    make_whmcs_request()
