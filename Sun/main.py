import csv
import time
import random
import os
from playwright.sync_api import sync_playwright

# --- Configuration ---
TARGET_URL = "https://signup.sunpalacecasino.eu/"
CSV_FILENAME = "accounts.csv"
EMAILS_FILENAME = "emails.txt"
COMPLETED_CSV_FILENAME = "registered_accounts.csv"

def load_accounts(filename):
    accounts = []
    try:
        with open(filename, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                accounts.append(row)
        print(f"Successfully loaded {len(accounts)} accounts from {filename}.")
        return accounts
    except FileNotFoundError:
        print(f"Error: Could not find {filename}.")
        return []

def load_emails(filename):
    emails = []
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    emails.append(line.strip())
        print(f"Successfully loaded {len(emails)} emails from {filename}.")
        return emails
    except FileNotFoundError:
        print(f"Error: Could not find {filename}.")
        return []

def save_completed_account(account, email, filename):
    """Appends the completed account to the finished CSV file."""
    account_to_save = account.copy()
    account_to_save['email'] = email  
   
    file_exists = os.path.isfile(filename)
    fieldnames = list(account_to_save.keys())
   
    with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(account_to_save)

def update_pending_files(remaining_accounts, remaining_emails, accounts_file, emails_file):
    """Overwrites the original files to remove the processed entries."""
    if remaining_accounts:
        fieldnames = list(remaining_accounts[0].keys())
        with open(accounts_file, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_accounts)
    else:
        open(accounts_file, 'w').close()
       
    with open(emails_file, mode='w', encoding='utf-8') as file:
        for em in remaining_emails:
            file.write(em + '\n')

def random_pause(page, min_ms=200, max_ms=700):
    page.wait_for_timeout(random.randint(min_ms, max_ms))

def human_type(page, selector_or_locator, text):
    if isinstance(selector_or_locator, str):
        locator = page.locator(selector_or_locator)
    else:
        locator = selector_or_locator
    locator.click()
   
    page.wait_for_timeout(random.randint(100, 300))
    locator.press_sequentially(text, delay=random.randint(30, 80))
    page.wait_for_timeout(random.randint(200, 500))

def register_account(page, account, auto_email):
    print(f"\n--- Starting registration for {account['first_name']} {account['last_name']} ---")
   
    dob = account['dob'].strip()
    gender = account['gender'].strip().upper()
   
    page.goto(TARGET_URL)
    random_pause(page, 1000, 2000)

    # --- STEP 1: Personal Details ---
    human_type(page, 'input[name="ng.form0.stepOne.firstName"]', account["first_name"])
    human_type(page, 'input[name="ng.form0.stepOne.lastName"]', account["last_name"])
    human_type(page, 'input[name="ng.form0.stepOne.email"]', auto_email)
    human_type(page, 'input[name="ng.form0.stepOne.userName"]', account["username"])
    human_type(page, 'input[name="ng.form0.stepOne.password"]', account["password"])
    human_type(page, 'input[name="ng.form0.stepOne.confirmPassword"]', account["password"])
   
    random_pause(page, 300, 600)
    page.click('fx-button:has-text("Next")')
    random_pause(page, 800, 1500)

    # --- STEP 2: Address Details ---
    dropdowns = page.locator('div.form-select-input')
    dropdowns.nth(0).click()
    random_pause(page, 300, 600)

    search_box = page.locator('input.form-select-option-filter').first
    human_type(page, search_box, 'India')
   
    page.locator('div.form-option').get_by_text('India', exact=True).first.click()
    random_pause(page, 500, 1000)
   
    dropdowns.nth(1).click()
    random_pause(page, 300, 600)
    page.locator('div.form-option').get_by_text(account['state'], exact=True).first.click()
   
    random_pause(page, 400, 800)
    human_type(page, 'input[name="ng.form0.stepTwo.city"]', account["city"])
    human_type(page, 'textarea[name="ng.form0.stepTwo.street1"]', account["address"])
    human_type(page, 'input[name="ng.form0.stepTwo.zipCode"]', account["zip"])
   
    random_pause(page, 400, 800)
    page.click('fx-button:has-text("Next"):visible')
    random_pause(page, 800, 1500)

    # --- STEP 3: Final Details ---
    if gender == 'F':
        page.click('label[for="genderFemale"]')
    else:
        page.click('label[for="genderMale"]')
       
    random_pause(page, 300, 700)
    human_type(page, 'input[name="ng.form0.stepThree.phoneNumber"]', account["phone"])
    human_type(page, 'input[name="ng.form0.stepThree.birthDate"]', dob)
   
    random_pause(page, 400, 1000)
    page.locator('input#acceptNewsLetter').check(force=True)
    random_pause(page, 200, 500)
    page.locator('input#acceptTermsAndConditions').check(force=True)
    random_pause(page, 300, 700)
   
    page.click('button[type="submit"]:has-text("Register")')
    print(f"Registration submitted for {account['username']} using email {auto_email}.")
   
    # --- POST-REGISTRATION STEPS ---
    print("Waiting for homepage redirect...")
   
    try:
        page.wait_for_load_state("load", timeout=90000)
    except Exception as e:
        print("Page load state took too long, proceeding anyway...")

    cashier_btn = page.locator('#mainViewCashierBtn')
    cashier_btn.wait_for(state='visible', timeout=90000)
    random_pause(page, 1000, 2000)
    cashier_btn.click(force=True)
    print("Clicked Cashier.")
   
    print("Opening Emailnator in a new tab...")
    emailnator_link = f"https://www.emailnator.com/mailbox#{auto_email}"
   
    new_tab = page.context.new_page()
    new_tab.goto(emailnator_link)
   
    random_pause(new_tab, 3000, 5000)
    print(f"Loaded inbox for {auto_email}. Check for the verification email.")

def main():
    accounts = load_accounts(CSV_FILENAME)
    emails = load_emails(EMAILS_FILENAME)
   
    if not accounts:
        print("No accounts loaded. Exiting.")
        return
    if not emails:
        print("No emails loaded. Please ensure emails.txt exists. Exiting.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        try:
            while accounts and emails:
                current_account = accounts.pop(0)
                current_email = emails.pop(0)

                # Route Playwright traffic through standard local connection
                context = browser.new_context(
                    no_viewport=True
                )
                page = context.new_page()
               
                page.set_default_timeout(60000)
               
                try:
                    register_account(page, current_account, current_email)
                   
                    save_completed_account(current_account, current_email, COMPLETED_CSV_FILENAME)
                    update_pending_files(accounts, emails, CSV_FILENAME, EMAILS_FILENAME)
                    print(f"[SUCCESS] Moved {current_account['username']} to {COMPLETED_CSV_FILENAME} and updated pending files.")
                   
                except Exception as inner_e:
                    print(f"\n[!] Registration failed for {current_account['username']}: {inner_e}")
                    raise inner_e
               
                if accounts and emails:
                    input("\n>>> Account complete. Press ENTER to continue to the next account... <<<\n")
               
                context.close()
               
            if not emails and accounts:
                print("\nRan out of emails in emails.txt. Stopping script.")
               
        except Exception as e:
            print(f"\n[!] An error occurred: {e}")
            input(">>> ERROR: Press ENTER to close the browser and end the script... <<<")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
