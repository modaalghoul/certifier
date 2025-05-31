from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from .models import Certificate, Course, Student
from PIL import Image
from reportlab.lib.utils import ImageReader
import uuid
from functools import wraps
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from ipware import get_client_ip
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe
from django.conf import settings
import os
from django.templatetags.static import static
from django.contrib.staticfiles import finders

def generate_certificate_pdf(certificate):
    buffer = BytesIO()
    try:
        # Get the background image path
        bg_image_path = finders.find('certificates/images/certificate_background.jpg')
        if not bg_image_path:
            raise ValueError("Certificate background image not found")

        # Get exact dimensions from background image
        with Image.open(bg_image_path) as img:
            img_width, img_height = img.size

        # Create the PDF with exact image dimensions
        c = canvas.Canvas(buffer, pagesize=(img_width, img_height))
        
        # Draw the background image at exact size
        c.drawImage(bg_image_path, 0, 0, img_width, img_height)

        # Calculate positions relative to image dimensions
        # Assuming standard positions as percentages of total dimensions
        name_y = img_height * 0.37  # Position for name
        course_y = img_height * 0.25  # Position for course name
        dates_y = img_height * 0.125  # Position for dates
        
        # Add only variable content
        # Add student name
        c.setFont("Helvetica-Bold", int(img_height * 0.04))  # Dynamic font size
        name = certificate.student.user.get_full_name() or certificate.student.user.email
        c.drawCentredString(img_width/2, name_y, name)
        
        # Add course name
        c.setFont("Helvetica-Bold", int(img_height * 0.035))
        c.drawCentredString(img_width/2, course_y, certificate.course.name)
        
        # Add dates with dynamic positioning
        dates_x = img_width * 0.27
        dates_from_x = img_width * 0.27
        dates_to_x = img_width * 0.45
        c.setFont("Helvetica", int(img_height * 0.025))
        start_date = certificate.start_date.strftime('%d/%m/%Y')
        end_date = certificate.end_date.strftime('%d/%m/%Y') if certificate.end_date else "Ongoing"
        c.drawString(dates_from_x, dates_y, f"{start_date}")
        c.drawString(dates_to_x, dates_y, f"{end_date}")

        # Add grade if available
        if certificate.grade:
            grade_y = dates_y - int(img_height * 0.035)
            c.drawString(dates_x, grade_y, f"{certificate.grade}")
        
        duration_y = dates_y - int(img_height * 0.065)
        c.drawString(dates_x, duration_y, f"{certificate.course.duration} hours")
        
        # Add certificate ID at bottom with dynamic positioning
        c.setFont("Helvetica", int(img_height * 0.015))
        c.setFillColor(colors.gray)
        c.drawString(img_width * 0.05, img_height * 0.04, f"Certificate ID: {certificate.certificate_id}")
        
        # Add QR code with white background
        qr_code = certificate.get_qr_code()
        qr_image_buffer = BytesIO()
        qr_size = int(img_height * 0.15)  # QR code size relative to image height
        
        with Image.open(BytesIO(qr_code)) as qr_image:
            # Create a white background
            bg = Image.new('RGBA', qr_image.size, 'white')
            # Paste the QR code onto the white background
            bg.paste(qr_image)
            bg.save(qr_image_buffer, format='PNG')
            qr_image_buffer.seek(0)
            qr_image_reader = ImageReader(qr_image_buffer)
            # Draw the QR code at the bottom right
            c.drawImage(qr_image_reader, 
                       img_width - (qr_size * 9), 
                       img_height * 0.07, 
                       width=qr_size, 
                       height=qr_size, 
                       mask='auto')
        
        # Close the PDF object cleanly
        c.showPage()
        c.save()
        
        return buffer.getvalue()
    finally:
        buffer.close()

@login_required
def view_certificate(request, certificate_id):
    try:
        uuid_id = uuid.UUID(certificate_id)
        certificate = get_object_or_404(Certificate, certificate_id=uuid_id)
    except ValueError:
        return HttpResponseForbidden("Invalid certificate ID format.")
      # Check if certificate is valid
    if not certificate.is_valid:
        return HttpResponseForbidden("This certificate has been marked as invalid and cannot be viewed.")
    
    # Check if the user has permission to view this certificate
    if not request.user.is_staff and request.user != certificate.student.user:
        return HttpResponseForbidden("You don't have permission to view this certificate.")
    
    # Generate PDF
    pdf = generate_certificate_pdf(certificate)
      # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    filename = f'certificate_{certificate.course.name}_{certificate.student.user.email}.pdf'
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response.write(pdf)
    
    return response

def rate_limit(request, key_prefix, max_requests=60, timeout=60):
    """Rate limit based on IP address"""
    client_ip, _ = get_client_ip(request)
    if not client_ip:
        raise PermissionDenied("Cannot determine client IP address.")
    
    cache_key = f"rate_limit:{key_prefix}:{client_ip}"
    requests = cache.get(cache_key, 0)
    
    if requests >= max_requests:
        raise PermissionDenied("Too many requests. Please try again later.")
    
    cache.set(cache_key, requests + 1, timeout)

def get_validity_message(certificate):
    """Generate a message about certificate validity"""
    if not certificate.is_valid:
        return {
            'status': 'invalid',
            'message': "This certificate has been invalidated by the issuing authority.",
            'details': "Contact the issuing authority for more information."
        }
    
    return {
        'status': 'valid',
        'message': f"This is a valid certificate{' with grade: ' + certificate.grade if certificate.grade else ''}",
        'details': f"Course period: {certificate.start_date.strftime('%B %d, %Y')} - {certificate.end_date.strftime('%B %d, %Y') if certificate.end_date else 'Ongoing'}"
    }

@require_safe
@ensure_csrf_cookie
def verify(request):
    certificate = None
    context = {
        'error': None,
        'error_type': None,
        'certificate_id': None
    }
    
    certificate_id = request.GET.get('certificate_id')
    if not certificate_id:
        context.update({
            'error_type': 'missing_id',
            'error': "No certificate ID was provided.",
            'help_text': "Please provide a valid certificate ID in the URL."
        })
        return render(request, 'certificates/verify.html', context)

    context['certificate_id'] = certificate_id
    
    try:
        certificate_uuid = uuid.UUID(certificate_id)
    except ValueError:
        context.update({
            'error_type': 'invalid_format',
            'error': "The provided certificate ID is not in the correct format.",
            'help_text': "Certificate IDs should be in UUID format. Please check if you copied the complete ID."
        })
        return render(request, 'certificates/verify.html', context)
    
    try:
        certificate = Certificate.objects.get(certificate_id=certificate_uuid)
        # Get detailed validity status
        validity_info = get_validity_message(certificate)
        is_valid = validity_info['status'] == 'valid'
        
        context.update({
            'certificate': certificate,
            'is_valid': is_valid,
            'validity_info': validity_info,
        })
    except Certificate.DoesNotExist:
        context.update({
            'error_type': 'not_found',
            'error': "The requested certificate could not be found in our system.",
            'help_text': "Please verify that you have entered the correct certificate ID. If you believe this is an error, contact the issuing authority."
        })
    
    return render(request, 'certificates/verify.html', context)

def home(request):
    return render(request, 'certificates/home.html')

def course_list(request):
    courses = Course.objects.all().order_by('name')
    return render(request, 'certificates/course_list.html', {
        'courses': courses
    })

@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            if hasattr(user, 'student'):
                user.student.require_password_change = False
                user.student.save()
            messages.success(request, 'Your password was successfully updated!')
            return redirect('certificates:dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'certificates/password_change.html', {'form': form})

def password_change_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                student = Student.objects.get(user=request.user)
                if student.require_password_change:
                    return redirect('certificates:password_change')
            except Student.DoesNotExist:
                pass
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Update existing views to use the password_change_required decorator
@login_required
@password_change_required
def dashboard(request):
    certificates = Certificate.objects.filter(student__user=request.user).order_by('-issue_date')
    return render(request, 'certificates/dashboard.html', {
        'certificates': certificates
    })
