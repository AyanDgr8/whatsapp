# multymessenger/views.py

from django.shortcuts import render, redirect
from .forms import MessageForm, ExcelUploadForm
from .models import MultyMessenger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
from django.http import JsonResponse

# Function to generate unique ID
def generate_unique_id():
    last_record = MultyMessenger.objects.last()
    if last_record:
        try:
            last_id = int(last_record.unique_id.split('_')[1])  # Extract the number from the unique_id
            new_id = f"MuM_{last_id + 1}"  # Increment the last number and create the new ID
        except (IndexError, ValueError):
            new_id = "MuM_100"
    else:
        new_id = "MuM_100"
    
    return new_id

# Function to send WhatsApp message
def send_whatsapp_message(contact_nums, message):
    driver = webdriver.Chrome()  # Adjust path if necessary
    print("Opening WhatsApp Web...")
    driver.get("https://web.whatsapp.com")
        
    print("Waiting for QR code to load...")
    input_box_xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
    WebDriverWait(driver, 60).until(
        EC.visibility_of_element_located((By.XPATH, input_box_xpath))
    )
    print("QR code scanned, sending messages...")
    
    for contact_num in contact_nums:
        try:
            whatsapp_url = f"https://web.whatsapp.com/send?phone={contact_num}&text={message}"
            driver.get(whatsapp_url)
            time.sleep(5)  # Give some time for the page to load

            # Locate the message input box using the provided XPath
            input_box_xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
            input_box = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, input_box_xpath))
            )
            input_box.send_keys(Keys.ENTER)  # This sends the message automatically
            time.sleep(2)
        except Exception as e:
            print(f"Error sending message to {contact_num}: {e}")
    
    driver.quit()

# Function to prepend the country code
def add_country_code(contact_num):
    # Add "+91" to the contact number if it doesn't already start with it
    if not contact_num.startswith("+91"):
        return "+91" + contact_num
    return contact_num

def home(request):
    contact_nums_str = ""  # Initialize an empty string for the contact numbers
    form = MessageForm()  # Initialize the form by default
    contact_nums = []  # To hold the phone numbers from the uploaded file

    if request.method == 'POST':
        if 'file-upload' in request.FILES:
            # Handle file upload
            file = request.FILES['file-upload']
            try:
                # Read the Excel file and extract f_name, l_name, and phone
                df = pd.read_excel(file)

                # Extract the relevant columns (assuming column names in the Excel file are 'f_name', 'l_name', 'phone')
                contact_nums = df['phone'].dropna().astype(str).tolist()

                # Add the country code "+91" to each contact number
                contact_nums = [add_country_code(num) for num in contact_nums]

                contact_nums_str = ', '.join(contact_nums)  # Join phone numbers as a comma-separated string

                # Save f_name, l_name, and phone into the database
                for _, row in df.iterrows():
                    unique_id = generate_unique_id()
                    MultyMessenger.objects.create(
                        unique_id=unique_id,
                        contact_num=row['phone'],
                        f_name=row['f_name'],
                        l_name=row['l_name'],
                        message="",  # You can leave this blank if the message is sent later
                    )

                # Fill the contact_num field with the extracted phone numbers
                form = MessageForm(initial={'contact_num': contact_nums_str})

                # Return JSON response with the contact numbers
                return JsonResponse({'contact_nums': contact_nums})
            except Exception as e:
                print(f"Error processing file: {e}")
        else:
            # Handle form submission
            form = MessageForm(request.POST)
            if form.is_valid():
                contact_nums = form.cleaned_data['contact_num'].split(',')
                message = form.cleaned_data['message']

                # Add the country code "+91" to each contact number
                contact_nums = [add_country_code(num) for num in contact_nums]

                # Save each contact and message in the database
                for contact_num in contact_nums:
                    unique_id = generate_unique_id()
                    MultyMessenger.objects.create(
                        unique_id=unique_id,
                        contact_num=contact_num,
                        message=message
                    )

                # Send the messages
                send_whatsapp_message(contact_nums, message)
                return redirect('home')

    excel_form = ExcelUploadForm()

    # Pass the extracted numbers to the template
    return render(request, 'multymessenger/home.html', {
        'form': form,
        'excel_form': excel_form,
        'contact_nums_str': contact_nums_str
    })
