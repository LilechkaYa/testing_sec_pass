import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor # Needed for parallel speed

load_dotenv()

# We use a session so that the login cookies persist in memory
session = requests.Session()
_LOGGED_IN = False  # Track login state globally within the container

def login_to_portal():
    global _LOGGED_IN
    url = os.environ["LOGIN_URL"]
    user = os.environ["PORTAL_USER"]
    pw = os.environ["PORTAL_PASS"]

    print("[Requests] Attempting fresh login...", flush=True)
    
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        
        csrf_input = soup.find('input', {'name': 'YII_CSRF_TOKEN'})
        if not csrf_input:
            print("[Error] Could not find YII_CSRF_TOKEN on login page.")
            return False
        
        csrf_token = csrf_input['value']

        payload = {
            'YII_CSRF_TOKEN': csrf_token,
            'LoginForm[username]': user,
            'LoginForm[password]': pw,
            'yt0': 'Login'
        }

        login_response = session.post(url, data=payload, timeout=10)
        
        if "logout" in login_response.text.lower():
            print("[Requests] Successfully logged into portal.")
            _LOGGED_IN = True
            return True
        else:
            print("[Requests] Login failed. Check credentials.")
            return False
    except Exception as e:
        print(f"[Requests] Login Error: {e}")
        return False

def get_td_value_from_html(html, key, key_in_th=True):
    soup = BeautifulSoup(html, 'lxml')
    try:
        if key_in_th:
            target = soup.find('th', string=lambda t: t and key in t)
            return target.find_next_sibling('td').get_text(strip=True)
        else:
            target = soup.find('td', string=lambda t: t and key in t)
            return target.find_next_sibling('td').get_text(strip=True)
    except Exception:
        return "N/A"

def fetch_portal_config(server_id: str):
    global _LOGGED_IN
    
    if not _LOGGED_IN:
        if not login_to_portal():
            return None
    else:
        print(f"[Requests] Reusing existing session for server {server_id}", flush=True)

    # URLs to fetch
    info_url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
    audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"

    # --- PARALLEL FETCHING START ---
    # Fetching both URLs at the same time cuts wait time in half
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        future_info = executor.submit(session.get, info_url, timeout=10)
        future_audit = executor.submit(session.get, audit_url, timeout=10)
        
        # Get results
        info_res = future_info.result()
        audit_res = future_audit.result()
    # --- PARALLEL FETCHING END ---

    # AUTO-RETRY: If the session expired
    if "LoginForm" in info_res.text or "LoginForm" in audit_res.text:
        print("[Requests] Session expired. Re-authenticating...")
        _LOGGED_IN = False
        return fetch_portal_config(server_id)

    return {
        "ns1": get_td_value_from_html(info_res.text, "Label"),
        "dedicatedip": get_td_value_from_html(info_res.text, "Production IPv4"),
        "cpu": get_td_value_from_html(audit_res.text, "CPU Label", key_in_th=False),
        "ram": get_td_value_from_html(audit_res.text, "Total RAM", key_in_th=False),
        "disks": get_td_value_from_html(audit_res.text, "Total Storage", key_in_th=False),
        "server_id": server_id 
    }
