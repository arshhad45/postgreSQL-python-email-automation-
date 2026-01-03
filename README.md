# 📧 PostgreSQL Loan Payment Reminder & Automation System

A backend automation system that sends **loan payment reminder emails**, provides a **payment link**, updates **payment status in PostgreSQL**, and sends a **confirmation email after payment**.

Built using **Python, Flask, PostgreSQL (Neon), SMTP**, automated with **GitHub Actions**, and deployed on **Koyeb**.

---

## 🚀 Features

- Automated loan payment reminder emails
- PostgreSQL database using Neon
- Dynamic payment link generation
- Payment status tracking (UNPAID → PAID)
- Confirmation email after successful payment
- Email activity logging
- Flask backend deployed on Koyeb
- Scheduled automation using GitHub Actions

---

## 🛠 Tech Stack

- **Backend:** Python, Flask  
- **Database:** PostgreSQL (Neon)  
- **Email:** Gmail SMTP  
- **Automation:** GitHub Actions (Cron Jobs)  
- **Deployment:** Koyeb  
- **Database Driver:** psycopg2  

---

## 📂 Project Structure
├── app.py # Flask payment service
- ├── send_email.py # Email automation script
- ├── requirements.txt
- ├── .env # Environment variables (local)
- ├── .github/
- │   └── workflows/
- │ └── email_cron.yml # GitHub Actions automation
- └── README.md


