# Deployment Checklist

## Before Deployment
1. Environment Setup
   - [ ] Create .env file from .env.example
   - [ ] Generate new SECRET_KEY
   - [ ] Set DEBUG=False
   - [ ] Configure ALLOWED_HOSTS
   - [ ] Setup PostgreSQL database
   - [ ] Configure email settings

2. Static Files
   - [ ] Ensure all static files are in place
   - [ ] Run python manage.py collectstatic
   - [ ] Verify certificate background images are in certificates/static/certificates/images/

3. Database
   - [ ] Backup existing SQLite database
   - [ ] Configure PostgreSQL settings in .env
   - [ ] Run migrations on production database

4. Security
   - [ ] Enable HTTPS
   - [ ] Configure SSL certificate
   - [ ] Review security settings in settings.py
   - [ ] Remove any default/test passwords
   - [ ] Update admin passwords

## Deployment Steps
1. Server Setup
   - [ ] Install Python 3.9+
   - [ ] Install PostgreSQL
   - [ ] Install required system packages
   - [ ] Create virtual environment
   - [ ] Install requirements: pip install -r requirements.txt

2. Application Setup
   - [ ] Clone repository
   - [ ] Configure environment variables
   - [ ] Run migrations: python manage.py migrate
   - [ ] Collect static files: python manage.py collectstatic
   - [ ] Create superuser: python manage.py createsuperuser

3. Web Server Setup
   - [ ] Configure Gunicorn
   - [ ] Setup Nginx/Apache as reverse proxy
   - [ ] Configure SSL certificates
   - [ ] Setup static file serving

4. Monitoring Setup
   - [ ] Configure logging
   - [ ] Setup backup system
   - [ ] Configure monitoring tools

## Post-Deployment
1. Testing
   - [ ] Test all URLs
   - [ ] Verify static files are serving correctly
   - [ ] Test certificate generation
   - [ ] Test certificate verification
   - [ ] Test user authentication
   - [ ] Test admin interface

2. Maintenance
   - [ ] Setup regular backups
   - [ ] Configure error notifications
   - [ ] Document deployment process
   - [ ] Setup monitoring alerts
