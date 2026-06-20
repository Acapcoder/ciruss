"""Builds a self-contained HTML report (images embedded as base64)."""
import base64, os

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
OUT = os.path.join(os.path.dirname(__file__), "CIRRUS_Report.html")


def img(name):
    with open(os.path.join(ASSETS, name), "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


IMAGES = {
    "SIGNIN": img("01_signin.png"),
    "SIGNUP": img("02_signup.png"),
    "DASHBOARD": img("03_dashboard.png"),
    "CONNECTIONS": img("04_connections.png"),
    "FILES": img("05_files.png"),
}

CSS = """
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Times New Roman", Times, serif;
    color: #000000;
    background: #ffffff;
    font-size: 12pt;
    line-height: 1.6;
    margin: 0;
  }
  .page { padding: 2.2cm 2.2cm; max-width: 21cm; margin: 0 auto; }
  h1, h2, h3, h4 { color: #000000; font-weight: bold; }
  h1.chapter { font-size: 20pt; border-bottom: 2px solid #000000; padding-bottom: 6px; margin-top: 0; }
  h2 { font-size: 15pt; margin-top: 22px; }
  h3 { font-size: 13pt; margin-top: 16px; }
  p, li { text-align: justify; }
  ul, ol { padding-left: 22px; }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 11pt; }
  th, td { border: 1px solid #000000; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { font-weight: bold; }
  figure { margin: 18px 0; text-align: center; }
  figure img { max-width: 100%; border: 1px solid #000000; }
  figcaption { font-size: 10.5pt; font-style: italic; margin-top: 6px; text-align: center; }
  code { font-family: "Courier New", monospace; font-size: 10.5pt; }

  /* Cover */
  .cover { height: 26cm; display: flex; flex-direction: column; justify-content: center;
           align-items: center; text-align: center; }
  .cover .title { font-size: 46pt; font-weight: bold; letter-spacing: 2px; }
  .cover .subtitle { font-size: 16pt; margin-top: 8px; }
  .cover .doctype { font-size: 20pt; margin-top: 40px; font-weight: bold; }
  .cover .meta { margin-top: 50px; font-size: 13pt; }
  .cover .rule { width: 60%; border-top: 1.5px solid #000000; margin: 26px auto; }

  /* Architecture diagram (pure CSS, black only) */
  .diagram { border: 1px solid #000; padding: 16px; margin: 16px 0; }
  .tier { border: 1.5px solid #000; padding: 10px 14px; margin: 8px auto; max-width: 70%;
          text-align: center; font-weight: bold; }
  .arrow { text-align: center; font-size: 14pt; }

  .toc-line { display: flex; justify-content: space-between; border-bottom: 1px dotted #000;
              padding: 5px 0; }
  .toc-line span:first-child { font-weight: normal; }

  @media print {
    .page { padding: 0; }
    h1.chapter { page-break-before: always; }
    .cover, .toc-page { page-break-after: always; }
    figure { page-break-inside: avoid; }
    @page { margin: 2cm; }
  }
</style>
"""

COVER = """
<section class="cover">
  <div class="title">CIRRUS</div>
  <div class="subtitle">Smart Multi-Cloud Storage Pooling and Compression Platform</div>
  <div class="rule"></div>
  <div class="doctype">Project Report</div>
  <div class="meta">
    <p>Submitted in partial fulfillment of the requirements of the course</p>
    <p><strong>[Course Name and Code]</strong></p>
    <p>[Department / Institution Name]</p>
  </div>
  <div class="meta">
    <p><strong>Submitted by</strong></p>
    <p>Member 1: [Full Name and Roll Number]</p>
    <p>Member 2: [Full Name and Roll Number]</p>
    <p>Member 3: [Full Name and Roll Number]</p>
    <p>Member 4: [Full Name and Roll Number]</p>
  </div>
  <div class="meta"><p>Session 2025 to 2026</p></div>
</section>
"""

TOC = """
<section class="toc-page">
  <h1 class="chapter" style="page-break-before:auto">Table of Contents</h1>
  <div class="toc-line"><span>1. Introduction</span><span>1</span></div>
  <div class="toc-line"><span>2. System Architecture</span><span>2</span></div>
  <div class="toc-line"><span>3. Database Design</span><span>3</span></div>
  <div class="toc-line"><span>4. Core Features and Implementation</span><span>4</span></div>
  <div class="toc-line"><span>5. Security and Privacy</span><span>5</span></div>
  <div class="toc-line"><span>6. User Interface</span><span>6</span></div>
  <div class="toc-line"><span>7. Deployment Architecture</span><span>7</span></div>
  <div class="toc-line"><span>8. Team Contributions</span><span>8</span></div>
  <div class="toc-line"><span>9. Conclusion and Future Work</span><span>9</span></div>
</section>
"""

BODY = """
<h1 class="chapter">1. Introduction</h1>
<h2>1.1 Overview</h2>
<p>CIRRUS is a web based platform that allows a user to connect several free cloud storage accounts, such as Google Drive and Dropbox, and use them together as a single unified storage space. Instead of treating each cloud account separately, CIRRUS pools the free quota of every connected account into one combined capacity. Every file that a user uploads is first compressed and then automatically routed to the connected cloud that currently has the largest amount of free space.</p>
<h2>1.2 Problem Statement</h2>
<p>Individual cloud providers offer only a limited amount of free storage, for example fifteen gigabytes on Google Drive and two gigabytes on Dropbox. Users frequently hold several such accounts, yet the free space remains fragmented and difficult to use as a whole. There is no convenient consumer tool that presents these scattered free allocations as one large and easy to manage storage box.</p>
<h2>1.3 Objectives</h2>
<ul>
  <li>To let users connect multiple free cloud accounts through a simple and secure sign in process.</li>
  <li>To present the combined free capacity of all connected accounts as one pooled storage box.</li>
  <li>To compress files automatically and route each file to the cloud with the most available space.</li>
  <li>To organize stored files using a unified virtual folder structure independent of the physical cloud location.</li>
  <li>To protect user accounts and cloud credentials using strong cryptographic measures.</li>
</ul>
<h2>1.4 Scope</h2>
<p>The platform supports user registration and authentication, connection of Google Drive and Dropbox accounts through the official authorization flow, compression of files, automatic storage routing, virtual folder navigation, bulk uploads, and a dashboard that reports the pooled capacity and storage savings. The system stores only metadata and encrypted credentials, while the actual file contents reside on the user owned cloud accounts.</p>

<h1 class="chapter">2. System Architecture</h1>
<h2>2.1 Architectural Overview</h2>
<p>CIRRUS follows a three tier architecture. The presentation tier is a single page web application built with React. The application tier is a backend service built with the FastAPI framework. The data tier is a managed PostgreSQL database hosted on Supabase. The backend communicates with external cloud providers through their official application programming interfaces to transfer the actual file data.</p>
<div class="diagram">
  <div class="tier">End User Web Browser</div>
  <div class="arrow">|</div>
  <div class="tier">React Frontend (hosted on Vercel)</div>
  <div class="arrow">|</div>
  <div class="tier">FastAPI Backend (hosted on Amazon Web Services)</div>
  <div class="arrow">|</div>
  <div class="tier">Supabase PostgreSQL Database (metadata and encrypted tokens)</div>
  <div class="arrow">|</div>
  <div class="tier">Google Drive and Dropbox (actual file storage)</div>
</div>
<figcaption>Figure 2.1: High level three tier architecture of the CIRRUS platform.</figcaption>
<h2>2.2 Technology Stack</h2>
<table>
  <tr><th>Layer</th><th>Technology</th><th>Purpose</th></tr>
  <tr><td>Frontend</td><td>React, Vite, React Router</td><td>User interface, routing, and client logic</td></tr>
  <tr><td>Backend</td><td>Python, FastAPI, Uvicorn</td><td>API, authentication, compression, and routing engine</td></tr>
  <tr><td>Database</td><td>PostgreSQL on Supabase</td><td>Storage of users, accounts, folders, files, and logs</td></tr>
  <tr><td>Cloud APIs</td><td>Google Drive API, Dropbox API</td><td>Physical upload, download, and quota reading</td></tr>
  <tr><td>Hosting</td><td>Amazon Web Services, Vercel</td><td>Backend server and frontend delivery</td></tr>
</table>
<h2>2.3 Data Flow</h2>
<p>When a user uploads a file, the browser sends the file to the backend together with the authentication token. The backend compresses the file, queries the live free space of every connected account, selects the account with the most available space, and uploads the compressed file to that cloud through its official interface. The backend then records the file metadata in the database and returns a direct web link to the stored file.</p>

<h1 class="chapter">3. Database Design</h1>
<h2>3.1 Overview</h2>
<p>The database consists of five related tables. The design isolates user identity, connected storage accounts, virtual folders, stored file metadata, and an activity audit trail. Each record uses a universally unique identifier as its primary key. Only metadata and encrypted credentials are persisted, and no file content is stored in the database.</p>
<h2>3.2 Tables</h2>
<table>
  <tr><th>Table</th><th>Key Columns</th><th>Description</th></tr>
  <tr><td>users</td><td>id, email, hashed_password, full_name, created_at</td><td>Registered user accounts with securely hashed passwords</td></tr>
  <tr><td>storage_accounts</td><td>id, user_id, provider, display_name, credentials_json, quota_limit, used_space</td><td>Connected cloud accounts with encrypted refresh tokens and live quota figures</td></tr>
  <tr><td>folders</td><td>id, user_id, name, parent_id, created_at</td><td>Virtual folder tree using a self reference for nesting</td></tr>
  <tr><td>stored_files</td><td>id, user_id, folder_id, account_id, original_name, compression_type, original_size, compressed_size, web_link</td><td>Metadata for every uploaded file and its physical cloud location</td></tr>
  <tr><td>audit_logs</td><td>id, user_id, action, details, timestamp</td><td>Record of user actions such as sign up, login, upload, and delete</td></tr>
</table>
<h2>3.3 Relationships</h2>
<ul>
  <li>A user owns many storage accounts, folders, files, and audit log entries.</li>
  <li>A storage account contains many stored files.</li>
  <li>A folder contains many files and may contain child folders through the parent identifier.</li>
</ul>

<h1 class="chapter">4. Core Features and Implementation</h1>
<h2>4.1 Storage Pooling</h2>
<p>The platform aggregates the free capacity of every connected account. The free space of an account is computed as the quota limit minus the used space, and the dashboard reports the sum across all accounts as a single pooled figure.</p>
<h2>4.2 Compression and Smart Routing</h2>
<p>Each uploaded file is compressed using the gzip or zip algorithm before transfer. The routing engine then selects the connected account with the greatest free space and uploads the compressed file to that account. This approach balances usage across accounts and maximizes the effective capacity of the pool.</p>
<h2>4.3 Virtual Folders and Bulk Upload</h2>
<p>Files are organized through a unified virtual folder tree maintained in the database. A single folder may contain files that physically reside on different clouds, which preserves the concept of one combined storage box. The file manager supports selecting and uploading many files at once, and each file in a batch is routed independently.</p>
<h2>4.4 Activity Dashboard</h2>
<p>The dashboard summarizes the total number of files, the combined usage and limit, the space saved through compression, and a recent activity log. It provides the user with a clear and immediate understanding of the state of the pooled storage.</p>

<h1 class="chapter">5. Security and Privacy</h1>
<h2>5.1 Authentication</h2>
<p>User accounts are protected with passwords that are hashed using a salted PBKDF2 function based on the SHA256 algorithm. Sessions are maintained using signed JSON Web Tokens that expire after a fixed period.</p>
<h2>5.2 Credential Encryption</h2>
<p>Cloud authorization is performed using the official authorization code flow, which means the platform never receives or stores user passwords for the connected clouds. The resulting refresh tokens are encrypted at rest using symmetric Fernet encryption before they are written to the database.</p>
<h2>5.3 Audit Logging</h2>
<p>Significant actions, including registration, login, upload, and deletion, are recorded in an audit log table associated with the user. This provides traceability and supports accountability within the system.</p>

<h1 class="chapter">6. User Interface</h1>
<p>The interface uses a clean red and white visual theme. The following figures present the principal screens of the platform.</p>
<figure><img src="@SIGNIN@"><figcaption>Figure 6.1: Sign in screen for returning users.</figcaption></figure>
<figure><img src="@SIGNUP@"><figcaption>Figure 6.2: Registration screen with agreement to the terms of service and privacy policy.</figcaption></figure>
<figure><img src="@DASHBOARD@"><figcaption>Figure 6.3: Dashboard showing pooled usage, compression savings, and recent activity.</figcaption></figure>
<figure><img src="@CONNECTIONS@"><figcaption>Figure 6.4: Cloud connections screen for linking Google Drive and Dropbox accounts.</figcaption></figure>
<figure><img src="@FILES@"><figcaption>Figure 6.5: File manager with folder navigation, search, and bulk upload.</figcaption></figure>

<h1 class="chapter">7. Deployment Architecture</h1>
<p>The application is deployed as a live service. The frontend is built and served through Vercel. The backend runs on an Amazon Web Services instance behind a reverse proxy with a trusted certificate, which is required for secure authorization callbacks. The database is the managed PostgreSQL service provided by Supabase. Application secrets, including the database connection string and signing keys, are stored as protected environment variables and are never committed to the source repository.</p>

<h1 class="chapter">8. Team Contributions</h1>
<p>The project was completed by a team of four members. The responsibilities were divided into four distinct layers so that the workload was balanced and the areas of ownership did not overlap.</p>
<h2>8.1 Member 1, Backend Core and Database</h2>
<p>The first member was responsible for the backend service and the data layer. This member designed the relational schema of five tables, configured the PostgreSQL database on Supabase, and implemented the database migration logic. The member also developed the core application programming interface for files, folders, and dashboard statistics, and built the compression pipeline together with the smart routing engine that selects the emptiest cloud for each upload.</p>
<h2>8.2 Member 2, Authentication and Security</h2>
<p>The second member was responsible for all matters of authentication and security. This member implemented user registration and login, the salted password hashing scheme, and the signed token based session system. The member also implemented the symmetric encryption of cloud credentials at rest and developed the audit logging mechanism that records significant user actions.</p>
<h2>8.3 Member 3, Cloud Integration</h2>
<p>The third member was responsible for the integration with external cloud providers. This member implemented the official authorization code flow for Google Drive and Dropbox, including the secure handling and refreshing of access tokens. The member also developed the storage client layer that performs upload, download, deletion, live quota reading, and the generation of direct web links to stored files.</p>
<h2>8.4 Member 4, Frontend and Deployment</h2>
<p>The fourth member was responsible for the web application and its delivery. This member built the React interface, including the dashboard, the cloud connections manager, and the file manager with folder navigation and bulk upload. The member also designed the red and white visual theme and the guidance tooltips, and carried out the deployment of the frontend, backend, and database to their respective hosting platforms.</p>

<h1 class="chapter">9. Conclusion and Future Work</h1>
<h2>9.1 Conclusion</h2>
<p>CIRRUS successfully demonstrates that fragmented free cloud allocations can be unified into a single and practical storage box. The platform combines secure authentication, encrypted credential handling, file compression, intelligent routing, and a clear user interface into a complete and deployed product.</p>
<h2>9.2 Future Work</h2>
<ul>
  <li>Adding support for further providers such as OneDrive once organizational restrictions are resolved.</li>
  <li>Implementing the splitting of very large files across multiple clouds with automatic reassembly on download.</li>
  <li>Introducing file sharing between users and richer search and preview capabilities.</li>
</ul>
"""

body = BODY
for token, uri in IMAGES.items():
    body = body.replace(f"@{token}@", uri)

html = "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>CIRRUS Project Report</title>" \
       + CSS + "</head><body><div class=\"page\">" + COVER + TOC + body + "</div></body></html>"

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("Report written to", OUT, "size", round(len(html) / 1024), "KB")
