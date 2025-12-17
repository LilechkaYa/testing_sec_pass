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




def main():
    """
    Entry point that retrieves a live, logged-in driver.
    """
    driver = None
    try:
        print("--- Starting Portal Session ---")
        
        # 1. This one call now handles setup, credentials, and login
        # Set keep_browser_open=True to ensure the window stays alive for scraping
        driver = login_to_portal(keep_browser_open=True)
        
        # 2. If we reached this line, the driver is logged in
        print("\n--- Success ---")
        print(f"Driver is ready. Current URL: {driver.current_url}")
        
        # 3. SCRAPING STARTS HERE
        # You can now pass 'driver' to other functions:
        # data = perform_scraping(driver)

    except Exception as e:
        print(f"\n--- FATAL SCRIPT ERROR ---")
        print(f"The process failed: {e}")
    
    print("Script finished. Browser session remains active.")

if __name__ == "__main__":
    main()
        