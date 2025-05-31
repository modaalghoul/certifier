from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django import forms
from .models import Course, Certificate, Student
import random
import string

# Customize the User admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# We don't need to register User model as it's already registered by django.contrib.auth

class StudentForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Student first name')
    last_name = forms.CharField(max_length=30, required=True, help_text='Student last name')
    email = forms.EmailField(required=True, help_text='Will be used as username')
    phone = forms.CharField(max_length=20, required=True, help_text='Contact phone number (will be initial password)')

    class Meta:
        model = Student
        fields = ('phone',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if not instance.pk:  # New student
            user = User.objects.create(
                username=self.cleaned_data['email'],
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name']
            )
            # Use phone number as the initial password
            temp_password = self.cleaned_data['phone']
            user.set_password(temp_password)
            user.save()
            instance.user = user
            instance._temp_password = temp_password
            instance.require_password_change = True
        else:  # Existing student
            instance.user.username = self.cleaned_data['email']
            instance.user.email = self.cleaned_data['email']
            instance.user.first_name = self.cleaned_data['first_name']
            instance.user.last_name = self.cleaned_data['last_name']
            instance.user.save()
        
        if commit:
            instance.save()
        
        if hasattr(instance, '_temp_password'):
            self.instance._temp_password = instance._temp_password
            
        return instance

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration', 'created_at')
    search_fields = ('name', 'description')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('formatted_certificate_id', 'get_student_name', 'course', 'issue_date', 'start_date', 'end_date', 'grade', 'is_valid')
    list_filter = ('is_valid', 'course', 'issue_date')
    search_fields = ('certificate_id', 'student__user__email', 'student__user__first_name', 
                    'student__user__last_name', 'course__name', 'grade')
    readonly_fields = ('certificate_id',)
    actions = ['invalidate_certificates', 'revalidate_certificates']

    def get_student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.email
    get_student_name.short_description = 'Student'
    
    def formatted_certificate_id(self, obj):
        return str(obj.certificate_id)
    formatted_certificate_id.admin_order_field = 'certificate_id'
    formatted_certificate_id.short_description = 'Certificate ID'

    def invalidate_certificates(self, request, queryset):
        updated = queryset.update(is_valid=False)
        self.message_user(request, f'{updated} certificates were marked as invalid.')
    invalidate_certificates.short_description = "Mark selected certificates as invalid"

    def revalidate_certificates(self, request, queryset):
        updated = queryset.update(is_valid=True)
        self.message_user(request, f'{updated} certificates were marked as valid.')
    revalidate_certificates.short_description = "Mark selected certificates as valid"

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentForm
    list_display = ('get_full_name', 'get_email', 'phone', 'require_password_change')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone')
    list_filter = ('require_password_change',)
    actions = ['reset_student_password']

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'
    get_full_name.admin_order_field = 'user__first_name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'

    def reset_student_password(self, request, queryset):
        for student in queryset:
            # Generate a new password
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            student.user.set_password(new_password)
            student.user.save()
            student.require_password_change = True
            student.save()
            self.message_user(
                request, 
                f"Reset password for {student.user.email}: {new_password}",
                level='SUCCESS'
            )
    reset_student_password.short_description = "Reset password for selected students"

    def response_add(self, request, obj, post_url_continue=None):
        if hasattr(obj, '_temp_password'):
            self.message_user(
                request,
                f"Student created successfully. Username: {obj.user.email}, Temporary password: {obj._temp_password}",
                level='SUCCESS'
            )
        return super().response_add(request, obj, post_url_continue)
