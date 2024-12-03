# multymessenger/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .forms import MessageForm, ExcelUploadForm
from .models import MultyMessenger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
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


def send_whatsapp_message(contact_nums, message):
    """
    Automate sending WhatsApp messages using Selenium WebDriver.
    """
    driver = webdriver.Chrome()  # Make sure to adjust the ChromeDriver path
    driver.get("https://web.whatsapp.com")
    print("Please scan the QR Code in the browser to log in to WhatsApp.")

    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]'))
        )
    except Exception:
        driver.quit()
        raise Exception("QR code login timeout. Please try again.")

    results = []
    for contact_num in contact_nums:
        try:
            # Open chat with the given phone number
            whatsapp_url = f"https://web.whatsapp.com/send?phone={contact_num}&text={message}"
            driver.get(whatsapp_url)
            time.sleep(10)

            # Locate the input box and send the message
            input_box_xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
            input_box = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, input_box_xpath))
            )
            input_box.send_keys(Keys.ENTER)  # Press Enter to send
            time.sleep(2)
            results.append((contact_num, "Success"))
        except Exception as e:
            results.append((contact_num, f"Failed: {str(e)}"))

    driver.quit()
    return results


def home(request):
    """
    Render the home page, handle file uploads, and process the message form.
    """
    contact_nums_str = ""  # Pre-filled numbers from the uploaded file

    if request.method == 'POST':
        if 'file-upload' in request.FILES:
            # Process the uploaded file
            file = request.FILES['file-upload']
            try:
                df = pd.read_excel(file)
                contact_nums = df['phone'].dropna().astype(str).tolist()
                contact_nums_str = ','.join(contact_nums)  # Prepare for pre-filling the form
                messages.success(request, "File uploaded successfully!")
            except Exception as e:
                messages.error(request, f"Error processing the uploaded file: {e}")
        else:
            # Process the message form submission
            form = MessageForm(request.POST)
            if form.is_valid():
                contact_nums = form.cleaned_data['contact_num']
                message = form.cleaned_data['message']

                # Save messages to the database
                for contact_num in contact_nums:
                    unique_id = generate_unique_id()
                    MultyMessenger.objects.create(
                        unique_id=unique_id,
                        contact_num=contact_num,
                        message=message
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
        form = MessageForm()

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
            # Extract phone numbers
            contact_nums = df['phone'].dropna().astype(str).tolist()

            # Ensure phone numbers have at most 15 characters
            contact_nums = [num[:15] for num in contact_nums]  # Truncate to 15 characters if longer

            return JsonResponse({'contact_nums': contact_nums})  # Return as JSON
        except Exception as e:
            return JsonResponse({'error': f"Error processing file: {e}"}, status=400)

    return JsonResponse({'error': 'No file uploaded'}, status=400)
