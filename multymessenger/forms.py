# multymessenger/forms.py

from django import forms
from .models import MultyMessenger

class MessageForm(forms.ModelForm):
    """
    Form for sending messages to multiple recipients.
    """
    contact_num = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter multiple numbers separated by commas',
            'class': 'form-control' 
        }),
        label='Contact Numbers (separate by commas)'
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Type your message...',
            'rows': 4,
            'class': 'form-control' 
        }),
        label='Message'
    )

    f_name = forms.CharField(
        widget=forms.HiddenInput(),  # Hidden field
        required=False
    )

    l_name = forms.CharField(
        widget=forms.HiddenInput(),  # Hidden field
        required=False
    )

    message_sent = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        widget=forms.HiddenInput(), 
        required=False
    )

    contact_num_valid = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        widget=forms.HiddenInput(), 
        required=False
    )

    class Meta:
        model = MultyMessenger
        fields = ['contact_num', 'message', 'f_name', 'l_name', 'message_sent', 'contact_num_valid']

    def clean_contact_num(self):
        """
        Custom validation for `contact_num`.
        Splits the input string into a list and validates each number.
        """
        contact_nums = self.cleaned_data['contact_num']
        contact_nums_list = [num.strip() for num in contact_nums.split(',')]

        # Define a regex for validating international phone numbers
        import re
        phone_regex = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format

        for num in contact_nums_list:
            if not phone_regex.match(num):
                raise forms.ValidationError(f"Invalid phone number format: {num}")
        
        return contact_nums_list  # Return the cleaned list of phone numbers


class ExcelUploadForm(forms.Form):
    """
    Form for uploading an Excel file.
    """
    file = forms.FileField(
        required=True,
        label="Upload Excel File",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file'  # Add custom class for styling
        })
    )

    def save_contacts(self, uploaded_file):
        """
        This method should be called to process the uploaded Excel file and
        save the contact details to the database.
        """
        import pandas as pd

        # Assuming the uploaded file is an Excel file with columns: 'f_name', 'l_name', 'phone', 'message_sent', 'contact_num_valid'
        df = pd.read_excel(uploaded_file)
        
        for _, row in df.iterrows():
            # Create a MultyMessenger instance for each row in the Excel file
            MultyMessenger.objects.create(
                f_name=row.get('f_name', ''),
                l_name=row.get('l_name', ''),
                contact_num=row['phone'],
                message_sent=row.get('message_sent', 'yes'),
                contact_num_valid=row.get('contact_num_valid', 'yes')
            )
