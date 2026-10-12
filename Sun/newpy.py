import csv
import time
import random
import os
import hashlib
from playwright.sync_api import sync_playwright, TimeoutError

# --- Configuration ---
TARGET_URL = "https://signup.sunpalacecasino.eu/"
CSV_FILENAME = "accounts.csv"
EMAILS_FILENAME = "emails.txt"
COMPLETED_CSV_FILENAME = "registered_accounts.csv"

def generate_fingerprint(seed):
    """Generate deterministic browser fingerprint for isolation."""
    if seed is None:
        seed = random.randint(100000, 999999)
    return f"fingerprint_{hashlib.md5(str(seed).encode()).hexdigest()[:12]}"

def generate_unique_user_agent():
    """Generate varied but realistic User-Agent strings."""
    platforms = ["Windows 10", "Windows 11", "macOS 14", "Linux 6.5"]
    browsers = ["Mozilla/5.0", "Mozilla/5.0"]
    versions = ["2024-01", "2024-06", "2024-10"]
    
    platform = random.choice(platforms)
    version = random.choice(versions)
    ua = f"{browsers[0]} (X11; {platform}; rv:{version}) Gecko/{version} Firefox/{version}"
    return ua

def generate_random_resolution():
    """Return random but realistic viewport dimensions."""
    widths = [1366, 1440, 1536, 1920, 2560]
    heights = [768, 900, 1080, 1440, 2160]
    return random.choice(widths), random.choice(heights)

def random_pause(page, min_ms=200, max_ms=700, jitter=True):
    """Human-like random pause with micro-jitter."""
    if jitter:
        base_delay = random.randint(min_ms, max_ms)
        micro_jitter = random.randint(-30, 30)
    else:
        base_delay = random.randint(min_ms, max_ms)
        micro_jitter = 0
    
    time.sleep((base_delay + micro_jitter) / 1000.0)

def fill_field(page, selector, text, max_retries=3):
    """Fill field with error handling and retries."""
    for attempt in range(max_retries):
        locator = page.locator(selector)
        if locator.count() == 0:
            continue
        try:
            locator.first.click()
            random_pause(page, 100, 200)
            locator.first.fill(text, timeout=30000)
            random_pause(page, 100, 300)
            return True
        except Exception:
            continue
    return False

def human_type(page, selector_or_locator, text, delay_range=(30, 80)):
    """Type text with realistic human typing speed."""
    locator = page.locator(selector_or_locator) if isinstance(selector_or_locator, str) else selector_or_locator
    locator.first.click()
    random_pause(page, 100, 300)
    try:
        locator.first.press_sequentially(text, delay=random.randint(*delay_range))
    except Exception:
        locator.first.fill(text, timeout=30000)
    random_pause(page, 200, 500)

def click_first_visible(page, *selectors):
    """Try multiple selectors to find and click visible button."""
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() == 0:
            continue
        try:
            locator.first.click(force=True)
            random_pause(page, 200, 400)
            return True
        except Exception:
            continue
    return False

def register_account(page, account, auto_email, fingerprint_id):
    """Perform registration with fingerprint-aware isolation."""
    print(f"\n--- Starting registration for {account['first_name']} {account['last_name']} (FP: {fingerprint_id}) ---")
    
    # Small context-specific wait to avoid pattern detection
    random_pause(page, 1500, 2500)
    
    dob = account["dob"].strip()
    gender = account["gender"].strip().upper()

    page.goto(TARGET_URL)
    random_pause(page, 1200, 2200)

    # Step 1: Basic info
    field_mapping = {
        "first_name": [
            'input[name*="firstName"], input[placeholder*="First Name" i]',
            'input[name="ng.form0.stepOne.firstName"]',
        ],
        "last_name": [
            'input[name*="lastName"], input[placeholder*="Last Name" i]',
            'input[name="ng.form0.stepOne.lastName"]',
        ],
        "email": [
            'input[type="email"], input[name*="email" i]',
            'input[name="ng.form0.stepOne.email"]',
        ],
        "username": [
            'input[name*="userName" i], input[placeholder*="Username" i]',
            'input[name="ng.form0.stepOne.userName"]',
        ],
        "password": [
            'input[type="password"], input[name*="password" i]',
            'input[name="ng.form0.stepOne.password"]',
        ],
    }

    for field_name, selectors in field_mapping.items():
        value = auto_email if field_name == "email" else account[field_name]
        filled = False
        for selector in selectors:
            if fill_field(page, selector, value):
                filled = True
                break
        if not filled:
            print(f"  Warning: Could not fill {field_name} field.")

    human_type(page, 'input[name="ng.form0.stepOne.confirmPassword"]', account["password"])
    click_first_visible(page, 
        'fx-button:has-text("Next")', 
        'button:has-text("Next")', 
        'button[type="submit"]:has-text("Next")')
    random_pause(page, 800, 1500)

    # Step 2: Location (country/state)
    if page.locator("div.form-select-input").count() >= 2:
        dropdowns = page.locator("div.form-select-input")
        dropdowns.nth(0).click()
        random_pause(page, 300, 600)
        
        search_box = page.locator("input.form-select-option-filter").first
        if search_box.count() > 0:
            human_type(page, search_box, "India")
            page.locator("div.form-option").get_by_text("India", exact=True).first.click()
        else:
            page.get_by_text("India", exact=True).first.click()
        random_pause(page, 500, 1000)

        dropdowns.nth(1).click()
        random_pause(page, 300, 600)
        page.locator("div.form-option").get_by_text(account["state"], exact=True).first.click()
    else:
        click_first_visible(page, 'select[name*="country" i]', 'input[placeholder*="Country" i]')
        page.get_by_text("India", exact=True).first.click(timeout=10000)
    random_pause(page, 400, 800)

    human_type(page, 'input[name="ng.form0.stepTwo.city"]', account["city"])
    human_type(page, 'textarea[name="ng.form0.stepTwo.street1"]', account["address"])
    human_type(page, 'input[name="ng.form0.stepTwo.zipCode"]', account["zip"])
    random_pause(page, 400, 800)
    
    click_first_visible(page, 
        'fx-button:has-text("Next"):visible', 
        'button:has-text("Next"):visible',
        'button[type="submit"]:has-text("Next"):visible')
    random_pause(page, 800, 1500)

    # Step 3: Personal details
    gender_selector = 'label[for="genderFemale"]' if gender == "F" else 'label[for="genderMale"]'
    click_first_visible(page, gender_selector, 'label:has-text("Female")', 'label:has-text("Male")')
    random_pause(page, 300, 700)
    
    human_type(page, 'input[name="ng.form0.stepThree.phoneNumber"]', account["phone"])
    human_type(page, 'input[name="ng.form0.stepThree.birthDate"]', dob)
    random_pause(page, 400, 1000)
    
    page.locator("input#acceptNewsLetter").check(force=True)
    random_pause(page, 200, 500)
    page.locator("input#acceptTermsAndConditions").check(force=True)
    random_pause(page, 300, 700)
    
    click_first_visible(page, 
        'button[type="submit"]:has-text("Register")', 
        'fx-button:has-text("Register")')
    
    print(f"Registration submitted for {account['username']} using email {auto_email}.")

    # Wait for redirect
    try:
        page.wait_for_load_state("load", timeout=90000)
    except TimeoutError:
        print("Page load state timed out, proceeding anyway...")

    # Click Cashier button (if needed)
    try:
        cashier_btn = page.locator("#mainViewCashierBtn")
        cashier_btn.wait_for(state="visible", timeout=90000)
        random_pause(page, 1000, 2000)
        cashier_btn.click(force=True)
        print("Clicked Cashier.")
    except Exception:
        print("Cashier button not found or timed out.")

    # Open Emailnator in new tab
    emailnator_link = f"https://www.emailnator.com/mailbox#{auto_email}"
    new_tab = page.context.new_page()
    new_tab.goto(emailnator_link)
    random_pause(new_tab, 3000, 5000)
    print(f"Loaded inbox for {auto_email}. Check for verification email.")


def load_accounts(filename):
    """Load accounts from CSV with error handling."""
    accounts = []
    try:
        with open(filename, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                accounts.append(row)
        print(f"✓ Successfully loaded {len(accounts)} accounts from {filename}.")
        return accounts
    except FileNotFoundError:
        print(f"✗ Error: Could not find {filename}.")
        return []
    except Exception as e:
        print(f"✗ Error loading {filename}: {e}")
        return []


def load_emails(filename):
    """Load emails from text file with validation."""
    emails = []
    try:
        with open(filename, mode="r", encoding="utf-8") as file:
            for line in file:
                email = line.strip()
                if email and "@" in email:
                    emails.append(email)
        print(f"✓ Successfully loaded {len(emails)} valid emails from {filename}.")
        return emails
    except FileNotFoundError:
        print(f"✗ Error: Could not find {filename}.")
        return []
    except Exception as e:
        print(f"✗ Error loading {filename}: {e}")
        return []


def save_completed_account(account, email, filename):
    """Append completed account to results CSV."""
    account_to_save = account.copy()
    account_to_save["email"] = email
    file_exists = os.path.isfile(filename)
    fieldnames = list(account_to_save.keys())

    with open(filename, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(account_to_save)


def update_pending_files(remaining_accounts, remaining_emails, accounts_file, emails_file):
    """Save remaining accounts and emails for next run."""
    if remaining_accounts:
        fieldnames = list(remaining_accounts[0].keys())
        with open(accounts_file, mode="w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_accounts)
    else:
        open(accounts_file, "w").close()
    
    with open(emails_file, mode="w", encoding="utf-8") as file:
        for email in remaining_emails:
            file.write(email + "\n")


def main():
    """Main orchestration with session management."""
    accounts = load_accounts(CSV_FILENAME)
    emails = load_emails(EMAILS_FILENAME)
    
    if not accounts:
        print("✗ No accounts loaded. Exiting.")
        return
    if not emails:
        print("✗ No emails loaded. Please ensure emails.txt exists. Exiting.")
        return

    print(f"🚀 Starting automation for {len(accounts)} accounts with {len(emails)} emails...")
    print("🔐 Using fingerprint isolation for privacy.")
    
    total_start = time.time()
    
    with sync_playwright() as p:
        # Launch browser with privacy-focused settings
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-features=NetworkPrediction,IdleDetection",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=ImprovedCookieControls",
                "--disable-default-apps",
                "--disable-component-extensions-with-background-pages",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--disable-sync",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pings",
                "--safe-mode",
            ]
        )
        
        try:
            while accounts and emails:
                current_account = accounts.pop(0)
                current_email = emails.pop(0)
                
                # Generate unique fingerprint for this session
                fingerprint_id = generate_fingerprint(current_account.get("username"))
                user_agent = generate_unique_user_agent()
                width, height = generate_random_resolution()
                
                print(f"\n[{current_account['username']}] Session FP: {fingerprint_id}")
                
                context = browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": width, "height": height},
                    locale="en-US",
                    timezone_id="America/New_York",
                    geolocation={"latitude": 40.7128, "longitude": -74.0060},
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br"
                    }
                )
                
                page = context.new_page()
                page.set_default_timeout(90000)
                page.set_extra_http_headers({
                    "X-Fingerprint-ID": fingerprint_id,
                    "X-Session-UID": hashlib.sha256(str(current_email).encode()).hexdigest()[:16]
                })

                try:
                    register_account(page, current_account, current_email, fingerprint_id)
                    
                    save_completed_account(current_account, current_email, COMPLETED_CSV_FILENAME)
                    update_pending_files(accounts, emails, CSV_FILENAME, EMAILS_FILENAME)
                    
                    print(
                        f"✓ [SUCCESS] Moved {current_account['username']} to "
                        f"{COMPLETED_CSV_FILENAME}"
                    )
                    
                    if accounts and emails:
                        input("\n>>> Account complete. Press ENTER to continue... <<<\n")
                        
                except Exception as inner_e:
                    error_msg = f"✗ [!] Registration failed for {current_account['username']}: {inner_e}"
                    print(error_msg)
                    # Continue instead of crashing
                finally:
                    context.close()
                    
            if not emails and accounts:
                print("\n⚠ Ran out of emails in emails.txt. Stopping script.")
                
        except KeyboardInterrupt:
            print("\n⚠ Script interrupted by user.")
        except Exception as e:
            print(f"\n✗ [!] An unexpected error occurred: {e}")
            input(">>> ERROR: Press ENTER to close the browser and end the script... <<<")
        finally:
            browser.close()
            
    total_time = time.time() - total_start
    print(f"\n🏁 Automation complete. Total runtime: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
