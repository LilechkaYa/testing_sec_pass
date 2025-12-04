import requests
import json
import os
import sys

# Import urllib3 to suppress the SSL warning if needed (good practice)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --- 1. LOCAL SERVER CONFIGURATION (The Source of Truth) ---
# NOTE: Populate these values with the exact data you expect WHMCS to return for the test server ID.
# Match the case and format (e.g., '16 GB', '8 Cores') from the WHMCS values.
LOCAL_SERVER_CONFIG = {
    # Keys for ALL server types
    "ns1": "D22_031",                  # Expected NS1 entry (e.g., dedicated or virtual identifier)
    "dedicatedip": "151.236.34.234",   # Expected Primary IP
    
    # Keys for DEDICATED servers only (configoptions - based on the 'option' key)
    # These must match the expected WHMCS configuration names and values.
    "cpu": "Default - 4-Core Intel Xeon E3-1240 v5 @ 3.5GHz",
    "ram": "Upgrade to 64GB DDR4",
    "disks": "Upgrade to 4x 500GB SSD",
}


# --- 2. SETUP AND CONFIGURATION ---
try:
    # Load API credentials securely from Docker environment variables (set via .env file)
    WHMCS_API_URL = os.environ["WHMCS_API_URL"]
    API_IDENTIFIER = os.environ["WHMCS_API_IDENTIFIER"]
    API_SECRET = os.environ["WHMCS_API_SECRET"]
except KeyError as e:
    print(f"FATAL ERROR: Environment variable {e} is not set.")
    sys.exit(1)

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
    
    # Ensure config_list is iterable (it can be a single dict or a list of dicts)
    if isinstance(config_list, dict):
        config_list = [config_list]
        
    for option in config_list:
        # Check against the 'option' key, which holds the configuration name (e.g., 'CPU', 'RAM')
        if option.get('option', '').lower() == name_key.lower():
            return option.get('value', 'N/A')
            
    return "N/A (Key Not Found)"


def analyze_and_compare(whmcs_data, local_config):
    """
    Parses WHMCS data, determines server type, and compares required fields.
    """
    discrepancies = {}
    
    # 1. Safely extract the primary product details
    product_list = whmcs_data.get('products', {}).get('product', [])
    if not product_list:
        print("❌ ERROR: No active product found for this domain/server ID in WHMCS.")
        return

    # Use the product with the 'Active' status if possible, otherwise use the first one.
    active_product = next((p for p in product_list if p.get('status') == 'Active'), product_list[0])
    whmcs_product = active_product 
    
    print(f"Comparing Product ID: {whmcs_product.get('id')} (Status: {whmcs_product.get('status', 'N/A')})")
    
    # 2. Determine Server Type and Define comparison keys
    ns1_value = whmcs_product.get('ns1', 'N/A')
    
    # Server type is determined by the 'hv' prefix in ns1, as requested.
    if ns1_value.lower().startswith("hv"):
        server_type = "VIRTUAL"
        # Virtual servers only check ns1 and dedicatedip
        fields_to_check = ["ns1", "dedicatedip"] 
    else:
        server_type = "DEDICATED"
        # Dedicated servers check all five keys
        fields_to_check = ["ns1", "dedicatedip", "cpu", "ram", "disks"]
        
    print(f"\n--- CONFIGURATION AUDIT: {server_id} (Type: {server_type}) ---")
    print("-" * 50)

    # 3. Iterate through fields and compare
    for field in fields_to_check:
        local_value = local_config.get(field, 'N/A')
        whmcs_value = 'N/A'

        if field in ["ns1", "dedicatedip"]:
            # Direct top-level fields
            whmcs_value = whmcs_product.get(field, 'N/A').strip(', ') 
        
        elif field in ["cpu", "ram", "disks"]:
            # Nested config option fields, looking up by the field name (e.g., 'cpu' maps to 'CPU' option)
            whmcs_value = get_config_option_value(whmcs_product, field)

        # Comparison Logic (case-insensitive and stripping whitespace for robustness)
        if str(whmcs_value).lower().strip() != str(local_value).lower().strip():
            discrepancies[field] = {
                "local": local_value,
                "whmcs": whmcs_value
            }
            print(f"🚨 DISCREPANCY on {field.upper()}: Local='{local_value}', WHMCS='{whmcs_value}'")
        else:
            print(f"✅ OK: {field.upper()} matches ('{local_value}')")

    if not discrepancies:
        print("-" * 50)
        print("🎉 RESULT: All required configuration fields match the local expectation!")
    else:
        print("-" * 50)
        print(f"⚠️ RESULT: Found {len(discrepancies)} critical discrepancies. Review WHMCS setup.")


# --- 4. MAIN EXECUTION ---
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
        response = requests.post(WHMCS_API_URL, data=API_PAYLOAD, timeout=20)
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
        analyze_and_compare(data, local_config=LOCAL_SERVER_CONFIG)

    except requests.exceptions.RequestException as e:
        print(f"🚨 CONNECTION ERROR: Failed to reach the WHMCS API.")
        print(f"Error details: {e}")
        print("\nACTION REQUIRED: Check URL and confirm CentOS IP is still whitelisted.")


if __name__ == "__main__":
    make_whmcs_request()
