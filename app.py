import os
import smtplib
import psycopg2
from email.message import EmailMessage
from email.utils import formataddr
from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SENDER_EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not all([DATABASE_URL, SENDER_EMAIL, PASSWORD]):
    raise ValueError("Missing environment variables. Check .env file")

SMTP_SERVER = "smtp.gmail.com"
PORT = 587

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- PAYMENT PAGE ----------------
@app.route("/pay/<loan_id>")
def payment_page(loan_id):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Fetch customer details
        cur.execute("""
            SELECT id, name, amount, email 
            FROM customers 
            WHERE id = %s AND payment_status = 'UNPAID'
        """, (loan_id,))
        
        customer = cur.fetchone()
        
        if not customer:
            return render_template_string("""
                <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                    <h2 style="color: #dc3545;">Payment Link Expired</h2>
                    <p>This payment has already been processed or the link is invalid.</p>
                </div>
            """)
        
        customer_id, name, amount, email = customer
        
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payment Portal</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        max-width: 500px;
                        width: 90%;
                        text-align: center;
                    }
                    h2 {
                        color: #333;
                        margin-bottom: 30px;
                    }
                    .info-box {
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        text-align: left;
                    }
                    .info-item {
                        margin: 10px 0;
                        display: flex;
                        justify-content: space-between;
                    }
                    .amount {
                        font-size: 2em;
                        color: #28a745;
                        font-weight: bold;
                        margin: 20px 0;
                    }
                    .pay-button {
                        background: linear-gradient(to right, #28a745, #20c997);
                        color: white;
                        border: none;
                        padding: 15px 40px;
                        font-size: 1.2em;
                        border-radius: 50px;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        margin-top: 20px;
                        width: 100%;
                    }
                    .pay-button:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 10px 20px rgba(40, 167, 69, 0.3);
                    }
                    .customer-name {
                        color: #667eea;
                        font-size: 1.5em;
                        margin-bottom: 10px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>💰 Payment Portal</h2>
                    <div class="customer-name">Hello, {{ name }}</div>
                    
                    <div class="info-box">
                        <div class="info-item">
                            <span>Loan ID:</span>
                            <span><strong>{{ loan_id }}</strong></span>
                        </div>
                        <div class="info-item">
                            <span>Due Amount:</span>
                            <span class="amount">₹{{ "%.2f"|format(amount) }}</span>
                        </div>
                    </div>
                    
                    <form action="/pay/confirm/{{ loan_id }}" method="POST">
                        <button type="submit" class="pay-button">
                            🚀 Confirm & Pay Now
                        </button>
                    </form>
                    
                    <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
                        You'll receive a confirmation email after successful payment.
                    </p>
                </div>
            </body>
            </html>
        """, name=name, loan_id=loan_id, amount=amount)
        
    except Exception as e:
        return f"<h3>Error: {str(e)}</h3>"
    finally:
        cur.close()
        conn.close()

# ---------------- PAYMENT CONFIRMATION ----------------
@app.route("/pay/confirm/<loan_id>", methods=["POST"])
def confirm_payment(loan_id):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Fetch customer details
        cur.execute("""
            SELECT id, name, email, amount 
            FROM customers 
            WHERE id = %s AND payment_status = 'UNPAID'
        """, (loan_id,))
        
        customer = cur.fetchone()
        
        if not customer:
            return render_template_string("""
                <div style="text-align: center; margin-top: 50px;">
                    <h2 style="color: #dc3545;">❌ Payment Already Processed</h2>
                    <p>This payment has already been completed.</p>
                </div>
            """)
        
        customer_id, name, email, amount = customer
        
        # Update payment status
        cur.execute("""
            UPDATE customers 
            SET payment_status = 'PAID', 
                paid_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (loan_id,))
        
        # Log payment in payments table
        cur.execute("""
            INSERT INTO payments (customer_id, amount, status, payment_date) 
            VALUES (%s, %s, 'SUCCESS', CURRENT_TIMESTAMP)
        """, (customer_id, amount))
        
        conn.commit()
        
        # Send confirmation email
        send_confirmation_email(name, email, loan_id, amount)
        
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payment Successful</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        padding: 50px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        max-width: 600px;
                        width: 90%;
                        text-align: center;
                    }
                    .success-icon {
                        font-size: 4em;
                        color: #28a745;
                        margin-bottom: 20px;
                    }
                    h2 {
                        color: #333;
                        margin-bottom: 20px;
                    }
                    .details {
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        text-align: left;
                    }
                    .detail-item {
                        margin: 10px 0;
                        display: flex;
                        justify-content: space-between;
                        padding: 8px 0;
                        border-bottom: 1px solid #dee2e6;
                    }
                    .detail-item:last-child {
                        border-bottom: none;
                    }
                    .amount {
                        font-size: 1.5em;
                        color: #28a745;
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h2>Payment Successful!</h2>
                    <p>Thank you for your payment. A confirmation email has been sent to:</p>
                    <p><strong>{{ email }}</strong></p>
                    
                    <div class="details">
                        <div class="detail-item">
                            <span>Customer Name:</span>
                            <span><strong>{{ name }}</strong></span>
                        </div>
                        <div class="detail-item">
                            <span>Loan ID:</span>
                            <span><strong>{{ loan_id }}</strong></span>
                        </div>
                        <div class="detail-item">
                            <span>Amount Paid:</span>
                            <span class="amount">₹{{ "%.2f"|format(amount) }}</span>
                        </div>
                        <div class="detail-item">
                            <span>Status:</span>
                            <span style="color: #28a745; font-weight: bold;">PAID</span>
                        </div>
                        <div class="detail-item">
                            <span>Date:</span>
                            <span>{{ date }}</span>
                        </div>
                    </div>
                    
                    <p style="color: #666; margin-top: 20px;">
                        Your payment has been processed successfully. Keep this confirmation for your records.
                    </p>
                </div>
            </body>
            </html>
        """, name=name, email=email, loan_id=loan_id, amount=amount, date=date.today())
        
    except Exception as e:
        conn.rollback()
        return f"<h3>❌ Database Error: {str(e)}</h3>"
    finally:
        cur.close()
        conn.close()

# ---------------- CONFIRMATION EMAIL ----------------
def send_confirmation_email(name, receiver_email, loan_id, amount):
    msg = EmailMessage()
    msg["Subject"] = f"Payment Confirmation - Loan ID: {loan_id}"
    msg["From"] = formataddr(("Loan Department", SENDER_EMAIL))
    msg["To"] = receiver_email
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: #28a745;">✅ Payment Confirmation</h2>
            </div>
            
            <p>Dear <strong>{name}</strong>,</p>
            
            <p>We're pleased to confirm that we have successfully received your payment.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Transaction Details:</h3>
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0;">Loan Reference ID:</td>
                        <td style="padding: 8px 0;"><strong>{loan_id}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Amount Paid:</td>
                        <td style="padding: 8px 0;"><strong style="color: #28a745; font-size: 1.2em;">₹{amount:.2f}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Status:</td>
                        <td style="padding: 8px 0;"><span style="color: #28a745; font-weight: bold;">PAID</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Date:</td>
                        <td style="padding: 8px 0;">{datetime.now().strftime('%d %B, %Y %I:%M %p')}</td>
                    </tr>
                </table>
            </div>
            
            <p>Your payment has been processed and your account is now up to date.</p>
            
            <p>Thank you for your timely payment.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                <p>Best regards,<br>
                <strong>Loan Department</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text fallback
    text_content = f"""
Dear {name},

We're pleased to confirm that we have successfully received your payment.

Transaction Details:
- Loan Reference ID: {loan_id}
- Amount Paid: ₹{amount:.2f}
- Status: PAID
- Date: {datetime.now().strftime('%d %B, %Y %I:%M %p')}

Your payment has been processed and your account is now up to date.

Thank you for your timely payment.

Best regards,
Loan Department
"""
    
    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype='html')
    
    try:
        with smtplib.SMTP(SMTP_SERVER, PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.send_message(msg)
        print(f"✅ Confirmation email sent to {name} ({receiver_email})")
    except Exception as e:
        print(f"❌ Failed to send confirmation email to {receiver_email}: {e}")

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8000, debug=True)
    
