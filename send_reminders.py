import os
import smtplib
import psycopg2
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SENDER_EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")  # Change for production

if not all([DATABASE_URL, SENDER_EMAIL, PASSWORD]):
    raise ValueError("Missing environment variables. Check .env file")

SMTP_SERVER = "smtp.gmail.com"
PORT = 587

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_unpaid_customers():
    """Fetch customers with unpaid dues (including overdue)"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Fetch unpaid customers, including those with past due dates
    cur.execute("""
        SELECT id, name, email, amount, due_date, payment_status
        FROM customers
        WHERE payment_status = 'UNPAID'
        ORDER BY due_date ASC
    """)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def generate_payment_link(loan_id):
    """Generate payment link with base URL"""
    return f"{BASE_URL}/pay/{loan_id}"

def send_reminder_email(name, receiver_email, loan_id, due_date, amount, payment_link):
    """Send reminder email to customer"""
    msg = EmailMessage()
    msg["Subject"] = f"Payment Reminder: ₹{amount:.2f} due on {due_date}"
    msg["From"] = formataddr(("Loan Department", SENDER_EMAIL))
    msg["To"] = receiver_email
    
    # Determine urgency
    days_until_due = (due_date - date.today()).days if due_date else 0
    urgency = "URGENT" if days_until_due <= 2 else "REMINDER"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: #ff6b35;">{urgency}: Payment Due</h2>
                <div style="background: {'#ffebee' if urgency == 'URGENT' else '#fff3e0'}; 
                    padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p style="margin: 0; font-weight: bold;">
                        {'⚠️ Action Required: Payment is due soon!' if urgency == 'URGENT' else '📅 Friendly Reminder'}
                    </p>
                </div>
            </div>
            
            <p>Dear <strong>{name}</strong>,</p>
            
            <p>This is a reminder regarding your outstanding loan payment.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Payment Details:</h3>
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px 0;">Loan ID:</td>
                        <td style="padding: 8px 0;"><strong>{loan_id}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Amount Due:</td>
                        <td style="padding: 8px 0;"><strong style="color: #dc3545; font-size: 1.2em;">₹{amount:.2f}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Due Date:</td>
                        <td style="padding: 8px 0;">
                            <strong>{due_date.strftime('%d %B, %Y') if due_date else 'Not specified'}</strong>
                            {' <span style="color: #dc3545;">(Overdue)</span>' if due_date and due_date < date.today() else ''}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">Days Remaining:</td>
                        <td style="padding: 8px 0;">
                            {f"<strong>{days_until_due}</strong> day(s)" if due_date and days_until_due > 0 else "<strong style='color: #dc3545;'>Overdue</strong>"}
                        </td>
                    </tr>
                </table>
            </div>
            
            <p>Please click the button below to complete your payment:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{payment_link}" 
                   style="background: linear-gradient(to right, #28a745, #20c997); 
                          color: white; 
                          padding: 15px 30px; 
                          text-decoration: none; 
                          border-radius: 50px; 
                          font-weight: bold;
                          display: inline-block;">
                    🚀 Pay Now
                </a>
            </div>
            
            <p style="font-size: 0.9em; color: #666;">
                If the button doesn't work, copy and paste this link in your browser:<br>
                <code style="background: #f5f5f5; padding: 5px 10px; border-radius: 3px; word-break: break-all;">
                    {payment_link}
                </code>
            </p>
            
            <p>For any queries, please contact our support team.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                <p>Best regards,<br>
                <strong>Loan Department</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_content = f"""
{urgency}: PAYMENT REMINDER

Dear {name},

This is a reminder regarding your outstanding loan payment of ₹{amount:.2f}.

Loan Details:
- Loan ID: {loan_id}
- Amount Due: ₹{amount:.2f}
- Due Date: {due_date.strftime('%d %B, %Y') if due_date else 'Not specified'}
- Status: {'OVERDUE' if due_date and due_date < date.today() else 'PENDING'}

Please use the following link to complete your payment:
{payment_link}

For any queries, please contact our support team.

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
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {receiver_email}: {e}")
        return False

def log_email(customer_id):
    """Log email sent to customer"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO email_logs (customer_id, sent_at, status)
            VALUES (%s, %s, %s)
        """, (customer_id, datetime.now(), "SENT"))
        conn.commit()
    except Exception as e:
        print(f"⚠️ Failed to log email for ID {customer_id}: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    """Main function to send reminder emails"""
    print("=" * 50)
    print("📧 Starting Payment Reminder System")
    print("=" * 50)
    
    customers = fetch_unpaid_customers()
    
    if not customers:
        print("✅ No pending payments found. No emails sent.")
        return
    
    print(f"📊 Found {len(customers)} customers with pending payments")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for customer in customers:
        customer_id, name, email, amount, due_date, status = customer
        
        # Check if due_date is a valid date
        if due_date:
            days_until_due = (due_date - date.today()).days
            if days_until_due < 0:
                print(f"⚠️  {name}: Payment is {abs(days_until_due)} day(s) overdue")
        
        payment_link = generate_payment_link(customer_id)
        
        print(f"📨 Processing: {name} ({email}) - ₹{amount:.2f}")
        
        success = send_reminder_email(
            name=name,
            receiver_email=email,
            loan_id=customer_id,
            due_date=due_date,
            amount=amount,
            payment_link=payment_link
        )
        
        if success:
            log_email(customer_id)
            success_count += 1
            print(f"   ✅ Email sent successfully")
        else:
            fail_count += 1
            print(f"   ❌ Failed to send email")
        
        print()  # Empty line for readability
    
    print("=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"✅ Successfully sent: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total processed: {len(customers)}")
    print("=" * 50)

if __name__ == "__main__":
    main()