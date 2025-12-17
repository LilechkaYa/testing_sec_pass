import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Use WebDriver Manager to handle the correct Chrome driver version
from webdriver_manager.chrome import ChromeDriverManager 

# --- 1. Load Environment Variables ---
load_dotenv()

from selenium.webdriver.chrome.options import Options

def login_to_portal(keep_browser_open: bool = True):
    """
    Handles credentials fetching, driver setup, and login.
    Returns the live WebDriver object on success, or raises an Exception on failure.
    """
    # 1. Fetch credentials using os.environ (Fail-fast)
    try:
        url = os.environ["LOGIN_URL"]
        user = os.environ["PORTAL_USER"]
        pw = os.environ["PORTAL_PASS"]
    except KeyError as e:
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        sys.exit(1)

    # 2. Setup Driver with Options
    options = Options()
    if keep_browser_open:
        options.add_experimental_option("detach", True)
    
    # Initialize the driver
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print(f"[Selenium] Navigating to: {url}")
    
    try:
        # 3. Navigate and Wait
        driver.get(url)
        
        # Wait for the specific ID we found in your HTML
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "LoginForm_username"))
        )
        
        # 4. Enter Credentials
        driver.find_element(By.ID, "LoginForm_username").send_keys(user)
        driver.find_element(By.ID, "LoginForm_password").send_keys(pw)
        
        # 5. Click Login (using the name 'yt0' from your HTML)
        driver.find_element(By.NAME, "yt0").click()
        
        # 6. Verify Redirection
        WebDriverWait(driver, 10).until(EC.url_changes(url))
        
        print("[Selenium] Login successful. Returning live driver.")
        return driver  # driver returned for scraper

    except Exception as e:
        # If login fails, we SHOULD close the driver to prevent ghost processes
        print(f"Login failed: {e}")
        driver.quit()
        sys.exit(1)

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
    """Retrieve server data from the portal."""
    close_driver = False
    
    # 1. Use existing driver or create a new one using your updated function
    if not driver:
        # No arguments needed now as it uses os.environ internally
        driver = login_to_portal(keep_browser_open=False) 
        close_driver = True

    try:
        # --- Server info page ---
        url = f"https://portal.simplyhosting.com/admin/devicemanagement/device/info/id/{server_id}/"
        driver.get(url)

        # Wait for the Production IPv4 row to appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(., 'Production IPv4')]]/td"))
        )

        results_dict_portal = {
            "Server": server_id,
            "ipv4": get_td_value_generic(driver, "Production IPv4", key_in_th=True),
            "Label": get_td_value_generic(driver, "Label", key_in_th=True)
        }

        # --- Audit page ---
        audit_url = f"https://portal.simplyhosting.com/admin/devicemanagement/audit/get/deviceId/{server_id}/"
        driver.get(audit_url)

        # Wait for Audit page specific element
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//tr[td[contains(., 'CPU Label')]]/td[2]"))
        )

        for field in ["CPU Label", "Total RAM", "Total Storage"]:
            results_dict_portal[field] = get_td_value_generic(driver, field, key_in_th=False)

        return results_dict_portal

    except Exception as e:
        print(f"[Error] Failed to scrape server {server_id}: {e}")
        return None

    finally:
        # Only close if this function was the one that opened the driver
        if close_driver and driver:
            driver.quit()

def main():
    """
    Entry point: Log in and scrape data for a single specific server.
    """
    driver = None
    # Replace this with your actual target Server ID
    target_server_id = "29305" 
    
    try:
        print(f"--- Starting Portal Session for Server {target_server_id} ---")
        
        # 1. Login and get the live driver
        # keep_browser_open=True allows you to see the result after the script ends
        driver = login_to_portal(keep_browser_open=True)
        
        # 2. Extract data for the single server
        # We pass the authenticated driver directly to the scraper
        print(f"Fetching data...")
        server_data = get_server_data(target_server_id, driver=driver)
        
        # 3. Output the result
        print("\n--- Scraped Data ---")
        if server_data:
            for key, value in server_data.items():
                print(f"{key}: {value}")
        else:
            print("Failed to retrieve data. Check the server ID or portal state.")

    except Exception as e:
        print(f"\n--- FATAL SCRIPT ERROR ---")
        print(f"The process failed: {e}")
    
    print("\nScript finished. Browser session remains active.")

if __name__ == "__main__":
    main()
