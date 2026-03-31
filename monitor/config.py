"""
Configuration for the ERAN call center monitor.
Edit this file or use environment variables to set credentials.
"""
import os

PORTAL_URL = "https://portal.eran.org.il/CallCenter/default.aspx"
LOGIN_URL = "https://portal.eran.org.il/Account/Login"

# Credentials – prefer environment variables over hard-coded values
EMAIL = os.environ.get("ERAN_EMAIL", "")
PASSWORD = os.environ.get("ERAN_PASSWORD", "")

# How often to sample the stats (seconds). 5 min = 300.
POLL_INTERVAL_SECONDS = int(os.environ.get("ERAN_POLL_INTERVAL", "300"))

# Where to store data
DB_PATH = os.environ.get("ERAN_DB_PATH", "eran_monitor.db")

# Session cookie file (so we don't have to log in every time)
SESSION_FILE = os.environ.get("ERAN_SESSION_FILE", "eran_session.json")
