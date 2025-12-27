import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter

load_dotenv()

# --- NEW: SECRET LOADER HELPER ---
def get_secret(key, default=None):
    """
    Checks for a Docker Secret file first, then falls back to an Environment Variable.
    """
    secret_path = f"/run/secrets/{key}"
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()  # .strip() handles hidden \n characters
    return os.environ.get(key, default)

# --- NETWORK OPTIMIZATION ---
session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
session.mount('https://', adapter)

_LOGGED_IN = False 

def login_to_portal():
    global _LOGGED_IN
    # Use get_secret instead of os.environ
    url = get_secret("LOGIN_URL")
    user = get_secret("PORTAL_USER")
    pw = get_secret("PORTAL_PASS")

    if not url or not user or not pw:
        print("Error: Missing credentials for Portal login.")
        return False

    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        csrf_input = soup.find('input', {'name': 'YII_CSRF_TOKEN'})
        if not csrf_input: return False
        
        payload = {
            'YII_CSRF_TOKEN': csrf_input['value'],
            'LoginForm[username]': user,
            'LoginForm[password]': pw,
            'yt0': 'Login'
        }
        login_response = session.post(url, data=payload, timeout=10)
        
        if "logout" in login_response.text.lower():
            _LOGGED_IN = True
            return True
        return False
    except Exception as e:
        print(f"Login Error: {e}")
        return False

# ... (extract_value remains the same)

def fetch_portal_config(server_id: str):
    global _LOGGED_IN
    
    if not _LOGGED_IN and not login_to_portal():
        return None

    # Use the Config Base URL from environment (non-sensitive)
    base_url = os.environ.get("CONFIG_BASE_URL", "https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/")
    info_url = f"{base_url}{server_id}/"
    
    # Example: you might want to separate the Audit URL base too
    audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_info = executor.submit(session.get, info_url, timeout=10)
        f_audit = executor.submit(session.get, audit_url, timeout=10)
        info_res = f_info.result()
        audit_res = f_audit.result()

    if "LoginForm" in info_res.text or "LoginForm" in audit_res.text:
        _LOGGED_IN = False
        return fetch_portal_config(server_id)

    info_soup = BeautifulSoup(info_res.text, 'lxml')
    audit_soup = BeautifulSoup(audit_res.text, 'lxml')

    # Get selectors from Env (non-sensitive)
    info_sel = os.environ.get("INFO_SELECTOR", "Label") # Defaulting to your previous string
    
    config = {
        "ns1": extract_value(info_soup, "Label"),
        "dedicatedip": extract_value(info_soup, "Production IPv4"),
        "cpu": extract_value(audit_soup, "CPU Label", key_in_th=False),
        "ram": extract_value(audit_soup, "Total RAM", key_in_th=False),
        "disks": extract_value(audit_soup, "Total Storage", key_in_th=False),
        "last_update": extract_value(audit_soup, "Last Update", key_in_th=False),
        "server_id": server_id 
    }
    
    return config

