import requests
import json
import os
import sys
import re
from dotenv import load_dotenv
import urllib3
from portal_data import fetch_portal_config

# Suppress the SSL warning for development/testing if necessary
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION INITIALIZATION ---
load_dotenv()

# --- 1. API CREDENTIALS ---
def get_api_credentials():
    try:
        credentials = {
            "WHMCS_API_URL": os.environ["WHMCS_API_URL"],
            "API_IDENTIFIER": os.environ["WHMCS_API_IDENTIFIER"],
            "API_SECRET": os.environ["WHMCS_API_SECRET"],
        }
        return credentials
    except KeyError as e:
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        sys.exit(1)

API_CREDENTIALS = get_api_credentials()

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

# --- HELPER FUNCTIONS ---

def normalize_ns1(value):
    """Compare only the part before '_'"""
    if not value:
        return ""
    return str(value).split("_", 1)[0].lower().strip()


def normalize_ram(value):
    """
    Normalizes RAM values to '<number>g'
    Examples:
      64G -> 64g
      64GB -> 64g
      64GB DDR5 -> 64g
    """
    if not value:
        return ""

    match = re.search(r"(\d+)", str(value))
    if not match:
        return ""

    return f"{match.group(1)}g"


def get_config_option_value(whmcs_product, name_key):
    config_list = whmcs_product.get('configoptions', {}).get('configoption', [])

    if isinstance(config_list, dict):
        config_list = [config_list]

    for option in config_list:
        if option.get('option', '').lower() == name_key.lower():
            return option.get('value', 'N/A')

    return "N/A (Key Not Found)"


def analyze_and_compare(whmcs_data, local_config):
    discrepancies = {}

    product_list = whmcs_data.get('products', {}).get('product', [])
    if not product_list:
        print("❌ ERROR: No active product found for this domain/server ID in WHMCS.")
        return

    whmcs_product = product_list[0]

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
        local_value = local_config.get(field, 'N/A')
        whmcs_value = 'N/A'

        if field in ["ns1", "dedicatedip"]:
            whmcs_value = whmcs_product.get(field, 'N/A').strip(', ')

        elif field in ["cpu", "ram", "disks"]:
            whmcs_value = get_config_option_value(whmcs_product, field)

        # --- NORMALIZED COMPARISON ---
        if field == "ns1":
            whmcs_compare = normalize_ns1(whmcs_value)
            local_compare = normalize_ns1(local_value)

        elif field == "ram":
            whmcs_compare = normalize_ram(whmcs_value)
            local_compare = normalize_ram(local_value)

        else:
            whmcs_compare = str(whmcs_value).lower().strip()
            local_compare = str(local_value).lower().strip()

        if whmcs_compare != local_compare:
            discrepancies[field] = {
                "local": local_value,
                "whmcs": whmcs_value
            }
            print(f"🚨 DISCREPANCY on {field.upper()}: Portal='{local_value}', WHMCS='{whmcs_value}'")
        else:
            print(f"✅ OK: {field.upper()} matches ('{local_value}')")

    if not discrepancies:
        print("-" * 50)
        print("🎉 RESULT: All required configuration fields match the local expectation!")
    else:
        print("-" * 50)
        print(f"⚠️ RESULT: Found {len(discrepancies)} critical discrepancies.")


# --- MAIN EXECUTION ---
def make_whmcs_request():
    if not server_id:
        print("ERROR: Domain Name cannot be empty.")
        return

    print(f"\n--- Attempting direct connection to WHMCS API ---")

    try:
        response = requests.post(
            WHMCS_API_URL,
            data=API_PAYLOAD,
            timeout=20,
            verify=False
        )
        response.raise_for_status()

        data = response.json()

        if data.get('result') == 'error':
            print(f"🚨 WHMCS API ERROR: {data.get('message', 'Unknown API Error')}")
            return

        if data.get('totalresults', 0) == 0:
            print(f"❌ SUCCESSFUL CONNECTION, but no results found for domain: {server_id}")
            return

        local_config = fetch_portal_config(server_id)
        if local_config is None:
            print("❌ ERROR: Failed to fetch portal configuration.")
            return

        analyze_and_compare(data, local_config=local_config)

    except requests.exceptions.RequestException as e:
        print(f"🚨 CONNECTION ERROR: Failed to reach the WHMCS API.")
        print(f"Error details: {e}")


if __name__ == "__main__":
    make_whmcs_request()

