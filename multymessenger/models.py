# multymessenger/models.py
from django.db import models

class MultyMessenger(models.Model):
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

    class Meta:
        db_table = 'messenger'  # Custom database table name
        indexes = [
            models.Index(fields=['unique_id']),  # Index for faster lookups
        ]
        # Optional: Explicitly specify database charset if needed (in database migration)
        # Example for MySQL: 'DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci'

    def __str__(self):
        return f"Message {self.id} from {self.contact_num} sent at {self.date_sent}"
