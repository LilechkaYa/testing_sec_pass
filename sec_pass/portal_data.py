import os
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter

load_dotenv()

# --- 1. SECRET LOADER ---
def get_secret(key, default=None):
    """Checks for a Docker Secret file first, then falls back to Env."""
    secret_path = f"/run/secrets/{key}"
    if os.path.exists(secret_path):
        try:
            with open(secret_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error reading secret {key}: {e}")
    return os.environ.get(key, default)

# --- 2. NETWORK OPTIMIZATION ---
session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
session.mount('https://', adapter)

_LOGGED_IN = False 

def login_to_portal():
    global _LOGGED_IN
    url = get_secret("LOGIN_URL")
    user = get_secret("PORTAL_USER")
    pw = get_secret("PORTAL_PASS")

    if not url or not user or not pw:
        print("🚨 FATAL: Portal credentials (LOGIN_URL, USER, PASS) missing.")
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

def extract_value(soup, key, key_in_th=True):
    try:
        tag = 'th' if key_in_th else 'td'
        # Improved lambda to handle both exact and partial matches
        target = soup.find(tag, string=lambda t: t and key.lower() in t.get_text().lower())
        if target:
            val = target.find_next_sibling('td').get_text(" ", strip=True)
            return val
        return "N/A"
    except:
        return "N/A"

def extract_raid_state_from_ajax(html):
    """Parses RAID state integer from /admin/auditor/DeviceDetails/{id}"""
    try:
        soup = BeautifulSoup(html, "lxml")
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2 and "raid" in cells[0].get_text(strip=True).lower():
                text = cells[1].get_text(" ", strip=True).lower()
                match = re.search(r"state:\s*(\d+)", text)
                return match.group(1) if match else "N/A"
        return "N/A"
    except:
        return "N/A"

def fetch_portal_config(server_id: str):
    global _LOGGED_IN
    
    if not _LOGGED_IN and not login_to_portal():
        return None

    info_url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
    audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
    raid_url = f"https://portal.simplyhosting.com/admin/auditor/DeviceDetails/{server_id}"

    # Increased workers to 3 to handle the new RAID AJAX call
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_info = executor.submit(session.get, info_url, timeout=10)
        f_audit = executor.submit(session.get, audit_url, timeout=10)
        f_raid = executor.submit(session.get, raid_url, timeout=10)
        
        info_res = f_info.result()
        audit_res = f_audit.result()
        raid_res = f_raid.result()

    if "LoginForm" in info_res.text or "LoginForm" in audit_res.text:
        _LOGGED_IN = False
        return fetch_portal_config(server_id)

    info_soup = BeautifulSoup(info_res.text, 'lxml')
    audit_soup = BeautifulSoup(audit_res.text, 'lxml')

    config = {
        "ns1": extract_value(info_soup, "Label"),
        "dedicatedip": extract_value(info_soup, "Production IPv4"),
        "cpu": extract_value(audit_soup, "CPU Label", key_in_th=False),
        "ram": extract_value(audit_soup, "Total RAM", key_in_th=False),
        "disks": extract_value(audit_soup, "Total Storage", key_in_th=False),
        "last_update": extract_value(audit_soup, "Last Update", key_in_th=False),
        "raid": extract_raid_state_from_ajax(raid_res.text),
        "server_id": server_id 
    }
    
    return config
