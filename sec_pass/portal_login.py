import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Use WebDriver Manager to handle the correct Chrome driver version
from webdriver_manager.chrome import ChromeDriverManager 

# --- 1. Load Environment Variables ---
load_dotenv()

# Retrieve constants from environment variables
#LOGIN_URL = os.getenv("LOGIN_URL")
#PORTAL_USER = os.getenv("PORTAL_USER")
#PORTAL_PASS = os.getenv("PORTAL_PASS")


def get_portal_credentials():
    try:
        credentials = {
            "LOGIN_URL": os.environ["LOGIN_URL"],
            "PORTAL_USER": os.environ["PORTAL_USER"],
            "PORTAL_PASS": os.environ["PORTAL_PASS"],
        }
        return credentials
    except KeyError as e:
        # Exit if any required variable is missing
        print(f"FATAL ERROR: Environment variable {e} is not set.")
        print("ACTION: Ensure your local .env file is present and correctly populated.")
        sys.exit(1)


# --- 2. API CREDENTIALS LOADING ---
# Load and validate credentials right away. If any are missing, the script exits here.
PORTAL_CREDENTIALS = get_portal_credentials()

# Map the credentials into the main variables for clearer use (optional, but clean)
LOGIN_URL = PORTAL_CREDENTIALS["LOGIN_URL"]
PORTAL_USER = PORTAL_CREDENTIALS["PORTAL_USER"]
PORTAL_PASS = PORTAL_CREDENTIALS["PORTAL_PASS"]


# Temporary check to confirm .env loaded successfully
#print(f"DEBUG: URL loaded is {LOGIN_URL}")


def login_only(driver: WebDriver) -> str:
    """
    Handles the login workflow only, with detailed debug prints.
    (Updated to use By.ID selectors based on HTML analysis)
    """
    if not all([LOGIN_URL, PORTAL_USER, PORTAL_PASS]):
        return "[CONFIG ERROR] Missing variables in .env."
        
    print(f"[Selenium] Navigating to login page: {LOGIN_URL}")
    
    try:
        # 1. Navigate to the login page
        driver.get(LOGIN_URL)
        #print("[DEBUG STEP 1] Successfully navigated to URL. Waiting for form elements.")
        
        # 2. Wait for the login form elements to be present
        # *** MODIFICATION 1: Changed By.NAME, "username" to By.ID, "LoginForm_username" ***
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "LoginForm_username"))
        )
        
        #print("[DEBUG STEP 2] Form elements found. Entering credentials.")
        
        # 3. Enter credentials
        # *** MODIFICATION 2: Changed By.NAME, "username" to By.ID, "LoginForm_username" ***
        driver.find_element(By.ID, "LoginForm_username").send_keys(PORTAL_USER)
        
        # *** MODIFICATION 3: Changed By.NAME, "password" to By.ID, "LoginForm_password" ***
        driver.find_element(By.ID, "LoginForm_password").send_keys(PORTAL_PASS)
        
        # 4. Find and click the login button
        # *** MODIFICATION 4: Simplified button search to use the known type="submit" ***
        login_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        
        login_button.click()
        #print("[DEBUG STEP 3] Login button clicked. Waiting for successful redirection.")
        
        # 5. Verify successful login
        WebDriverWait(driver, 10).until(
            EC.url_changes(LOGIN_URL) 
        )
        
        print("[Selenium] Login successful.")
        return "successful login"
        
    # Error handling remains the same...
    except TimeoutException:
        error_msg = "[Selenium ERROR] Timeout: Failed to find elements or redirect after login. Check if URL changed."
        return error_msg
    except NoSuchElementException as e:
        error_msg = f"[Selenium ERROR] Element Missing: Check selectors. Error: {e.msg.splitlines()[0]}"
        return error_msg
    except WebDriverException as e:
        error_msg = f"[Selenium ERROR] WebDriver/Network Issue: {e.msg.splitlines()[0]}"
        return error_msg
    except Exception as e:
        error_msg = f"[Selenium ERROR] Unexpected Error: {e}"
        return error_msg


def main():
    """
    Sets up the WebDriver and calls the login function. 
    This is the entry point of the script.
    """
    driver = None
    try:
        # 1. Setup WebDriver using WebDriverManager
        print("--- Setting up Chrome WebDriver ---")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        
        # 2. Call the login function
        print("--- Starting Login Process ---")
        login_status = login_only(driver)
        
        # 3. Output Result
        print("\n--- Final Login Result ---")
        print(f"Status: {login_status}")

    except Exception as e:
        print(f"\n--- FATAL SCRIPT ERROR ---")
        print(f"An unhandled error occurred during driver setup or script execution: {e}")
        login_status = "Driver Setup Failed"
    
    finally:
        # 4. Clean up
        if driver:
            driver.quit()
            print("Driver closed.")
        
if __name__ == "__main__":
    main()