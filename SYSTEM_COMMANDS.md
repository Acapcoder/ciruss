# Linux & Systemd Server Management Commands Cheat Sheet

This document lists essential Linux, Nginx, and Systemd commands used to deploy, monitor, and manage the **CIRRUS FastAPI Backend** on the AWS EC2 instance. It serves as a handy guide for server demos, troubleshooting, and viva preparation.

---

## ⚙️ 1. Systemd (Service Manager) Commands
These control the background FastAPI service daemon (`cirrus-backend.service`).

| Command | Action |
|---------|--------|
| `sudo systemctl status cirrus-backend` | Check if the backend is currently active (running) or stopped/crashed. |
| `sudo systemctl start cirrus-backend` | Start the backend service. |
| `sudo systemctl stop cirrus-backend` | Stop the backend service. |
| `sudo systemctl restart cirrus-backend` | Stop and restart the service (used to apply backend code updates). |
| `sudo systemctl enable cirrus-backend` | Configure the service to start automatically whenever the EC2 server boots. |
| `sudo systemctl disable cirrus-backend` | Prevent the service from starting automatically on boot. |
| `sudo systemctl daemon-reload` | Reload systemd configurations (must run this if you modify `cirrus-backend.service`). |

---

## 📊 2. Journalctl (System Logs) Commands
Used to inspect, tail, and troubleshoot application logs and traceback errors.

| Command | Action |
|---------|--------|
| `sudo journalctl -u cirrus-backend -f` | Follow the backend logs live (real-time stream of incoming API requests/errors). |
| `sudo journalctl -u cirrus-backend -n 50 --no-pager` | View the last 50 lines of logs without entering page scroll mode. |
| `sudo journalctl -u cirrus-backend --since "1 hour ago"` | View logs generated within the last hour. |
| `sudo journalctl -u cirrus-backend --since "today"` | View all logs generated since midnight. |
| `sudo journalctl -u cirrus-backend -p err` | View only error logs (ignoring standard info and debug logs). |

---

## 🌐 3. Nginx (Reverse Proxy & Web Server) Commands
Nginx routes incoming HTTP (80) and HTTPS (443) traffic to the Uvicorn FastAPI server on port 8000.

| Command | Action |
|---------|--------|
| `sudo nginx -t` | Test Nginx configuration files for syntax errors before reloading. |
| `sudo systemctl restart nginx` | Restart the Nginx web server. |
| `sudo systemctl status nginx` | Check if Nginx is running and listening for web traffic. |
| `sudo tail -f /var/log/nginx/access.log` | Follow incoming web traffic requests hit list in real-time. |
| `sudo tail -f /var/log/nginx/error.log` | Check Nginx-specific forwarding errors (e.g., `502 Bad Gateway` issues). |
| `sudo nano /etc/nginx/sites-available/cirrus` | Edit the site's forwarding and domain configuration file. |

---

## 📁 4. Linux File System & Directory Commands
Basic commands to navigate directories, inspect files, and check permissions.

| Command | Action |
|---------|--------|
| `pwd` | Print Working Directory (shows your current absolute folder path). |
| `ls -la` | List all files in the current directory (including hidden ones like `.env` and `.git`). |
| `cd ciruss/backend` | Navigate to the backend application folder. |
| `cat .env` | Print the contents of the environment configuration file to the terminal screen. |
| `nano .env` | Open the command-line text editor to modify configurations/keys. |
| `chmod 600 .env` | Restrict `.env` file permissions so only the owner can read/write it (crucial for security). |
| `df -h` | Display available and used disk space on the EC2 instance in human-readable gigabytes. |
| `du -sh *` | Check the size of each file/folder in the current directory (helps find large log files). |

---

## 🐍 5. Python, Virtual Environment, & Manual Runs
Manage Python packages and test running the backend server manually.

| Command | Action |
|---------|--------|
| `source venv/bin/activate` | Activate the Python virtual environment (so pip uses the local workspace packages). |
| `deactivate` | Exit the current virtual environment. |
| `pip install -r requirements.txt` | Install or update backend dependencies. |
| `pip list` | View all installed packages and their versions inside the virtual environment. |
| `uvicorn main:app --host 127.0.0.1 --port 8000` | Run the backend server manually to inspect console outputs in foreground. |

---

## 🔌 6. Network & Port Diagnostics
Diagnose which services are listening on which ports (FastAPI on 8000, Nginx on 80/443).

| Command | Action |
|---------|--------|
| `sudo ss -tulnp` or `sudo netstat -tulnp` | List all active listening ports and the system process IDs (PIDs) running them. |
| `curl -I http://127.0.0.1:8000/docs` | Ping the local FastAPI uvicorn daemon internally to check if it's responding. |
| `curl -I https://api.yourdomain.com/docs` | Test the external, secure HTTPS API gateway connectivity. |
