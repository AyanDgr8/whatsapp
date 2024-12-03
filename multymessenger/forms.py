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

    class Meta:
        model = MultyMessenger
        fields = ['contact_num', 'message']

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
