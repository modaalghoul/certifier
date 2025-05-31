# Import required environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

Write-Host "Starting deployment process..."

# Install or upgrade pip
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..."
pip install -r requirements.txt

# Run migrations
Write-Host "Running database migrations..."
python manage.py migrate

# Collect static files
Write-Host "Collecting static files..."
python manage.py collectstatic --noinput

# Create super user if needed
$CREATE_SUPERUSER = Read-Host "Do you want to create a superuser? (y/n)"
if ($CREATE_SUPERUSER -eq 'y') {
    python manage.py createsuperuser
}

Write-Host "Deployment setup completed!"
Write-Host "Please make sure to:"
Write-Host "1. Configure your web server (Nginx/Apache)"
Write-Host "2. Setup SSL certificates"
Write-Host "3. Configure your database"
Write-Host "4. Start Gunicorn with: gunicorn certifier.wsgi:application"
