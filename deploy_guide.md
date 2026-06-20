# CIRRUS Deployment Guide (AWS & Vercel)

This document provides a step-by-step guide to deploying the CIRRUS Cloud Space Pooling application live. It utilizes **AWS** for hosting the FastAPI backend, **Supabase** for the PostgreSQL database, and **Vercel** for the React frontend.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    User([End User Browser])
    Vercel[Vercel Frontend - React/Vite]
    AWS[AWS Backend - FastAPI/Uvicorn]
    Supabase[(Supabase - PostgreSQL)]
    Clouds[(Google Drive / Dropbox)]

    User -->|Serves Web UI| Vercel
    User -->|API Requests & Auth| AWS
    AWS -->|Reads/Writes Metadata & User Auth| Supabase
    AWS -->|Uploads/Downloads Compressed Files| Clouds
```

---

## 🗄️ Step 1: Database Setup (Supabase)
*Note: Your database connection is already successfully set up and migrated. These are references for production configuration.*

1. Log in to [Supabase](https://supabase.com/).
2. Create or navigate to your project.
3. Retrieve your PostgreSQL connection string from **Project Settings → Database → Connection string → URI**.
4. Encode your password correctly if it contains special characters (escaped using URL percent encoding).

---

## 🐍 Step 2: Backend Deployment (AWS EC2)

We recommend deploying the FastAPI backend on an **AWS EC2** instance (e.g., Ubuntu 22.04 LTS or 24.04 LTS).

### 1. Launch an EC2 Instance
- **OS**: Choose **Ubuntu 22.04 LTS** or **Ubuntu 24.04 LTS** (64-bit x86).
- **Instance Type**: Select `t2.micro` or `t3.micro` (Free Tier eligible).
- **Key Pair**: Create or use an existing SSH key pair and save the `.pem` key securely.
- **Security Group (Firewall)**:
  - Add inbound rule: **SSH** (Port 22) from your IP.
  - Add inbound rule: **HTTP** (Port 80) from anywhere.
  - Add inbound rule: **HTTPS** (Port 443) from anywhere.

### 2. Connect to the EC2 Instance
Open your terminal and SSH into the instance using your key pair:
```bash
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip
```

### 3. Install System Dependencies & Python Setup
Update packages, add the Deadsnakes PPA to access stable Python versions, and install Python 3.12, Nginx, Git, and PostgreSQL development headers:
```bash
sudo apt update && sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev nginx git libpq-dev build-essential -y
```

### 4. Clone and Prepare the Application
Clone the codebase, navigate to the backend, set up a virtual environment using Python 3.12, and install dependencies:
```bash
git clone https://github.com/Acapcoder/ciruss.git
cd ciruss/backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a persistent environment configurations file `.env` inside the `backend/` directory:
```bash
nano .env
```
Paste and fill in the following configurations (replacing with your secure secrets):
```env
DATABASE_URL=postgresql://your_db_user:your_db_password@your_db_host:5432/your_db_name
CIRRUS_SECRET_KEY=your_fernet_secret_key_here
CIRRUS_JWT_SECRET=your_jwt_signing_secret_here
CIRRUS_BACKEND_URL=https://api.yourdomain.com
```
*Note: Secure the file permissions so other system users cannot read it:*
```bash
chmod 600 .env
```

### 6. Create a Systemd Service (Daemonize Backend)
Create a systemd unit file so Uvicorn runs continuously in the background and restarts automatically:
```bash
sudo nano /etc/systemd/system/cirrus-backend.service
```
Paste the following configurations:
```ini
[Unit]
Description=CIRRUS FastAPI Backend Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ciruss/backend
ExecStart=/home/ubuntu/ciruss/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
EnvironmentFile=/home/ubuntu/ciruss/backend/.env

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cirrus-backend
sudo systemctl start cirrus-backend
sudo systemctl status cirrus-backend
```

### 7. Configure Nginx as a Reverse Proxy
Create an Nginx configuration file to redirect external traffic (HTTP/HTTPS) on port 80/443 to the Uvicorn daemon running on port 8000:
```bash
sudo nano /etc/nginx/sites-available/cirrus
```
Paste the following configuration (replace `your-domain.com` with your actual domain name, or use the EC2 public IP if you don't have a domain configured yet):
```nginx
server {
    listen 80;
    server_name your-domain.com your-ec2-public-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Max upload size limit (adjust if uploading large files)
        client_max_body_size 100M;
    }
}
```
Link the file to enable the site, test configurations, and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/cirrus /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Obtain an SSL Certificate (Certbot Let's Encrypt)
Secure the EC2 endpoint with free trusted SSL keys (mandatory for Google/Dropbox OAuth redirect callbacks to function securely):
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```
Follow the interactive prompts to enable automatic HTTP-to-HTTPS redirects.

---


## ⚛️ Step 3: Frontend Deployment (Vercel)

The React frontend is deployed to Vercel and compiled on build.

1. **Sign Up / Log In**:
   - Go to [Vercel](https://vercel.com/) and connect your GitHub account.
2. **Import Project**:
   - Click **Add New → Project**.
   - Select your repository (`ciruss`).
3. **Configure Root & Build Settings**:
   - **Framework Preset**: Select **Vite** (Vercel automatically detects it).
   - **Root Directory**: Select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. **Environment Variables**:
   - Add the following Environment Variable in the configuration panel:
     - **Key**: `VITE_API_BASE_URL`
     - **Value**: Your live AWS backend URL (e.g., `https://cirrus-backend-env.eba-xxxx.amazonaws.com` — *no trailing slash*).
5. **Deploy**:
   - Click **Deploy**. Vercel will build the React bundle and provision a live HTTPS URL.

---

## ⚙️ Step 4: OAuth App Configuration

Once your frontend and backend are deployed live, update the callback redirect URIs inside your developer consoles:

1. **Google Cloud Console** (for Google Drive):
   - Navigate to **API & Services → Credentials → OAuth 2.0 Client IDs**.
   - Add the production redirect URI to **Authorized redirect URIs**:
     - `https://[YOUR_AWS_BACKEND_DOMAIN]/api/oauth/gdrive/callback`
2. **Dropbox App Console**:
   - Navigate to **My Apps → [Your Cirrus App] → OAuth 2**.
   - Add the production redirect URI to **Redirect URIs**:
     - `https://[YOUR_AWS_BACKEND_DOMAIN]/api/oauth/dropbox/callback`
3. Update the `backend/oauth_secrets.json` or configure the environment variables `CIRRUS_GDRIVE_CLIENT_ID`, `CIRRUS_GDRIVE_CLIENT_SECRET`, etc. in your AWS Environment Properties.

---

## 🛡️ Production Security Checklist
- [ ] **Rotate Supabase Password**: Change your Supabase DB password immediately (Supabase Dashboard → Database Settings) to protect it since it was exposed in chat. Update the `DATABASE_URL` environment property in AWS.
- [ ] **Disable Mock Storage**: For production, ensure no user connects mock accounts by checking environment constraints.
- [ ] **Configure CORS**: Limit `allow_origins` in `main.py` specifically to your Vercel domains rather than `["*"]` for absolute security.
