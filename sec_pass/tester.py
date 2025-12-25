import requests
import json
import os
import sys
import re
from dotenv import load_dotenv
import urllib3
from sec_pass.portal_data import fetch_portal_config

# Suppress the SSL warning for development/testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# --- 1. API CREDENTIALS ---
def get_api_credentials():
    try:
        return {
            "WHMCS_API_URL": os.environ["WHMCS_API_URL"],
            "API_IDENTIFIER": os.environ["WHMCS_API_IDENTIFIER"],
            "API_SECRET": os.environ["WHMCS_API_SECRET"],
        }
    except KeyError as e:
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        sys.exit(1)

API_CREDENTIALS = get_api_credentials()
WHMCS_API_URL = API_CREDENTIALS["WHMCS_API_URL"]
API_IDENTIFIER = API_CREDENTIALS["API_IDENTIFIER"]
API_SECRET = API_CREDENTIALS["API_SECRET"]

server_id = None
API_PAYLOAD = {
    'action': 'GetClientsProducts',
    'identifier': API_IDENTIFIER,
    'secret': API_SECRET,
    'responsetype': 'json',
    'domain': server_id
}

def set_server_id(sid):
    global server_id
    server_id = sid
    API_PAYLOAD['domain'] = sid

# --- HELPER FUNCTIONS ---

def normalize_ns1(value):
    if not value: return ""
    return str(value).split("_", 1)[0].lower().strip()

def normalize_ram(value):
    if not value: return ""
    match = re.search(r"(\d+)", str(value))
    return f"{match.group(1)}g" if match else ""

def normalize_cpu(value):
    """
    Simplifies CPU strings to just the model name.
    Example: 'AMD Ryzen 5 7600 @ 3.8GHz' -> 'amd ryzen 5 7600'
    """
    if not value: return ""
    val = str(value).lower()
    # Remove everything after '@' or '(' 
    val = re.split(r'[@\(\)]', val)[0]
    # Remove common filler words to keep the core model
    val = val.replace("processor", "").replace("cpu", "").strip()
    return " ".join(val.split())

def normalize_disks(value):
    """
    Converts disk strings to a numeric GB total.
    Handles '2x 960' and '2x 2TB' (Multiplies by 1000 for TB).
    """
    if not value: return 0
    val = str(value).lower()
    
    multiplier = 1
    mult_match = re.search(r"(\d+)\s*x", val)
    if mult_match:
        multiplier = int(mult_match.group(1))
    
    # Extract number and unit (GB or TB)
    size_match = re.search(r"(\d+(?:\.\d+)?)\s*(tb|gb)?", val)
    if not size_match:
        digits = re.search(r"(\d+)", val)
        return int(digits.group(1)) if digits else 0

    size_val = float(size_match.group(1))
    unit = size_match.group(2)

    if unit == 'tb':
        size_val *= 1000 # Using 1000 for disk manufacturer math
    
    return int(multiplier * size_val)

def get_config_option_value(whmcs_product, name_key):
    config_list = whmcs_product.get('configoptions', {}).get('configoption', [])
    if isinstance(config_list, dict):
        config_list = [config_list]
    for option in config_list:
        if option.get('option', '').lower() == name_key.lower():
            return option.get('value', 'N/A')
    return "N/A"

def analyze_and_compare(whmcs_data, local_config):
    discrepancies = {}
    product_list = whmcs_data.get('products', {}).get('product', [])
    if not product_list:
        print("❌ ERROR: No active product found in WHMCS.")
        return

    whmcs_product = product_list[0]
    ns1_value = whmcs_product.get('ns1', 'N/A')
    
    server_type = "VIRTUAL" if ns1_value.lower().startswith("hv") else "DEDICATED"
    fields = ["ns1", "dedicatedip"] if server_type == "VIRTUAL" else ["ns1", "dedicatedip", "cpu", "ram", "disks"]

    print(f"\n--- CONFIGURATION AUDIT: {server_id} ({server_type}) ---")
    print("-" * 50)

    for field in fields:
        local_val = local_config.get(field, 'N/A')
        whmcs_val = whmcs_product.get(field, 'N/A') if field in ["ns1", "dedicatedip"] else get_config_option_value(whmcs_product, field)

        is_match = False
        if field == "ns1":
            is_match = normalize_ns1(whmcs_val) == normalize_ns1(local_val)
        elif field == "ram":
            is_match = normalize_ram(whmcs_val) == normalize_ram(local_val)
        elif field == "cpu":
            # Check if one CPU string contains the other to handle varying detail levels
            whmcs_cpu = normalize_cpu(whmcs_val)
            local_cpu = normalize_cpu(local_val)
            is_match = (whmcs_cpu in local_cpu or local_cpu in whmcs_cpu)
        elif field == "disks":
            w_disk = normalize_disks(whmcs_val)
            l_disk = normalize_disks(local_val)
            # 10% tolerance for formatting/RAID overhead
            is_match = (l_disk >= w_disk * 0.9) if w_disk > 0 else (l_disk == w_disk)
        else:
            is_match = str(whmcs_val).lower().strip() == str(local_val).lower().strip()

        if not is_match:
            discrepancies[field] = {"local": local_val, "whmcs": whmcs_val}
            print(f"🚨 DISCREPANCY on {field.upper()}: Portal='{local_val}', WHMCS='{whmcs_val}'")
        else:
            print(f"✅ OK: {field.upper()} matches ('{local_val}')")

    print("-" * 50)
    if not discrepancies:
        print("🎉 RESULT: All fields match!")
    else:
        print(f"⚠️ RESULT: Found {len(discrepancies)} critical discrepancies.")

def make_whmcs_request():
    if not server_id: return
    print(f"\n--- Connecting to WHMCS API ---")
    try:
        response = requests.post(WHMCS_API_URL, data=API_PAYLOAD, timeout=20, verify=False)
        data = response.json()
        if data.get('result') == 'error' or data.get('totalresults', 0) == 0:
            print("❌ API Error or No Results.")
            return

        local_config = fetch_portal_config(server_id)
        if local_config:
            analyze_and_compare(data, local_config)
    except Exception as e:
        print(f"🚨 CONNECTION ERROR: {e}")

if __name__ == "__main__":
    make_whmcs_request()
