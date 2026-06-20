import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import AccountsManager from './components/AccountsManager';
import FileManager from './components/FileManager';
import { Lock, Mail, User as UserIcon, LayoutDashboard, HardDrive, Files, LogOut } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://cirrusapi.buzzetric.com';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('cirrus_token') || '');
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('cirrus_user') || 'null'));
  const navigate = useNavigate();
  const location = useLocation();

  const [stats, setStats] = useState({
    total_files: 0, original_size_total: 0, compressed_size_total: 0,
    space_saved_bytes: 0, saving_ratio: 0, provider_distribution: {}, account_usage: [],
  });
  const [accounts, setAccounts] = useState([]);
  const [files, setFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [logs, setLogs] = useState([]);
  const [providersInfo, setProvidersInfo] = useState({});
  const [loading, setLoading] = useState(false);
  const [networkError, setNetworkError] = useState(false);

  // Auth Form State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [authError, setAuthError] = useState('');
  const [showPolicyModal, setShowPolicyModal] = useState(null); // 'terms' | 'privacy' | null

  const isSignup = location.pathname === '/signup';

  const fetchAllData = async () => {
    if (!token) return;
    setLoading(true);
    setNetworkError(false);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const [statsRes, accountsRes, filesRes, foldersRes, logsRes, provRes] = await Promise.all([
        fetch(`${API_BASE}/api/stats`, { headers }),
        fetch(`${API_BASE}/api/accounts`, { headers }),
        fetch(`${API_BASE}/api/files`, { headers }),
        fetch(`${API_BASE}/api/folders`, { headers }),
        fetch(`${API_BASE}/api/logs`, { headers }),
        fetch(`${API_BASE}/api/oauth/providers`),
      ]);
      if (statsRes.status === 401 || accountsRes.status === 401 || filesRes.status === 401 || statsRes.status === 403) {
        handleLogout();
        return;
      }
      if (!statsRes.ok || !accountsRes.ok || !filesRes.ok) throw new Error('API error');
      setStats(await statsRes.json());
      setAccounts(await accountsRes.json());
      setFiles(await filesRes.json());
      if (foldersRes.ok) setFolders(await foldersRes.json());
      if (logsRes.ok) setLogs(await logsRes.json());
      if (provRes.ok) setProvidersInfo(await provRes.json());
    } catch (err) {
      console.error(err);
      if (err.message.includes('Failed to fetch') || err.message.includes('Load failed') || err instanceof TypeError) {
        setNetworkError(true);
      } else {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/oauth/providers`);
        if (!res.ok) throw new Error('Offline');
        setNetworkError(false);
        if (token) {
          fetchAllData();
        }
      } catch (err) {
        setNetworkError(true);
      }
    };
    checkBackend();
  }, [token]);

  const handleRetryConnection = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/oauth/providers`);
      if (res.ok) {
        handleLogout();
        setNetworkError(false);
        navigate('/signin');
      } else {
        throw new Error('Offline');
      }
    } catch (err) {
      console.error(err);
      setNetworkError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    if (isSignup && !acceptTerms) {
      setAuthError('You must agree to the Terms of Service & Privacy Policy');
      return;
    }
    setLoading(true);
    const endpoint = isSignup ? 'signup' : 'login';
    const bodyPayload = isSignup 
      ? { email, password, full_name: fullName }
      : { email, password };
    try {
      const res = await fetch(`${API_BASE}/api/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }
      localStorage.setItem('cirrus_token', data.access_token);
      localStorage.setItem('cirrus_user', JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      setEmail('');
      setPassword('');
      setFullName('');
      setAcceptTerms(false);
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('Load failed')) {
        setNetworkError(true);
      } else {
        setAuthError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('cirrus_token');
    localStorage.removeItem('cirrus_user');
    setToken('');
    setUser(null);
  };

  // Connect a cloud via the backend OAuth popup (stays connected via refresh token).
  const connectProvider = (provider) => {
    if (!token) return;
    const url = `${API_BASE}/api/oauth/${provider}/start?token=${encodeURIComponent(token)}&origin=${encodeURIComponent(window.location.origin)}`;
    const popup = window.open(url, 'cirrus_oauth', 'width=520,height=680');
    if (!popup) { alert('Popup blocked — allow popups for this site.'); return; }

    const onMessage = (e) => {
      if (!e.data || !e.data.cirrus_oauth) return;
      window.removeEventListener('message', onMessage);
      try { popup.close(); } catch { /* ignore */ }
      if (e.data.ok) fetchAllData();
      else alert(`Connect failed: ${e.data.error || 'unknown error'}`);
    };
    window.addEventListener('message', onMessage);
  };

  // Bulk upload: accepts one or many files, all routed into the given folder.
  const handleUploadFiles = async (fileList, compressionType, folderId, onProgress) => {
    if (!token) return;
    setLoading(true);
    const errors = [];
    try {
      const files = Array.from(fileList);
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        formData.append('compression', compressionType);
        if (folderId) formData.append('folder_id', folderId);
        const res = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          errors.push(`${files[i].name}: ${d.detail || res.status}`);
        }
        if (onProgress) onProgress(i + 1, files.length);
      }
      await fetchAllData();
      if (errors.length) throw new Error(errors.join('\n'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFolder = async (name, parentId) => {
    if (!token) return;
    const res = await fetch(`${API_BASE}/api/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ name, parent_id: parentId || null }),
    });
    if (!res.ok) { alert('Could not create folder: ' + ((await res.json()).detail || res.status)); return; }
    await fetchAllData();
  };

  const handleDeleteFolder = async (folderId) => {
    if (!token) return;
    const res = await fetch(`${API_BASE}/api/folders/${folderId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) { alert((await res.json()).detail || 'Could not delete folder'); return; }
    await fetchAllData();
  };

  const handleDeleteFile = async (fileId) => {
    if (!token) return;
    if (!window.confirm('Delete this file? This permanently deletes it from the cloud.')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/files/${fileId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Deletion failed');
      await fetchAllData();
    } catch (err) {
      alert('Failed to delete: ' + err.message);
      setLoading(false);
    }
  };

  const handleDownloadFile = async (fileId, filename) => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/download/${fileId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.setAttribute('download', filename);
      document.body.appendChild(link); link.click();
      link.parentNode.removeChild(link); window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to retrieve file: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!token) return;
    if (!window.confirm('Disconnect this account?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/accounts/${accountId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Disconnect failed');
      await fetchAllData();
    } catch (err) {
      alert('Failed to disconnect: ' + err.message);
      setLoading(false);
    }
  };

  const isSignupPath = location.pathname === '/signup';
  const isSigninPath = location.pathname === '/signin';
  const isAuthPath = isSignupPath || isSigninPath;

  // Render full screen offline page if the backend is down (styled similar to Vercel's 404 page)
  if (networkError) {
    return (
      <div style={vercelOfflinePageStyle}>
        <div style={vercelCardStyle}>
          <h1 style={vercelTitleStyle}>503: SERVICE_UNAVAILABLE</h1>
          <p style={vercelTextStyle}>
            Code: <code style={vercelCodeStyle}>BACKEND_OFFLINE</code>
          </p>
          <p style={vercelTextStyle}>
            ID: <code style={vercelCodeStyle}>cirrus::backend-connection-failed</code>
          </p>
        </div>
        <button 
          style={vercelButtonStyle} 
          onClick={handleRetryConnection} 
          disabled={loading}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#0070f3'; e.currentTarget.style.color = '#ffffff'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#ffffff'; e.currentTarget.style.color = '#0070f3'; }}
        >
          {loading ? 'Reconnecting...' : 'Retry connection to check for service availability.'}
        </button>
      </div>
    );
  }

  // If the user is not authenticated and trying to access an authenticated route, redirect to /signin
  if (!token && !isAuthPath) {
    return <Navigate to="/signin" replace />;
  }

  // If the user is authenticated and trying to access /signin or /signup, redirect to /dashboard
  if (token && isAuthPath) {
    return <Navigate to="/dashboard" replace />;
  }

  // If the user is authenticated and on the root path /, redirect to /dashboard
  if (token && location.pathname === '/') {
    return <Navigate to="/dashboard" replace />;
  }

  // Render Login page if not authenticated
  if (!token) {
    const isSignup = isSignupPath;
    return (
      <div style={authPageStyle}>
        <div className="glass-card" style={authCardStyle}>
          <div style={authHeaderStyle}>
            <img src="/logo.png" alt="CIRRUS" style={{ width: '80px', height: '80px', objectFit: 'contain', marginBottom: '10px' }} />
            <h1 style={{ fontSize: '2rem', margin: '5px 0' }}>CIRRUS</h1>
            <p className="subtitle" style={{ fontSize: '0.9rem' }}>Smart Cloud Quota Pooling & Compression</p>
          </div>

          <form onSubmit={handleAuthSubmit} style={authFormStyle}>
            {authError && <div style={authErrorStyle}>{authError}</div>}

            {isSignup && (
              <div className="form-group">
                <label>Full Name</label>
                <div style={inputContainerStyle}>
                  <UserIcon size={16} style={inputIconStyle} />
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Enter your full name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    style={{ paddingLeft: '38px', width: '100%' }}
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label>Email Address</label>
              <div style={inputContainerStyle}>
                <Mail size={16} style={inputIconStyle} />
                <input
                  type="email"
                  className="form-control"
                  placeholder="name@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  style={{ paddingLeft: '38px', width: '100%' }}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>
              <div style={inputContainerStyle}>
                <Lock size={16} style={inputIconStyle} />
                <input
                  type="password"
                  className="form-control"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ paddingLeft: '38px', width: '100%' }}
                />
              </div>
            </div>

            {isSignup && (
              <div style={termsCheckboxContainerStyle}>
                <input
                  type="checkbox"
                  id="accept-terms"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  required
                  style={{ cursor: 'pointer' }}
                />
                <label htmlFor="accept-terms" style={termsLabelStyle}>
                  I agree to the <a href="#terms" onClick={(e) => { e.preventDefault(); setShowPolicyModal('terms'); }} style={termsLinkStyle}>Terms of Service</a> & <a href="#privacy" onClick={(e) => { e.preventDefault(); setShowPolicyModal('privacy'); }} style={termsLinkStyle}>Privacy Policy</a>
                </label>
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', marginTop: '10px' }} disabled={loading}>
              {loading ? 'Processing...' : isSignup ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <div style={authToggleContainerStyle}>
            <button style={authToggleBtnStyle} onClick={() => { navigate(isSignup ? '/signin' : '/signup'); setAuthError(''); }}>
              {isSignup ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>

        {showPolicyModal && (
          <div className="modal-overlay" onClick={() => setShowPolicyModal(null)}>
            <div className="modal-container" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>{showPolicyModal === 'terms' ? 'Terms of Service' : 'Privacy Policy'}</h3>
                <button className="modal-close-btn" onClick={() => setShowPolicyModal(null)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>
              <div className="modal-body">
                {showPolicyModal === 'terms' ? (
                  <>
                    <p>Welcome to CIRRUS ("we," "us," "our"). By registering for, accessing, or using the CIRRUS Cloud Space Pooling service (the "Service"), you agree to be bound by these Terms of Service (the "Terms"). If you do not agree to these Terms, you may not access or use the Service.</p>
                    
                    <h4>1. Description of Service</h4>
                    <p>CIRRUS is a cloud storage quota pooling and file compression software utility. The Service does not provide dedicated cloud storage. Instead, the Service acts as a secure middleware client that pools, compresses, and splits files across the third-party cloud storage accounts (e.g., Google Drive, OneDrive, Dropbox) that you connect to your CIRRUS account.</p>
                    
                    <h4>2. Disclaimer of Warranties</h4>
                    <p>THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.</p>
                    <p>WE DO NOT WARRANT THAT:</p>
                    <ul>
                      <li>THE SERVICE WILL OPERATE UNINTERRUPTED, SECURE, OR ERROR-FREE.</li>
                      <li>FILES UPLOADED OR COMPRESSED WILL BE SECURE FROM DOWNTIME, CORRUPTION, OR LOSS.</li>
                      <li>THE THIRD-PARTY CLOUD PROVIDERS WILL MAINTAIN CONTINUOUS API ACCESS OR AGREEABLE SERVICE LEVEL AGREEMENTS.</li>
                    </ul>
                    <p>YOU AGREE THAT YOUR USE OF THE SERVICE IS AT YOUR SOLE RISK.</p>
                    
                    <h4>3. Limitation of Liability & Exclusion of Damages</h4>
                    <p>TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL CIRRUS, ITS DEVELOPERS, CREATORS, CONTRIBUTORS, AFFILIATES, OR LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR EXEMPLARY DAMAGES. THIS INCLUDES, BUT IS NOT LIMITED TO, DAMAGES FOR:</p>
                    <ul>
                      <li>LOSS OF PROFITS, GOODWILL, USE, DATA, OR OTHER INTANGIBLE LOSSES.</li>
                      <li>FILE LOSS, DATA CORRUPTION, TRANSMISSION FAILURES, DELETION, OR ALTERATION.</li>
                      <li>SERVICE OUTAGES, DATABASE DOWNTIME, OR SYSTEM FAILURES (INCLUDING BUT NOT LIMITED TO SUPABASE, AWS, OR CONNECTED CLOUDS).</li>
                      <li>UNAUTHORIZED ACCESS TO OR ALTERATION OF YOUR USER TRANSMISSIONS OR ENCRYPTED STORAGE KEYS.</li>
                    </ul>
                    <p>OUR TOTAL CUMULATIVE LIABILITY FOR ANY CLAIMS ARISING UNDER THESE TERMS SHALL NOT EXCEED THE AMOUNT PAID BY YOU, IF ANY, FOR USING THE SERVICE, OR USD $10.00, WHICHEVER IS LESS.</p>
                    
                    <h4>4. Third-Party Services & APIs</h4>
                    <p>The Service relies heavily on integrations with third-party cloud platforms. We exert no control over, and assume no responsibility for, the availability, policies, API restrictions, or actions of third-party platforms. Any breach of terms or loss of data caused by third-party actions is strictly between you and the third-party provider.</p>
                    
                    <h4>5. Indemnification</h4>
                    <p>You agree to defend, indemnify, and hold harmless CIRRUS, its developers, operators, affiliates, and employees from and against any and all claims, damages, obligations, losses, liabilities, costs, debt, and expenses (including but not limited to reasonable attorney's fees) arising from:</p>
                    <ul>
                      <li>Your access and use of the Service.</li>
                      <li>Your violation of any term of these Terms.</li>
                      <li>Your violation of any third-party right, including without limitation any copyright, property, or privacy right.</li>
                      <li>Any claim that your content or uploaded files caused damage to a third party.</li>
                    </ul>
                    
                    <h4>6. Dispute Resolution & Arbitration</h4>
                    <p>Any dispute, claim, or controversy arising out of or relating to these Terms, including the determination of the scope or applicability of this agreement to arbitrate, shall be resolved exclusively by final, binding arbitration in accordance with local laws. You explicitly waive the right to participate in class actions or class-wide arbitration.</p>
                    
                    <h4>7. Changes to Terms</h4>
                    <p>We reserve the right to amend these terms at any time. We will notify you of any material changes by posting the updated terms on this page. Your continued use of the Service following modifications constitutes acceptance of the new Terms.</p>
                  </>
                ) : (
                  <>
                    <p>At CIRRUS, we are committed to protecting your privacy. This Privacy Policy details how we handle user accounts, credentials, and file metadata.</p>
                    
                    <h4>1. Information We Collect</h4>
                    <ul>
                      <li><strong>Account Data:</strong> When you register, we collect your Full Name, Email Address, and a hashed version of your password.</li>
                      <li><strong>Storage Credentials:</strong> To pool your storage quota, we collect and store OAuth credentials (access tokens and refresh tokens) for the third-party cloud accounts you connect.</li>
                      <li><strong>Metadata:</strong> We collect and store file and folder metadata (such as names, file sizes, compression statuses, and folder locations) to render your dashboard and support directory navigation.</li>
                    </ul>
                    
                    <h4>2. Security & Encryption Safeguards</h4>
                    <p>We implement rigorous cryptographic security measures to safeguard your credentials:</p>
                    <ul>
                      <li><strong>OAuth Credentials:</strong> All third-party access tokens and refresh keys are encrypted at rest using AES-256-GCM encryption before storing in the database.</li>
                      <li><strong>Hashed Passwords:</strong> User account passwords are secure-hashed using salted hashing algorithms.</li>
                      <li>We do not store raw, unencrypted third-party storage credentials anywhere on our systems.</li>
                    </ul>
                    
                    <h4>3. No File Content Access</h4>
                    <p>The compression and transfer of your files occur dynamically on our server gateway. CIRRUS does not read, scan, view, parse, copy, or retain the actual content of the files passing through our system. Once compressed and transmitted to your connected clouds, no file content is cached or stored locally on CIRRUS servers.</p>
                    
                    <h4>4. Third-Party Data Sharing</h4>
                    <p>We have a strict zero-sharing policy:</p>
                    <ul>
                      <li>We do not sell, trade, rent, or distribute your personal details, email address, file metadata, or OAuth tokens to any third-party advertisers, companies, or entities.</li>
                      <li>Your information is used strictly to run the quota pooling service.</li>
                    </ul>
                    
                    <h4>5. Account Deletion & Data Portability</h4>
                    <p>You can disconnect any cloud account at any time. Disconnecting an account immediately and permanently purges the associated encrypted OAuth credentials from our database. You can also request complete account deletion, which will wipe all database entries, including your personal details, hashed password, connected accounts, and file metadata history.</p>
                    
                    <h4>6. Contact and Compliance</h4>
                    <p>For any questions regarding these privacy practices or to request data removal, please contact the system administrator.</p>
                  </>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-primary" onClick={() => setShowPolicyModal(null)}>I Understand</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Render main application shell for authenticated users
  return (
    <div className="app-container">
      <Sidebar onLogout={handleLogout} userEmail={user?.email} />
      
      {/* Mobile Bottom Navigation (Glassmorphic) */}
      {token && (
        <nav className="mobile-nav">
          <button className={`mobile-nav-item ${location.pathname === '/dashboard' ? 'active' : ''}`} onClick={() => navigate('/dashboard')}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </button>
          <button className={`mobile-nav-item ${location.pathname === '/connections' ? 'active' : ''}`} onClick={() => navigate('/connections')}>
            <HardDrive size={20} />
            <span>Connections</span>
          </button>
          <button className={`mobile-nav-item ${location.pathname === '/files' ? 'active' : ''}`} onClick={() => navigate('/files')}>
            <Files size={20} />
            <span>Files</span>
          </button>
          <button className="mobile-nav-item" onClick={handleLogout} style={{ color: 'var(--danger)' }}>
            <LogOut size={20} />
            <span>Sign Out</span>
          </button>
        </nav>
      )}

      <main className="main-content">
        <Routes>
          <Route path="/dashboard" element={<Dashboard stats={stats} logs={logs} loading={loading} onRefresh={fetchAllData} userFullName={user?.full_name} />} />
          <Route path="/connections" element={
            <AccountsManager
              accounts={accounts}
              providersInfo={providersInfo}
              onConnect={connectProvider}
              onDeleteAccount={handleDeleteAccount}
              loading={loading}
            />
          } />
          <Route path="/files" element={
            <FileManager
              files={files}
              folders={folders}
              onUpload={handleUploadFiles}
              onCreateFolder={handleCreateFolder}
              onDeleteFolder={handleDeleteFolder}
              onDelete={handleDeleteFile}
              onDownload={handleDownloadFile}
              loading={loading}
            />
          } />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

// Inline Styles
const authPageStyle = {
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '100vh',
  width: '100vw',
  background: '#fafafa',
  padding: '20px',
};

const authCardStyle = {
  width: '100%',
  maxWidth: '420px',
  padding: '40px 30px',
};

const authHeaderStyle = {
  textAlign: 'center',
  marginBottom: '30px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
};

const authFormStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
};

const inputContainerStyle = {
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
  width: '100%',
};

const inputIconStyle = {
  position: 'absolute',
  left: '12px',
  color: '#94a3b8',
  pointerEvents: 'none',
};

const authErrorStyle = {
  padding: '10px 14px',
  background: 'rgba(220, 38, 38, 0.05)',
  border: '1px solid rgba(220, 38, 38, 0.12)',
  borderRadius: '8px',
  color: 'var(--danger)',
  fontSize: '0.85rem',
  textAlign: 'center',
};

const termsCheckboxContainerStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: '8px',
  marginTop: '6px',
  marginBottom: '6px',
};

const termsLabelStyle = {
  fontSize: '0.75rem',
  color: '#475569',
  lineHeight: '1.4',
  cursor: 'pointer',
};

const termsLinkStyle = {
  color: '#be123c',
  fontWeight: '600',
  textDecoration: 'underline',
};

const authToggleContainerStyle = {
  textAlign: 'center',
  marginTop: '25px',
};

const authToggleBtnStyle = {
  background: 'transparent',
  border: 'none',
  color: 'var(--primary)',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: '600',
  transition: 'color 0.2s',
};

const errorBannerStyle = {
  background: 'rgba(220, 38, 38, 0.05)',
  border: '1px solid rgba(220, 38, 38, 0.12)',
  borderRadius: '12px',
  padding: '30px',
  color: 'var(--danger)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
  gap: '8px',
  maxWidth: '600px',
  margin: '80px auto',
};

const vercelOfflinePageStyle = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '100vh',
  width: '100vw',
  backgroundColor: '#ffffff',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  padding: '20px',
  boxSizing: 'border-box',
  animation: 'fadeIn 0.3s ease',
};

const vercelCardStyle = {
  border: '1px solid #eaeaea',
  borderRadius: '5px',
  width: '100%',
  maxWidth: '490px',
  padding: '24px',
  backgroundColor: '#ffffff',
  boxShadow: 'none',
  textAlign: 'left',
  boxSizing: 'border-box',
  marginBottom: '20px',
};

const vercelTitleStyle = {
  fontSize: '16px',
  fontWeight: '600',
  color: '#000000',
  margin: '0 0 20px 0',
  fontFamily: 'inherit',
};

const vercelTextStyle = {
  fontSize: '14px',
  color: '#444444',
  margin: '8px 0',
  lineHeight: '1.5',
};

const vercelCodeStyle = {
  fontFamily: 'monospace',
  backgroundColor: '#fafafa',
  padding: '2px 6px',
  borderRadius: '4px',
  border: '1px solid #eaeaea',
};

const vercelButtonStyle = {
  display: 'inline-block',
  width: '100%',
  maxWidth: '490px',
  textAlign: 'center',
  padding: '12px 24px',
  border: '1px solid #0070f3',
  borderRadius: '5px',
  color: '#0070f3',
  backgroundColor: '#ffffff',
  textDecoration: 'none',
  fontSize: '14px',
  cursor: 'pointer',
  transition: 'background-color 0.2s, color 0.2s',
  outline: 'none',
  fontFamily: 'inherit',
};
