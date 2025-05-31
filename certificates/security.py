from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from functools import wraps
from ipware import get_client_ip
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponseForbidden

def admin_brute_force_protect(view_func):
    """Protect admin login from brute force attacks"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'method'):
            return view_func(request, *args, **kwargs)
            
        if request.method == 'POST':
            client_ip, _ = get_client_ip(request)
            if not client_ip:
                return HttpResponseForbidden("Cannot determine client IP address.")
            
            cache_key = f"admin_login:{client_ip}"
            failed_attempts = cache.get(cache_key, {'count': 0, 'first_attempt': None})
            
            # Reset counter if it's been more than 24 hours
            if failed_attempts['first_attempt']:
                first_attempt = failed_attempts['first_attempt']
                if timezone.now() - first_attempt > timedelta(hours=24):
                    failed_attempts = {'count': 0, 'first_attempt': None}
            
            if failed_attempts['count'] >= 5:  # Max 5 attempts
                return HttpResponseForbidden("Too many login attempts. Please try again later.")
            
            # Update attempts only if it's a failed login
            if 'username' in request.POST and not request.user.is_authenticated:
                failed_attempts['count'] += 1
                if not failed_attempts['first_attempt']:
                    failed_attempts['first_attempt'] = timezone.now()
                cache.set(cache_key, failed_attempts, 86400)  # 24 hours
        
        return view_func(request, *args, **kwargs)
    return wrapper
