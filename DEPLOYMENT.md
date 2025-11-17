# Deployment Guide for Smash Platform

## Issue: Static and Media Files Not Loading on PaaS

### Problem

When deploying to PaaS (like Railway, Heroku, or PythonAnywhere), static files (images, CSS, JS) are not served because:

1. Django's development server (`runserver`) serves static files automatically, but production servers don't.
2. You need to collect all static files to a single directory and configure the server to serve them.

### Solution

#### 1. Updated Settings (`settings.py`)

Added `STATIC_ROOT` for collecting static files:

```python
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # For production collectstatic
```

#### 2. Updated URLs (`urls.py`)

Added proper static file serving for both development and production:

```python
# Serve media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files (works in both development and production)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
else:
    # In production, serve static files from STATIC_ROOT
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
```

#### 3. Before Deploying to PaaS

Run this command to collect all static files:

```bash
python manage.py collectstatic --noinput
```

Or use the provided batch script:

```bash
collect_static.bat
```

This will:

-   Copy all files from `STATICFILES_DIRS` to `STATIC_ROOT` (staticfiles folder)
-   Copy all static files from installed apps

#### 4. Update `.gitignore`

Make sure you're committing the staticfiles folder if your PaaS requires it:

If using a PaaS with build process (Railway, Heroku):

```gitignore
# Keep staticfiles/ in git if PaaS needs it
# staticfiles/
```

If PaaS runs collectstatic during deployment:

```gitignore
# Ignore staticfiles/ - will be generated during deployment
staticfiles/
```

#### 5. PaaS-Specific Configuration

##### For PythonAnywhere / Generic PaaS:

1. Run `python manage.py collectstatic` locally or on server
2. Ensure `staticfiles/` folder is uploaded
3. Configure web server to serve `/static/` from `staticfiles/` directory

##### For Railway / Heroku:

1. Add to your `Procfile`:

    ```
    release: python manage.py collectstatic --noinput
    web: gunicorn smash.wsgi
    ```

2. Or add to your deployment script:
    ```bash
    python manage.py migrate
    python manage.py collectstatic --noinput
    ```

#### 6. Media Files (User Uploads)

For media files (like uploaded post images):

-   In development: Django serves them from `MEDIA_ROOT`
-   In production: Consider using cloud storage (AWS S3, Cloudinary, etc.) or configure your web server to serve the `media/` directory

##### Option A: Use Cloud Storage (Recommended for production)

Install django-storages:

```bash
pip install django-storages boto3  # for AWS S3
# or
pip install django-storages[google]  # for Google Cloud Storage
```

##### Option B: Serve locally (not recommended for large scale)

Ensure media files are served via your web server configuration.

#### 7. Verify Deployment

After deploying:

1. Check that `STATIC_ROOT/images/user-profile.png` exists
2. Visit `https://your-domain.com/static/images/logo-smash.png`
3. Check browser console for 404 errors
4. Verify `DEBUG = False` in production settings

#### 8. Troubleshooting

**404 errors for static files:**

-   Run `python manage.py collectstatic` again
-   Check `STATIC_ROOT` path exists
-   Verify files are in `staticfiles/` directory

**Images still not loading:**

-   Clear browser cache
-   Check file paths in templates use `{% static 'path/to/file' %}`
-   Verify `{% load static %}` is at top of templates

**Media files (uploads) not working:**

-   Check `MEDIA_ROOT` and `MEDIA_URL` settings
-   Verify upload directory has write permissions
-   Consider using cloud storage for production

## Additional Notes

### Environment Variables

Make sure these are set in production:

```env
PRODUCTION=true
DEBUG=false
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=your-domain.com
```

### Security Checklist

-   [ ] `DEBUG = False` in production
-   [ ] `SECRET_KEY` is from environment variable
-   [ ] `ALLOWED_HOSTS` configured properly
-   [ ] `CSRF_TRUSTED_ORIGINS` includes your domain
-   [ ] Static files collected
-   [ ] Database migrations applied
-   [ ] Media upload directory configured

### Commands Reference

```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Check deployment settings
python manage.py check --deploy
```
