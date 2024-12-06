# multymessenger/models.py

from django.db import models

class MultyMessenger(models.Model):
    YES_NO_CHOICES = [('yes', 'Yes'), ('no', 'No')]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    # Auto-generated primary key
    id = models.AutoField(primary_key=True)

    # Unique identifier for each message (e.g., UUID or other generated ID)
    unique_id = models.CharField(max_length=36, unique=True)

    # Optional fields for sender's first and last name
    f_name = models.CharField(max_length=50, null=True, blank=True)
    l_name = models.CharField(max_length=50, null=True, blank=True)

    # Required contact number
    contact_num = models.TextField()

    # The message content
    message = models.TextField()

    # Automatically set the date when the message is sent
    date_sent = models.DateTimeField(auto_now_add=True)

    # Indicates whether the message has been sent (yes/no)
    message_status = models.CharField(max_length=7, choices=STATUS_CHOICES, default='pending')

    # Indicates whether the contact number is valid (yes/no)
    contact_num_valid = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='yes')

    class Meta:
        db_table = 'messenger'  # Custom database table name
        indexes = [
            models.Index(fields=['unique_id']), 
            models.Index(fields=['contact_num']),
            models.Index(fields=['date_sent']),
        ]

    def __str__(self):
        return f"Message to {self.unique_id} {self.contact_num} - {self.get_message_status_display} sent at {self.date_sent}"
