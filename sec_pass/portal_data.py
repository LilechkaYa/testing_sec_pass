import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager 

# --- 1. Load Environment Variables ---
load_dotenv()

def login_to_portal(keep_browser_open: bool = True):
    """
    Handles credentials fetching, driver setup, and login.
    Returns the live WebDriver object on success.
    """
    try:
        url = os.environ["LOGIN_URL"]
        user = os.environ["PORTAL_USER"]
        pw = os.environ["PORTAL_PASS"]
    except KeyError as e:
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        sys.exit(1)

    options = Options()
    if keep_browser_open:
        options.add_experimental_option("detach", True)
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print(f"[Selenium] Navigating to login portal...")
    
    try:
        driver.get(url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "LoginForm_username"))
        )
        
        driver.find_element(By.ID, "LoginForm_username").send_keys(user)
        driver.find_element(By.ID, "LoginForm_password").send_keys(pw)
        driver.find_element(By.NAME, "yt0").click()
        
        WebDriverWait(driver, 10).until(EC.url_changes(url))
        
        print("[Selenium] Login successful.")
        return driver

    except Exception as e:
        print(f"Login failed: {e}")
        if driver:
            driver.quit()
        return None

def get_td_value_generic(driver, key, key_in_th=True):
    try:
        if key_in_th:
            td_element = driver.find_element(By.XPATH, f"//tr[th[contains(., '{key}')]]/td")
        else:
            td_element = driver.find_element(By.XPATH, f"//tr[td[contains(., '{key}')]]/td[2]")
        return td_element.text.strip()
    except:
        return None

def get_server_data(server_id: str, driver=None):
    """
    Navigates through portal pages and assembles the PORTAL_SERVER_CONFIG.
    """
    close_driver = False
    if not driver:
        driver = login_to_portal(keep_browser_open=False) 
        close_driver = True

    if not driver:
        return None

    try:
        # --- 1. Server info page ---
        url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(., 'Production IPv4')]]/td"))
        )

        ipv4 = get_td_value_generic(driver, "Production IPv4", key_in_th=True)
        label = get_td_value_generic(driver, "Label", key_in_th=True)

        # --- 2. Audit page ---
        audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
        driver.get(audit_url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[td[contains(., 'CPU Label')]]/td[2]"))
        )

        cpu = get_td_value_generic(driver, "CPU Label", key_in_th=False)
        ram = get_td_value_generic(driver, "Total RAM", key_in_th=False)
        disks = get_td_value_generic(driver, "Total Storage", key_in_th=False)

        PORTAL_SERVER_CONFIG = {
            "ns1": label,
            "dedicatedip": ipv4,
            "cpu": cpu,
            "ram": ram,
            "disks": disks,
            "server_id": server_id 
        }

        return PORTAL_SERVER_CONFIG

    except Exception as e:
        print(f"[Error] Scraping failed for {server_id}: {e}")
        return None
    finally:
        if close_driver and driver:
            driver.quit()

def fetch_portal_config(server_id: str):
    """
    THE ENTRY POINT FOR EXTERNAL MODULES.
    Call this function to get the PORTAL_SERVER_CONFIG dictionary.
    """
    print(f"--- Fetching Portal Config for Server {server_id} ---")
    
    # We log in once here
    driver = login_to_portal(keep_browser_open=True)
    
    if driver:
        config = get_server_data(server_id, driver=driver)
        return config
    return None