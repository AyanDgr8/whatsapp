# multymessenger/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .forms import MessageForm, ExcelUploadForm
from .models import MultyMessenger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd

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

def open_whatsapp_in_new_tab(driver):
    """
    Open WhatsApp Web in a new browser tab using JavaScript.
    """
    driver.execute_script("window.open('https://web.whatsapp.com', '_blank');")
    # Switching to the new tab
    driver.switch_to.window(driver.window_handles[-1])
    print("WhatsApp Web is now open in a new tab. Please scan the QR Code to log in.")

def send_whatsapp_message(contact_nums, message):
    """
    Automate sending WhatsApp messages using an existing WebDriver.
    """
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Start the browser maximized
    chrome_options.add_argument("--disable-infobars")  # Disable the 'Chrome is being controlled' infobar
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--headless")  # Optionally run in headless mode (without GUI)
    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--no-sandbox") #Bypass OS security model, MUST BE THE VERY FIRST OPTION
    options.add_argument("--headless")
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("start-maximized");  #open Browser in maximized mode
    options.add_argument("disable-infobars"); # disabling infobars
    options.add_argument("--disable-extensions"); # disabling extensions
    options.add_argument("--disable-gpu"); #applicable to windows os only
    options.add_argument("--disable-dev-shm-usage"); # overcome limited resource problems

    # Initialize the driver with ChromeDriverManager
    service = Service(ChromeDriverManager().install())  # Automatically manage ChromeDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)  # Create the driver

    # Open WhatsApp in a new tab
    open_whatsapp_in_new_tab(driver)

    # Wait for WhatsApp Web to load
    time.sleep(10)  # Adjust this wait time if necessary

    results = []
    for contact_num in contact_nums:
        try:
            # Open chat with the given phone number
            whatsapp_url = f"https://web.whatsapp.com/send?phone={contact_num}&text={message}"
            driver.get(whatsapp_url)
            time.sleep(5)  # Reduced wait time for the URL to load

            # Check for the "Invalid URL" alert message
            try:
                # Wait for the alert to be present and handle it if found
                WebDriverWait(driver, 2).until(EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[1]/div/div/span[2]/div/span/div/div/div/div/div/div[2]/div/button")
                ))
                # Click the "OK" button to close the invalid URL alert
                ok_button = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/span[2]/div/span/div/div/div/div/div/div[2]/div/button")
                ok_button.click()  # Close the alert
                time.sleep(2)  # Reduced sleep time after handling the alert
                results.append((contact_num, "Invalid URL, skipped"))
                continue  # Continue with the next contact number

            except Exception:
                # No alert found, continue normally
                pass

            # Locate the input box and send the message
            input_box_xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
            input_box = WebDriverWait(driver, 4).until(
                EC.visibility_of_element_located((By.XPATH, input_box_xpath))
            )
            input_box.send_keys(Keys.ENTER)  # Press Enter to send
            time.sleep(2)  # Shorter sleep after sending
            results.append((contact_num, "Success"))
        except Exception as e:
            results.append((contact_num, f"Failed: {str(e)}"))

    driver.quit()
    return results

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
            message = message,

            print(contact_nums, f_names, l_names, message)  # Debugging: Check extracted values

            # Ensure phone numbers have at most 15 characters
            contact_nums = [num[:15] for num in contact_nums]  # Truncate to 15 characters if longer

            # Save to database
            for i, contact_num in enumerate(contact_nums):
                f_name = f_names[i] if i < len(f_names) else None
                l_name = l_names[i] if i < len(l_names) else None

                # Check if this contact number already exists in the database
                if not MultyMessenger.objects.filter(contact_num=contact_num).exists():
                    # Debugging output before saving
                    print(f"Saving: {contact_num}, {f_name}, {l_name} {message}")
                    
                    # Create a new MultyMessenger instance
                    MultyMessenger.objects.create(
                        unique_id=generate_unique_id(),  # Ensure you have a function to generate unique IDs
                        contact_num=contact_num,
                        f_name=f_name,
                        l_name=l_name,
                        message=message
                    )
                else:
                    print(f"Duplicate entry found for contact number: {contact_num}")

            return JsonResponse({'contact_nums': contact_nums, 'f_names': f_names, 'l_names': l_names, 'message': message}) 
        
        except Exception as e:
            print(f"Error processing file: {e}") 
            return JsonResponse({'error': f"Error processing file: {e}"}, status=400)

    return JsonResponse({'error': 'No file uploaded'}, status=400)
