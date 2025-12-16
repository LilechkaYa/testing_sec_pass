import os
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
LOGIN_URL = os.getenv("LOGIN_URL")
PORTAL_USER = os.getenv("PORTAL_USER")
PORTAL_PASS = os.getenv("PORTAL_PASS")

# Temporary check to confirm .env loaded successfully
print(f"DEBUG: URL loaded is {LOGIN_URL}")


def login_only(driver: WebDriver) -> str:
    """
    Handles the login workflow only, navigating to the login page, 
    entering credentials, and submitting the form.

    :param driver: The Selenium WebDriver instance.
    :return: A string indicating the result: "successful login" or a detailed error message.
    """
    
    # 0. Configuration check (Already confirmed to be working, but kept for safety)
    if not all([LOGIN_URL, PORTAL_USER, PORTAL_PASS]):
        return "[CONFIG ERROR] Missing variables (URL/USER/PASS) in the .env file."
        
    print(f"[Selenium] Navigating to login page: {LOGIN_URL}")
    
    try:
        # 1. Navigate to the login page
        driver.get(LOGIN_URL)
        print("[DEBUG STEP 1] Successfully navigated to URL. Waiting for form elements.")
        
        # 2. Wait for the login form elements to be present (adjust element names if necessary)
        WebDriverWait(driver, 10).until(
            # This assumes the username field has a 'name' attribute set to 'username'
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        print("[DEBUG STEP 2] Form elements found. Entering credentials.")
        
        # 3. Enter credentials
        driver.find_element(By.NAME, "username").send_keys(PORTAL_USER)
        driver.find_element(By.NAME, "password").send_keys(PORTAL_PASS)
        
        # 4. Find and click the login button
        login_button = None
        try:
            # Try common selectors first
            login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        except NoSuchElementException:
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            except NoSuchElementException:
                # Fallback: Find button by common text
                login_button = driver.find_element(
                    By.XPATH, 
                    "//button[contains(text(), 'Login') or contains(text(), 'Sign In')] | //input[@value='Login' or @value='Sign In']"
                )
                
        login_button.click()
        print("[DEBUG STEP 3] Login button clicked. Waiting for successful redirection.")
        
        # 5. Verify successful login by waiting for the URL to change
        # This is the standard way to confirm a successful login redirect.
        WebDriverWait(driver, 10).until(
            EC.url_changes(LOGIN_URL) 
        )
        
        print("[Selenium] Login successful.")
        return "successful login"
        
    except TimeoutException:
        # Check if the page shows an error message indicating failed login
        # This is an optional check, customize based on your login page's error element
        try:
            # Look for a common error message element, e.g., one with the class 'error-message'
            driver.find_element(By.CLASS_NAME, "error-message")
            return "[Selenium ERROR] Login failed: Page shows an authentication error message."
        except NoSuchElementException:
            # If no error message is found, it was a general timeout (bad selectors or slow redirect)
            return "[Selenium ERROR] Timeout: Failed to find login elements or post-login redirection timed out."
            
    except NoSuchElementException as e:
        error_msg = f"[Selenium ERROR] Element Missing: Cannot find expected element (username, password, or button). Error: {e.msg.splitlines()[0]}"
        return error_msg
        
    except WebDriverException as e:
        error_msg = f"[Selenium ERROR] WebDriver/Network Issue: Failed to connect or browser crash. Error: {e.msg.splitlines()[0]}"
        return error_msg
        
    except Exception as e:
        error_msg = f"[Selenium ERROR] An unexpected error occurred: {e}"
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