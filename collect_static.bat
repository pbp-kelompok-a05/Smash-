@echo off
REM Activate virtual environment
call env\Scripts\activate

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

echo.
echo Static files have been collected to 'staticfiles' directory.
echo.
pause
