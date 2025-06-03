from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image, ImageDraw
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
import string
from django.utils import timezone

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, unique=True)
    require_password_change = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"

    @staticmethod
    def generate_temp_password():
        """Generate a temporary password for new students"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField(help_text="Duration in hours")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issue_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(default=timezone.now, help_text="Course start date")
    end_date = models.DateTimeField(null=True, blank=True, help_text="Course end date")
    is_valid = models.BooleanField(default=True)
    grade = models.TextField(help_text="Student's grade in the course", null=True, blank=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.course.name}"

    def get_qr_code(self):
        # Generate QR code for certificate verification
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )        # The URL that will be used to verify the certificate
        verification_url = reverse('certificates:verify')
        # Add the certificate ID as a query parameter
        verification_url = f"{verification_url}?certificate_id={self.certificate_id}"
        # Make the URL absolute by adding the domain
        absolute_url = f"https://certifier.onrender.com{verification_url}"
        qr.add_data(absolute_url)
        qr.make(fit=True)

        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        return buffer.getvalue()

    def is_currently_valid(self):
        """Check if the certificate is valid"""
        return self.is_valid
