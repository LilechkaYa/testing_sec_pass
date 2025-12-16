import requests
import json
import os
import sys
from dotenv import load_dotenv # <-- New Import!
import urllib3
from portal_data import PORTAL_SERVER_CONFIG 

# Suppress the SSL warning for development/testing if necessary
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION INITIALIZATION ---
# Load variables from the .env file into the environment (os.environ).
# This is safe because load_dotenv() won't override variables already set
# by a host environment (like Docker) or the shell itself.
load_dotenv() 

def get_api_credentials():
    """
    Retrieves and validates required API environment variables from os.environ.
    The source is either the .env file (local) or the Docker host (production).
    """
    try:
        credentials = {
            "WHMCS_API_URL": os.environ["WHMCS_API_URL"],
            "API_IDENTIFIER": os.environ["WHMCS_API_IDENTIFIER"],
            "API_SECRET": os.environ["WHMCS_API_SECRET"],
        }
        return credentials
    except KeyError as e:
        # Exit if any required variable is missing
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        print("ACTION: Ensure your local .env file is present and correctly populated.")
        sys.exit(1)


# --- 2. API CREDENTIALS LOADING ---
# Load and validate credentials right away. If any are missing, the script exits here.
API_CREDENTIALS = get_api_credentials()

# Map the credentials into the main variables for clearer use (optional, but clean)
WHMCS_API_URL = API_CREDENTIALS["WHMCS_API_URL"]
API_IDENTIFIER = API_CREDENTIALS["API_IDENTIFIER"]
API_SECRET = API_CREDENTIALS["API_SECRET"]


# --- Interactive Input ---
server_id = input("Enter the 5-digit Domain Number (server_id) to check: ")

# --- API Request Setup ---
API_PAYLOAD = {
    'action': 'GetClientsProducts',
    'identifier': API_IDENTIFIER,
    'secret': API_SECRET,
    'responsetype': 'json',
    'domain': server_id
}


# --- 3. COMPARISON LOGIC FUNCTIONS ---

def get_config_option_value(whmcs_product, name_key):
    """
    Safely extracts a value from the nested configoptions structure using the 'option' key.
    """
    config_list = whmcs_product.get('configoptions', {}).get('configoption', [])
    
    if isinstance(config_list, dict):
        config_list = [config_list]
        
    for option in config_list:
        if option.get('option', '').lower() == name_key.lower():
            return option.get('value', 'N/A')
            
    return "N/A (Key Not Found)"


def analyze_and_compare(whmcs_data, portal_config):
    """
    Parses WHMCS data, determines server type, and compares required fields.
    """
    discrepancies = {}
    
    product_list = whmcs_data.get('products', {}).get('product', [])
    if not product_list:
        print("❌ ERROR: No active product found for this domain/server ID in WHMCS.")
        return

    #active_product = next((p for p in product_list if p.get('status') == 'Active'), product_list[0])
    whmcs_product = product_list[0]
    
    #print(f"Comparing Product ID: {whmcs_product.get('id')} (Status: {whmcs_product.get('status', 'N/A')})")
    
    ns1_value = whmcs_product.get('ns1', 'N/A')
    
    if ns1_value.lower().startswith("hv"):
        server_type = "VIRTUAL"
        fields_to_check = ["ns1", "dedicatedip"] 
    else:
        server_type = "DEDICATED"
        fields_to_check = ["ns1", "dedicatedip", "cpu", "ram", "disks"]
        
    print(f"\n--- CONFIGURATION AUDIT: {server_id} (Type: {server_type}) ---")
    print("-" * 50)

    for field in fields_to_check:
        portal_value = portal_config.get(field, 'N/A')
        whmcs_value = 'N/A'

        if field in ["ns1", "dedicatedip"]:
            whmcs_value = whmcs_product.get(field, 'N/A').strip(', ') 
        
        elif field in ["cpu", "ram", "disks"]:
            whmcs_value = get_config_option_value(whmcs_product, field)

        if str(whmcs_value).lower().strip() != str(portal_value).lower().strip():
            discrepancies[field] = {
                "portal": portal_value,
                "whmcs": whmcs_value
            }
            print(f"🚨 DISCREPANCY on {field.upper()}: Portal='{portal_value}', WHMCS='{whmcs_value}'")
        else:
            print(f"✅ OK: {field.upper()} matches ('{portal_value}')")

    if not discrepancies:
        print("-" * 50)
        print("🎉 RESULT: All required configuration fields match!")
    else:
        print("-" * 50)
        print(f"⚠️ RESULT: Found {len(discrepancies)} critical discrepancies. Please double check server configuration.")


# --- 4. MAIN EXECUTION (Unchanged) ---
def make_whmcs_request():
    """
    Handles the API request and error checking.
    """
    if not server_id:
        print("ERROR: Domain Name cannot be empty.")
        return

    print(f"\n--- Attempting direct connection to WHMCS API ---")

    try:
        # Make the API request
        # Note: 'verify=False' is used due to the urllib3 disable_warnings call above
        response = requests.post(WHMCS_API_URL, data=API_PAYLOAD, timeout=20, verify=False) 
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()

        if data.get('result') == 'error':
            error_message = data.get('message', 'Unknown API Error')
            print(f"🚨 WHMCS API ERROR: {error_message}")
            return
        
        if data.get('totalresults', 0) == 0:
            print(f"❌ SUCCESSFUL CONNECTION, but no results found for domain: {server_id}")
            return

        # Success: Start analysis and comparison
        analyze_and_compare(data, portal_config=PORTAL_SERVER_CONFIG)

    except requests.exceptions.RequestException as e:
        print(f"🚨 CONNECTION ERROR: Failed to reach the WHMCS API.")
        print(f"Error details: {e}")
        print("\nACTION REQUIRED: Check URL and confirm your current IP is still whitelisted by WHMCS.")


if __name__ == "__main__":
    make_whmcs_request()