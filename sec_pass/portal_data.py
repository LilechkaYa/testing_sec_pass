import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# We use a session so that the login cookies persist for subsequent data fetches
session = requests.Session()

def login_to_portal():
    url = os.environ["LOGIN_URL"]
    user = os.environ["PORTAL_USER"]
    pw = os.environ["PORTAL_PASS"]

    # 1. GET the login page to grab the hidden CSRF token
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Locate the YII_CSRF_TOKEN input field
    csrf_input = soup.find('input', {'name': 'YII_CSRF_TOKEN'})
    if not csrf_input:
        print("[Error] Could not find YII_CSRF_TOKEN on login page.")
        return False
    
    csrf_token = csrf_input['value']

    # 2. Build the payload exactly as seen in your Network tab
    payload = {
        'YII_CSRF_TOKEN': csrf_token,
        'LoginForm[username]': user,
        'LoginForm[password]': pw,
        'yt0': 'Login'
    }

    # 3. POST the login data
    login_response = session.post(url, data=payload)
    
    # Check if login was successful by looking for a 'logout' link in the response
    if "logout" in login_response.text.lower():
        print("[Requests] Successfully logged into portal.")
        return True
    else:
        print("[Requests] Login failed. Check credentials or portal status.")
        return False

def get_td_value_from_html(html, key, key_in_th=True):
    """Parses HTML table data using BeautifulSoup."""
    soup = BeautifulSoup(html, 'lxml')
    try:
        if key_in_th:
            # Look for <th> containing the key, then get the <td> next to it
            target = soup.find('th', string=lambda t: t and key in t)
            return target.find_next_sibling('td').get_text(strip=True)
        else:
            # Look for <td> containing the key, then get the 2nd <td> in that row
            target = soup.find('td', string=lambda t: t and key in t)
            return target.find_next_sibling('td').get_text(strip=True)
    except Exception:
        return "N/A"

def fetch_portal_config(server_id: str):
    """Main entry point: Logs in and fetches server info/audit data."""
    if not login_to_portal():
        return None

    # URL 1: Server Info
    info_url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
    info_html = session.get(info_url).text
    
    # URL 2: Audit Data
    audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
    audit_html = session.get(audit_url).text

    return {
        "ns1": get_td_value_from_html(info_html, "Label"),
        "dedicatedip": get_td_value_from_html(info_html, "Production IPv4"),
        "cpu": get_td_value_from_html(audit_html, "CPU Label", key_in_th=False),
        "ram": get_td_value_from_html(audit_html, "Total RAM", key_in_th=False),
        "disks": get_td_value_from_html(audit_html, "Total Storage", key_in_th=False),
        "server_id": server_id 
    }
