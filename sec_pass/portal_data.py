import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# --- 1. Load Environment Variables ---
load_dotenv()

def login_to_portal(keep_browser_open: bool = False):
    """
    Handles credentials fetching, driver setup, and login in Headless mode
    using system-installed Chromium.
    """
    try:
        url = os.environ["LOGIN_URL"]
        user = os.environ["PORTAL_USER"]
        pw = os.environ["PORTAL_PASS"]
    except KeyError as e:
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        sys.exit(1)

    options = Options()
    # Headless flags for Linux/Container stability
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Path to the Chromium binary installed via apt-get
    options.binary_location = "/usr/bin/chromium"

    # Use the ChromeDriver binary installed via apt-get (usually /usr/bin/chromedriver)
    # This replaces ChromeDriverManager().install()
    service = ChromeService(executable_path="/usr/bin/chromedriver")
    
    print(f"[Selenium] Starting Headless Chromium...")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        print(f"[Selenium] Navigating to login portal...")
        driver.get(url)
        
        # Increased timeout to 15s for slower server environments
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "LoginForm_username"))
        )
        
        driver.find_element(By.ID, "LoginForm_username").send_keys(user)
        driver.find_element(By.ID, "LoginForm_password").send_keys(pw)
        driver.find_element(By.NAME, "yt0").click()
        
        WebDriverWait(driver, 15).until(EC.url_changes(url))
        
        print("[Selenium] Login successful.")
        return driver

    except Exception as e:
        print(f"Login failed: {e}")
        if driver:
            driver.quit()
        return None

def get_td_value_generic(driver, key, key_in_th=True):
    """Extracts text from a table based on a key string."""
    try:
        if key_in_th:
            td_element = driver.find_element(By.XPATH, f"//tr[th[contains(., '{key}')]]/td")
        else:
            td_element = driver.find_element(By.XPATH, f"//tr[td[contains(., '{key}')]]/td[2]")
        return td_element.text.strip()
    except Exception:
        return None

def get_server_data(server_id: str, driver):
    """
    The core scraping logic. Navigates to Info and Audit pages.
    """
    if not driver:
        return None

    try:
        # --- 1. Server info page ---
        info_url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
        driver.get(info_url)

        # Wait for the table row to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(., 'Production IPv4')]]"))
        )

        ipv4 = get_td_value_generic(driver, "Production IPv4", key_in_th=True)
        label = get_td_value_generic(driver, "Label", key_in_th=True)

        # --- 2. Audit page ---
        audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
        driver.get(audit_url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[td[contains(., 'CPU Label')]]"))
        )

        cpu = get_td_value_generic(driver, "CPU Label", key_in_th=False)
        ram = get_td_value_generic(driver, "Total RAM", key_in_th=False)
        disks = get_td_value_generic(driver, "Total Storage", key_in_th=False)

        return {
            "ns1": label,
            "dedicatedip": ipv4,
            "cpu": cpu,
            "ram": ram,
            "disks": disks,
            "server_id": server_id 
        }

    except Exception as e:
        print(f"[Error] Scraping failed for {server_id}: {e}")
        return None

def fetch_portal_config(server_id: str):
    """
    ENTRY POINT FOR EXTERNAL MODULES.
    """
    print(f"--- Fetching Portal Config for Server {server_id} ---")
    
    driver = login_to_portal(keep_browser_open=False)
    
    if driver:
        try:
            config = get_server_data(server_id, driver)
            return config
        finally:
            # Critical for Linux: Always kill the process
            driver.quit()
    return None
