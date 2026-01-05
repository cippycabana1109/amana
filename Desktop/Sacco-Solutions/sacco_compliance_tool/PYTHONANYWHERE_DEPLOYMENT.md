# PythonAnywhere Deployment Guide for Vimbatech

## Step 1: Create PythonAnywhere Account
1. Go to https://pythonanywhere.com
2. Click "Create Free Account"
3. Choose "Free" tier
4. Verify your email address

## Step 2: Upload Your Files
Since you have your code on GitHub, the easiest way is:

### Option A: Using Git (Recommended)
1. In PythonAnywhere console:
```bash
git clone https://github.com/CippyCabana1109/amana.git
cd amana
```

### Option B: Manual Upload
1. Create a zip file of your project (exclude __pycache__ and .git)
2. Upload via PythonAnywhere web interface
3. Extract the files

## Step 3: Set Up Virtual Environment
In PythonAnywhere console:
```bash
cd amana
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 4: Configure Flask App
1. Go to "Web" tab in PythonAnywhere
2. Click "Add a new web app"
3. Choose "Manual Configuration"
4. Python version: 3.10
5. Set path to your project: `/home/yourusername/amana`

## Step 5: Update WSGI Configuration
Edit the WSGI file:
```python
import sys
import os

# Add your project to the Python path
project_home = '/home/yourusername/amana'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import your Flask app
from app import app as application

# Configure Flask
application.secret_key = 'your-secret-key-here'
```

## Step 6: Set Environment Variables (Optional)
In PythonAnywhere Web tab, add environment variables:
- FLASK_ENV=production
- SECRET_KEY=your-secret-key

## Step 7: Test Your App
1. Reload your web app
2. Visit yourapp.pythonanywhere.com
3. Test login: admin/admin123

## Step 8: Configure Custom Domain (Optional)
1. Purchase domain (vimbatech.co.ke)
2. In PythonAnywhere Web tab, add domain
3. Update DNS settings

## Step 9: Setup Database (Optional)
PythonAnywhere offers MySQL:
1. Go to "Databases" tab
2. Create new database
3. Update your app.py to use MySQL instead of CSV files

## Troubleshooting

### If you get 500 error:
1. Check error logs in PythonAnywhere
2. Make sure all dependencies are installed
3. Verify file permissions

### If static files don't load:
1. In Web tab, set static files path
2. Path: `/home/yourusername/amana/static`
3. URL: `/static`

### If uploads don't work:
1. Check folder permissions
2. Create uploads folder: `mkdir uploads`
3. Set permissions: `chmod 755 uploads`

## Your URLs After Deployment
- Main app: yourusername.pythonanywhere.com
- Landing page: yourusername.pythonanywhere.com/landing
- Dashboard: yourusername.pythonanywhere.com/dashboard

## Next Steps
1. Test all functionality
2. Setup custom domain
3. Configure payment processing
4. Add SSL certificate (free on PythonAnywhere)
