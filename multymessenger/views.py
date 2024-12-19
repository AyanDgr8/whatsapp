# multymessenger/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .forms import MessageForm, ExcelUploadForm
from .models import MultyMessenger
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from seleniumbase import Driver

import time
import logging
import os
import platform

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_chrome_driver_path():
    """
    Automatically detects the Google Chrome path based on the operating system.
    """
    system_platform = platform.system().lower()

    chrome_paths = {
        "windows": [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ],
        "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
        "linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",  # For Chromium
            "/opt/google/chrome/chrome",
        ],
    }

    for path in chrome_paths.get(system_platform, []):
        if os.path.exists(path):
            return path

    raise FileNotFoundError("Google Chrome not found on your system.")


def update_message_status(contact_num, status):
    """
    Update the message status and contact number validity in the database.
    """
    try:
        messenger_entry = MultyMessenger.objects.filter(contact_num=contact_num, message_status="pending").first()
        if messenger_entry:
            messenger_entry.message_status = "sent" if status == "Success" else "failed"
            messenger_entry.contact_num_valid = "yes" if status == "Success" else "no"
            messenger_entry.save()
    except Exception as e:
        logging.error(f"Error updating status for {contact_num}: {e}")


def initialize_webdriver():
    """
    Initialize the Selenium WebDriver with Chrome options.
    """
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    # options.add_argument("--headless")  # Headless mode
    options.add_argument("--no-sandbox")  # Needed for some Linux environments
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver = Driver(browser="chrome")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver: {e}")
        raise


def send_whatsapp_message(contact_nums, message):
    """
    Automate sending WhatsApp messages using Selenium WebDriver.
    """
    driver = None  # Ensure driver is defined even if initialization fails

    try:
        driver = initialize_webdriver()
        driver.get("https://web.whatsapp.com")
        logging.info("Please scan the QR Code in the browser to log in to WhatsApp.")

        # Wait for QR code scanning
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]'))
        )
        logging.info("WhatsApp Web successfully logged in.")
    except Exception as e:
        logging.error(f"Error during WhatsApp Web login: {e}")
        if driver:  # Check if driver was initialized before attempting to quit
            driver.quit()
        raise Exception("Failed to log in to WhatsApp Web. Please try again.")

    results = []

    try:
        for contact_num in contact_nums:
            try:
                # Open chat with the given phone number
                whatsapp_url = f"https://web.whatsapp.com/send?phone={contact_num}&text={message}"
                driver.get(whatsapp_url)
                time.sleep(5)

                # Handle "Invalid URL" alert if present
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//div[contains(@data-testid, "alert")]'))
                    )
                    alert_ok_button = driver.find_element(By.XPATH, '//button[contains(text(), "OK")]')
                    alert_ok_button.click()
                    logging.warning(f"Invalid URL for contact: {contact_num}")
                    results.append((contact_num, "Invalid URL, skipped"))
                    continue
                except Exception:
                    pass  # No alert found, proceed

                # Locate the input box and send the message
                input_box_xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
                input_box = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, input_box_xpath))
                )
                input_box.send_keys(Keys.ENTER)  # Press Enter to send
                time.sleep(2)
                results.append((contact_num, "Success"))
                logging.info(f"Message sent successfully to {contact_num}.")
            except Exception as e:
                logging.error(f"Failed to send message to {contact_num}: {e}")
                results.append((contact_num, f"Failed: {str(e)}"))

    except Exception as e:
        logging.error(f"Unexpected error during message sending: {e}")
    finally:
        if driver:  # Check if driver exists before quitting
            driver.quit()
        logging.info("WebDriver session ended.")

    # Update message statuses in the database
    for contact_num, status in results:
        update_message_status(contact_num, status)

    return results


def generate_unique_id():
    """
    Generate a unique ID for each message based on the last record in the database.
    """
    last_record = MultyMessenger.objects.last()
    if last_record:
        try:
            last_id = int(last_record.unique_id.split('_')[1])  # Extract numeric part
            return f"MuM_{last_id + 1}"  # Increment the number
        except (IndexError, ValueError):
            return "MuM_100"  # Default ID if parsing fails
    return "MuM_100"  # Default ID if no records exist


def home(request):
    contact_nums_str = ""  # Initialize the string for contact numbers
    first_names = []
    last_names = []

    if request.method == 'POST':
        if 'file-upload' in request.FILES:
            # Process the uploaded file
            file = request.FILES['file-upload']
            try:
                df = pd.read_excel(file)
                # Extract first names, last names, and phone numbers
                first_names = df['f_name'].dropna().astype(str).tolist()
                last_names = df['l_name'].dropna().astype(str).tolist()
                contact_nums = df['phone'].dropna().astype(str).tolist()

                # Prepare for pre-filling the form
                contact_nums_str = ','.join(contact_nums)
                messages.success(request, "File uploaded successfully!")

                # Save all contacts as new entries in the database
                for i, contact_num in enumerate(contact_nums):
                    unique_id = generate_unique_id()
                    f_name = first_names[i] if i < len(first_names) else None
                    l_name = last_names[i] if i < len(last_names) else None

                    # Always create a new record for each contact
                    MultyMessenger.objects.create(
                        unique_id=unique_id,
                        contact_num=contact_num,
                        # message='',  # No message during file upload
                        f_name=f_name,
                        l_name=l_name
                    )
                return redirect('home')  # Redirect after processing the file

            except Exception as e:
                messages.error(request, f"Error processing the uploaded file: {e}")
        else:
            # Process the message form submission
            form = MessageForm(request.POST)
            if form.is_valid():
                contact_nums = form.cleaned_data['contact_num']
                message = form.cleaned_data['message']
                f_name = form.cleaned_data['f_name']
                l_name = form.cleaned_data['l_name']

                # Create a new record for every message sent
                for contact_num in contact_nums:
                    unique_id = generate_unique_id()
                    f_name = f_name  # Names not provided during message submission
                    l_name = l_name

                    MultyMessenger.objects.create(
                        unique_id=unique_id,
                        contact_num=contact_num,
                        message=message,
                        f_name=f_name,
                        l_name=l_name
                    )

                # Send WhatsApp messages
                try:
                    results = send_whatsapp_message(contact_nums, message)
                except Exception as e:
                    messages.error(request, f"Error sending messages: {e}")
                    return redirect('home')

                # Display results
                for contact_num, status in results:
                    if status == "Success":
                        messages.success(request, f"Message sent to {contact_num}.")
                    else:
                        messages.error(request, f"Failed to send message to {contact_num}: {status}")

                return redirect('home')  # Clear the form after submission
    else:
        form = MessageForm(initial={'contact_num': contact_nums_str})  # Set initial value here

    excel_form = ExcelUploadForm()

    return render(request, 'multymessenger/home.html', {
        'form': form,
        'excel_form': excel_form,
        'contact_nums_str': contact_nums_str
    })

def file_upload_endpoint(request):
    """
    Handle the file upload and process the Excel file to extract phone numbers.
    Ensure that each phone number has at most 15 characters.
    """
    if request.method == 'POST' and request.FILES.get('file-upload'):
        file = request.FILES['file-upload']
        try:
            # Read the uploaded Excel file
            df = pd.read_excel(file)
            print(df.head())  # Debugging: Check the file content

            # Extract phone numbers and names
            contact_nums = df['phone'].dropna().astype(str).tolist()
            f_names = df['f_name'].dropna().astype(str).tolist()
            l_names = df['l_name'].dropna().astype(str).tolist()

            print(contact_nums, f_names, l_names)  # Debugging: Check extracted values

            # Ensure phone numbers have at most 15 characters
            contact_nums = [num[:15] for num in contact_nums]  # Truncate to 15 characters if longer

            # Save to database
            for i, contact_num in enumerate(contact_nums):
                f_name = f_names[i] if i < len(f_names) else None
                l_name = l_names[i] if i < len(l_names) else None

                # Check if this contact number already exists in the database
                if not MultyMessenger.objects.filter(contact_num=contact_num).exists():
                    # Debugging output before saving
                    print(f"Saving: {contact_num}, {f_name}, {l_name}")
                    
                    # Create a new MultyMessenger instance
                    MultyMessenger.objects.create(
                        unique_id=generate_unique_id(),  # Ensure you have a function to generate unique IDs
                        contact_num=contact_num,
                        f_name=f_name,
                        l_name=l_name
                    )
                else:
                    print(f"Duplicate entry found for contact number: {contact_num}")

            return JsonResponse({'contact_nums': contact_nums, 'f_names': f_names, 'l_names': l_names}) 
        
        except Exception as e:
            print(f"Error processing file: {e}") 
            return JsonResponse({'error': f"Error processing file: {e}"}, status=400)

    return JsonResponse({'error': 'No file uploaded'}, status=400)
