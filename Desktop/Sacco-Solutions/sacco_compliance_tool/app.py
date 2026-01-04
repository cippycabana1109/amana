import os
import tempfile
from datetime import datetime
from functools import wraps
from io import BytesIO
import urllib.request
import urllib.parse

import pandas as pd
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash, send_file

try:
    from .fraud_model import detect_fraud, train_fraud_model
except ImportError:
    from fraud_model import detect_fraud, train_fraud_model


app = Flask(__name__)
app.secret_key = 'sacco_compliance_secret_key_2024'  # Change this in production!

# Simple user database (in production, use a proper database with hashed passwords)
USERS = {
    'admin': 'admin123',
    'compliance': 'sacco2024',
}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_report_stats():
    """Get statistics from the fraud report."""
    report_path = "compliance_fraud_report.csv"
    stats = {
        'total': 0,
        'high_risk': 0,
        'total_amount': 0,
        'model_status': 'Not Trained',
        'last_updated': 'Never'
    }
    
    if os.path.exists('fraud_model.pkl'):
        stats['model_status'] = 'Active'
    
    if os.path.exists(report_path):
        try:
            df = pd.read_csv(report_path)
            stats['total'] = len(df)
            stats['high_risk'] = len(df[df.get('compliance_flag', '') == 'High Risk']) if 'compliance_flag' in df.columns else 0
            stats['total_amount'] = df['amount'].sum() if 'amount' in df.columns else 0
            mod_time = os.path.getmtime(report_path)
            stats['last_updated'] = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d')
        except Exception:
            pass
    
    return stats


def get_transactions():
    """Get transactions from the fraud report."""
    report_path = "compliance_fraud_report.csv"
    if not os.path.exists(report_path):
        return []
    
    try:
        df = pd.read_csv(report_path)
        return df.to_dict(orient='records')
    except Exception:
        return []


@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard_view'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username in USERS and USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard_view'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup."""
    if request.method == 'POST':
        sacco_name = request.form.get('sacco_name')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # In production, save to database and send verification email
        # For now, just show success message and redirect to payment
        flash(f'Account created for {sacco_name}! Complete your setup to start your free trial.', 'success')
        return redirect(url_for('payment_page'))
    
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard_view():
    stats = get_report_stats()
    transactions = get_transactions()
    return render_template('dashboard.html', stats=stats, transactions=transactions)


@app.route('/upload')
@login_required
def upload_page():
    return render_template('upload.html')


@app.route('/reports')
@login_required
def reports_page():
    stats = get_report_stats()
    return render_template('reports.html', stats=stats)


def _save_uploaded_file(field_name: str = "file") -> str:
    if field_name not in request.files:
        raise ValueError(f"Missing upload field '{field_name}'")

    uploaded = request.files[field_name]
    if uploaded.filename is None or uploaded.filename.strip() == "":
        raise ValueError("Empty filename")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.close()
    uploaded.save(tmp.name)
    return tmp.name


@app.route('/train', methods=['POST'])
@login_required
def train():
    tmp_path = None
    try:
        tmp_path = _save_uploaded_file("file")
        train_fraud_model(tmp_path)
        flash('Model trained successfully!', 'success')
        return redirect(url_for('upload_page'))
    except Exception as e:
        flash(f'Training failed: {str(e)}', 'error')
        return redirect(url_for('upload_page'))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route('/detect', methods=['POST'])
@login_required
def detect():
    tmp_path = None
    try:
        tmp_path = _save_uploaded_file("file")
        report_df = detect_fraud(tmp_path)
        flash(f'Fraud detection complete! Found {len(report_df)} suspicious transactions.', 'success')
        return redirect(url_for('dashboard_view'))
    except Exception as e:
        flash(f'Detection failed: {str(e)}', 'error')
        return redirect(url_for('upload_page'))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route('/download/pdf')
@login_required
def download_pdf():
    """Generate and download PDF report."""
    report_path = "compliance_fraud_report.csv"
    if not os.path.exists(report_path):
        flash('No report available to download.', 'error')
        return redirect(url_for('reports_page'))
    
    try:
        df = pd.read_csv(report_path)
        
        # Generate HTML-based PDF content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; }}
                h1 {{ color: #6b46c1; border-bottom: 2px solid #6b46c1; padding-bottom: 10px; }}
                h2 {{ color: #4a5568; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background-color: #6b46c1; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                tr:nth-child(even) {{ background-color: #f7fafc; }}
                .high-risk {{ color: #dc2626; font-weight: bold; }}
                .normal {{ color: #16a34a; }}
                .summary {{ background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .summary-item {{ display: inline-block; margin-right: 40px; }}
                .summary-value {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                .summary-label {{ font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <h1>SACCO Compliance Fraud Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <div class="summary-item">
                    <div class="summary-value">{len(df)}</div>
                    <div class="summary-label">Total Flagged</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{len(df[df.get('compliance_flag', '') == 'High Risk']) if 'compliance_flag' in df.columns else 0}</div>
                    <div class="summary-label">High Risk</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">KES {df['amount'].sum():,.2f}</div>
                    <div class="summary-label">Total Amount</div>
                </div>
            </div>
            
            <h2>Flagged Transactions</h2>
            {df.to_html(index=False, classes='report-table', escape=False)}
            
            <p style="margin-top: 40px; font-size: 12px; color: #6b7280;">
                This report is confidential and intended for authorized personnel only.
            </p>
        </body>
        </html>
        """
        
        # Return as downloadable HTML (can be printed to PDF)
        buffer = BytesIO()
        buffer.write(html_content.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='text/html',
            as_attachment=True,
            download_name=f'fraud_report_{datetime.now().strftime("%Y%m%d")}.html'
        )
    except Exception as e:
        flash(f'Failed to generate report: {str(e)}', 'error')
        return redirect(url_for('reports_page'))


@app.route('/download/csv')
@login_required
def download_csv():
    """Download CSV report."""
    report_path = "compliance_fraud_report.csv"
    if not os.path.exists(report_path):
        flash('No report available to download.', 'error')
        return redirect(url_for('reports_page'))
    
    return send_file(
        report_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'fraud_report_{datetime.now().strftime("%Y%m%d")}.csv'
    )


@app.route('/send-email', methods=['POST'])
@login_required
def send_email_report():
    """Placeholder for email functionality."""
    email = request.form.get('email', '')
    subject = request.form.get('subject', 'SACCO Fraud Report')
    
    # In production, integrate with an email service (SendGrid, AWS SES, etc.)
    # For now, just show a success message
    flash(f'Report would be sent to {email} (Email service not configured yet).', 'success')
    return redirect(url_for('reports_page'))


@app.route('/download/sample')
@login_required
def download_sample():
    """Generate and download a sample CSV template."""
    sample_data = """transaction_id,member_id,type,amount,member_balance,time_of_day
TXN001,MEM001,deposit,15000,50000,09:30
TXN002,MEM002,withdrawal,8000,120000,14:15
TXN003,MEM003,loan,50000,200000,11:00
TXN004,MEM001,withdrawal,5000,45000,16:45
TXN005,MEM004,deposit,25000,75000,10:20
TXN006,MEM002,withdrawal,100000,20000,02:30
TXN007,MEM005,loan,150000,300000,13:00
TXN008,MEM003,deposit,10000,210000,08:45
"""
    buffer = BytesIO()
    buffer.write(sample_data.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='sacco_transactions_template.csv'
    )


# API endpoints for programmatic access
@app.route('/api/train', methods=['POST'])
def api_train():
    tmp_path = None
    try:
        tmp_path = _save_uploaded_file("file")
        train_fraud_model(tmp_path)
        return jsonify({"status": "success", "message": "Model trained successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route('/api/detect', methods=['POST'])
def api_detect():
    tmp_path = None
    try:
        tmp_path = _save_uploaded_file("file")
        report_df = detect_fraud(tmp_path)
        return jsonify({"status": "success", "report": report_df.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route('/landing')
def landing_page():
    """Serve the marketing landing page."""
    return send_file('landing/vimbatech_index.html')


@app.route('/pitch')
def pitch_deck():
    """Serve the pitch deck."""
    return send_file('pitch_deck.html')


# SMS Alert Configuration (Africa's Talking API - popular in Kenya)
SMS_CONFIG = {
    'api_key': os.environ.get('AT_API_KEY', ''),  # Set in environment
    'username': os.environ.get('AT_USERNAME', 'sandbox'),
    'sender_id': 'SACCOGUARD',
    'enabled': False  # Set to True when API key is configured
}


def send_sms_alert(phone_number: str, message: str) -> bool:
    """Send SMS alert using Africa's Talking API."""
    if not SMS_CONFIG['enabled'] or not SMS_CONFIG['api_key']:
        print(f"[SMS] Would send to {phone_number}: {message}")
        return False
    
    try:
        url = "https://api.africastalking.com/version1/messaging"
        data = urllib.parse.urlencode({
            'username': SMS_CONFIG['username'],
            'to': phone_number,
            'message': message,
            'from': SMS_CONFIG['sender_id']
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data)
        req.add_header('apiKey', SMS_CONFIG['api_key'])
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 201
    except Exception as e:
        print(f"[SMS] Error sending to {phone_number}: {e}")
        return False


@app.route('/payment')
def payment_page():
    """Handle payment setup."""
    return render_template('payment.html')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    """SMS and notification settings."""
    if request.method == 'POST':
        phone = request.form.get('alert_phone', '')
        session['alert_phone'] = phone
        flash(f'Alert phone number updated to {phone}', 'success')
        return redirect(url_for('settings_page'))
    
    return render_template('settings.html')


if __name__ == "__main__":
    app.run(debug=True)
