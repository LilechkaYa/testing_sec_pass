import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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
    
    # 1. GET the login page to grab the hidden CSRF token
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        
        csrf_input = soup.find('input', {'name': 'YII_CSRF_TOKEN'})
        if not csrf_input:
            print("[Error] Could not find YII_CSRF_TOKEN on login page.")
            return False
        
        csrf_token = csrf_input['value']

        # 2. Build the payload
        payload = {
            'YII_CSRF_TOKEN': csrf_token,
            'LoginForm[username]': user,
            'LoginForm[password]': pw,
            'yt0': 'Login'
        }

        # 3. POST the login data
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
    
    # --- SESSION CACHE LOGIC ---
    # Only login if we haven't already in this container's lifetime
    if not _LOGGED_IN:
        if not login_to_portal():
            return None
    else:
        print(f"[Requests] Reusing existing session for server {server_id}", flush=True)

    # URL 1: Server Info
    info_url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
    info_res = session.get(info_url, timeout=10)
    
    # AUTO-RETRY: If the session expired, the portal redirects to login page
    if "LoginForm" in info_res.text:
        print("[Requests] Session expired. Re-authenticating...")
        _LOGGED_IN = False
        return fetch_portal_config(server_id) # Recursive call to re-login and try again

    # URL 2: Audit Data
    audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
    audit_res = session.get(audit_url, timeout=10)

    return {
        "ns1": get_td_value_from_html(info_res.text, "Label"),
        "dedicatedip": get_td_value_from_html(info_res.text, "Production IPv4"),
        "cpu": get_td_value_from_html(audit_res.text, "CPU Label", key_in_th=False),
        "ram": get_td_value_from_html(audit_res.text, "Total RAM", key_in_th=False),
        "disks": get_td_value_from_html(audit_res.text, "Total Storage", key_in_th=False),
        "server_id": server_id 
    }
