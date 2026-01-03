#!/bin/bash

# 1. Start the email reminder script in the background
python send_reminders.py &

# 2. Start the web server and bind it to port 8000
# (This ensures Koyeb's health check passes)
gunicorn app:app --bind 0.0.0.0:8000