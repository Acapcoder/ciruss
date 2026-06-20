import React, { useState } from 'react';
import { Files, HardDrive, Zap, RefreshCw, CheckCircle, AlertCircle, Info, Activity } from 'lucide-react';

function InfoTooltip({ text }) {
  const [visible, setVisible] = useState(false);
  return (
    <span 
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: '6px' }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <span style={{ cursor: 'help', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center' }}>
        <Info size={14} />
      </span>
      {visible && (
        <div style={tooltipBoxStyle}>
          {text}
        </div>
      )}
    </span>
  );
}

export default function Dashboard({ stats, logs, loading, onRefresh, userFullName }) {
  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const getPercentage = (used, limit) => {
    if (!limit || limit === 0) return 0;
    return Math.min(100, Math.round((used / limit) * 100));
  };

  // Compute aggregate quota totals
  const totalLimit = stats.account_usage ? stats.account_usage.reduce((acc, curr) => acc + curr.quota_limit, 0) : 0;
  const totalUsed = stats.account_usage ? stats.account_usage.reduce((acc, curr) => acc + curr.used_space, 0) : 0;
  const totalPercentage = getPercentage(totalUsed, totalLimit);

  // Compute compression saving text
  const savingPercent = stats.saving_ratio || 0;

  return (
    <div style={dashboardContainerStyle}>
      <header style={headerStyle}>
        <div>
          <h1>
            {(() => {
              const hour = new Date().getHours();
              if (hour >= 5 && hour < 12) return 'Good morning';
              if (hour >= 12 && hour < 17) return 'Good afternoon';
              return 'Good evening';
            })()}
            {userFullName ? `, ${userFullName}` : ''}
          </h1>
          <p className="subtitle">Smart, compressed, multi-cloud storage allocation</p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} disabled={loading} style={{ height: 'fit-content' }}>
          <RefreshCw size={18} className={loading ? 'spin-anim' : ''} style={loading ? spinStyle : {}} />
          <span>Refresh Stats</span>
        </button>
      </header>

      {/* Stats Cards Row */}
      <div style={statsGridStyle}>
        <div className="glass-card" style={statCardStyle}>
          <div style={statHeaderStyle}>
            <span style={statTitleStyle}>
              Total Registered Files
              <InfoTooltip text="Total number of virtual files uploaded and tracked across all pooled cloud storage accounts." />
            </span>
            <div style={{ ...iconBgStyle, background: 'rgba(190, 18, 60, 0.05)' }}>
              <Files size={20} color="#be123c" />
            </div>
          </div>
          <div style={statValueStyle}>{stats.total_files}</div>
          <div style={statFooterStyle}>Managed across cloud networks</div>
        </div>

        <div className="glass-card" style={statCardStyle}>
          <div style={statHeaderStyle}>
            <span style={statTitleStyle}>
              Combined Usage
              <InfoTooltip text="The aggregate amount of storage currently used across all connected Google Drive, Dropbox, etc. accounts." />
            </span>
            <div style={{ ...iconBgStyle, background: 'rgba(16, 185, 129, 0.08)' }}>
              <HardDrive size={20} color="#10b981" />
            </div>
          </div>
          <div style={statValueStyle}>{formatBytes(totalUsed)}</div>
          <div style={statFooterStyle}>Of {formatBytes(totalLimit)} aggregate limit</div>
        </div>

        <div className="glass-card" style={statCardStyle}>
          <div style={statHeaderStyle}>
            <span style={statTitleStyle}>
              Compression Space Saved
              <InfoTooltip text="The total storage space saved thanks to automatic client-side compression (Gzip or Zip) before routing." />
            </span>
            <div style={{ ...iconBgStyle, background: 'rgba(245, 158, 11, 0.08)' }}>
              <Zap size={20} color="#f59e0b" />
            </div>
          </div>
          <div style={statValueStyle}>
            {formatBytes(stats.space_saved_bytes)}
            <span style={percentageBadgeStyle}>-{savingPercent}%</span>
          </div>
          <div style={statFooterStyle}>
            Original: {formatBytes(stats.original_size_total)}
          </div>
        </div>
      </div>

      {/* Aggregate Storage Ring Visualization */}
      <div className="glass-card" style={aggregateSectionStyle}>
        <h2 style={{ display: 'flex', alignItems: 'center' }}>
          Aggregate Space Allocation
          <InfoTooltip text="A unified bar chart showing your pooled cloud storage capacity and how much of it is currently occupied." />
        </h2>
        <div style={aggregateContentStyle}>
          <div style={progressContainerStyle}>
            <div style={progressHeaderStyle}>
              <span>Storage Used</span>
              <span>{totalPercentage}% ({formatBytes(totalUsed)} / {formatBytes(totalLimit)})</span>
            </div>
            <div style={progressBarBgStyle}>
              <div style={{ ...progressBarFillStyle, width: `${totalPercentage}%` }} />
            </div>
          </div>
          <div style={routingLogStyle}>
            <span style={routingBadgeStyle}>Smart Routing Active</span>
            <p style={{ fontSize: '0.85rem', color: '#475569', marginTop: '6px' }}>
              Files are automatically routed to the cloud drive with the largest available free space after undergoing high-ratio gzip/zip compression.
            </p>
          </div>
        </div>
      </div>

      {/* Split allocations and audit logs section */}
      <div className="dashboard-grid">
        {/* Connected Cloud Accounts Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ marginBottom: '15px' }}>Attached Cloud Allocations</h2>
          {stats.account_usage && stats.account_usage.length === 0 ? (
            <div className="glass-card" style={emptyAccountsStyle}>
              <AlertCircle size={32} color="#64748b" style={{ marginBottom: '10px' }} />
              <p>No storage accounts registered. Link a drive to start uploading.</p>
            </div>
          ) : (
            <div style={accountsListStyle}>
              {stats.account_usage && stats.account_usage.map((acc) => {
                const currentPct = getPercentage(acc.used_space, acc.quota_limit);
                const freeSpace = Math.max(0, acc.quota_limit - acc.used_space);
                
                return (
                  <div className="glass-card" key={acc.id} style={accountCardStyle}>
                    <div style={accountHeaderStyle}>
                      <div>
                        <h3 style={accountNameStyle}>{acc.display_name}</h3>
                        <span className="badge badge-primary" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                          {acc.provider}
                        </span>
                      </div>
                      {acc.is_active ? (
                        <div style={statusBadgeStyle}>
                          <CheckCircle size={14} color="#10b981" />
                          <span style={{ color: '#10b981', fontSize: '0.75rem', fontWeight: 600 }}>CONNECTED</span>
                        </div>
                      ) : (
                        <div style={statusBadgeStyle}>
                          <AlertCircle size={14} color="#ef4444" />
                          <span style={{ color: '#ef4444', fontSize: '0.75rem', fontWeight: 600 }}>OFFLINE</span>
                        </div>
                      )}
                    </div>

                    <div style={accountBodyStyle}>
                      <div style={spaceRowStyle}>
                        <span>Used: {formatBytes(acc.used_space)}</span>
                        <span>Free: {formatBytes(freeSpace)}</span>
                      </div>
                      <div style={progressBarBgStyle}>
                        <div 
                          style={{ 
                            ...progressBarFillStyle, 
                            width: `${currentPct}%`,
                            background: acc.provider_type === 's3' ? '#FF9900' : 
                                        acc.provider_type === 'gcs' ? '#4285F4' :
                                        acc.provider_type === 'gdrive' ? '#34A853' :
                                        acc.provider_type === 'dropbox' ? '#0061FE' : '#be123c'
                          }} 
                        />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.75rem', color: '#64748b' }}>
                        <span>Limit: {formatBytes(acc.quota_limit)}</span>
                        <span>{currentPct}% used</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Audit Log Feed */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={20} color="#be123c" />
            <span>Recent Activity Logs</span>
            <InfoTooltip text="Secure audit trail fetched directly from your Supabase backend, documenting operations on folders, cloud drives, and files." />
          </h2>
          <div className="glass-card" style={logsContainerStyle}>
            {!logs || logs.length === 0 ? (
              <div style={emptyLogsStyle}>
                <p>No activity logs recorded yet. Upload a file to see logs populate.</p>
              </div>
            ) : (
              <div style={logsListStyle}>
                {logs.map((log) => (
                  <div key={log.id} style={logItemStyle}>
                    <div style={logHeaderStyle}>
                      <span className="badge badge-primary" style={logBadgeStyle}>
                        {log.action}
                      </span>
                      <span style={logTimeStyle}>
                        {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div style={logDetailsStyle}>{log.details}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Inline Styles
const dashboardContainerStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '30px',
};

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const statsGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
  gap: '20px',
};

const statCardStyle = {
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const statHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const statTitleStyle = {
  fontSize: '0.875rem',
  fontWeight: '600',
  color: '#475569',
  display: 'inline-flex',
  alignItems: 'center',
};

const iconBgStyle = {
  width: '38px',
  height: '38px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const statValueStyle = {
  fontSize: '1.8rem',
  fontWeight: '700',
  color: '#1e293b',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
};

const percentageBadgeStyle = {
  fontSize: '0.8rem',
  background: 'rgba(16, 185, 129, 0.08)',
  color: '#10b981',
  padding: '2px 8px',
  borderRadius: '12px',
  fontWeight: '600',
};

const statFooterStyle = {
  fontSize: '0.75rem',
  color: '#64748b',
};

const aggregateSectionStyle = {
  padding: '30px',
};

const aggregateContentStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '20px',
  marginTop: '15px',
};

const progressContainerStyle = {
  width: '100%',
};

const progressHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '0.9rem',
  color: '#475569',
  marginBottom: '8px',
  fontWeight: '600',
};

const progressBarBgStyle = {
  width: '100%',
  height: '8px',
  background: 'rgba(0, 0, 0, 0.05)',
  borderRadius: '8px',
  overflow: 'hidden',
};

const progressBarFillStyle = {
  height: '100%',
  background: '#be123c', // Solid flat red, no gradient
  borderRadius: '8px',
  transition: 'width 0.4s ease',
};

const routingLogStyle = {
  background: '#ffffff',
  border: '1px solid rgba(0, 0, 0, 0.08)',
  borderRadius: '8px',
  padding: '16px',
};

const routingBadgeStyle = {
  fontSize: '0.75rem',
  fontWeight: '700',
  color: '#be123c',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
};

const accountsListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '15px',
};

const emptyAccountsStyle = {
  padding: '40px',
  textAlign: 'center',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  color: '#64748b',
  height: '100%',
  justifyContent: 'center',
};

const accountCardStyle = {
  padding: '20px',
  display: 'flex',
  flexDirection: 'column',
  gap: '15px',
};

const accountHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
};

const accountNameStyle = {
  fontSize: '1.05rem',
  fontWeight: '600',
  color: '#1e293b',
  marginBottom: '4px',
};

const statusBadgeStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  background: 'rgba(0, 0, 0, 0.02)',
  padding: '4px 8px',
  borderRadius: '6px',
  border: '1px solid rgba(0, 0, 0, 0.04)',
};

const accountBodyStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const spaceRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '0.8rem',
  color: '#475569',
};

const spinStyle = {
  animation: 'spin-slow 1s linear infinite',
};

const tooltipBoxStyle = {
  position: 'absolute',
  top: '24px',
  left: '50%',
  transform: 'translateX(-50%)',
  background: '#ffffff',
  border: '1px solid rgba(190, 18, 60, 0.2)',
  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.08)',
  padding: '10px 14px',
  borderRadius: '8px',
  width: '240px',
  color: '#475569',
  fontSize: '0.75rem',
  lineHeight: '1.4',
  zIndex: 100,
  pointerEvents: 'none',
  textAlign: 'left',
};

// Logs Component Styles
const logsContainerStyle = {
  flex: 1,
  padding: '20px',
  maxHeight: '400px',
  overflowY: 'auto',
  background: '#ffffff',
};

const emptyLogsStyle = {
  padding: '40px',
  textAlign: 'center',
  color: '#64748b',
  display: 'flex',
  height: '100%',
  alignItems: 'center',
  justifyContent: 'center',
};

const logsListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const logItemStyle = {
  paddingBottom: '10px',
  borderBottom: '1px solid rgba(0, 0, 0, 0.04)',
};

const logHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '4px',
};

const logBadgeStyle = {
  fontSize: '0.6rem',
  padding: '2px 6px',
};

const logTimeStyle = {
  fontSize: '0.7rem',
  color: '#94a3b8',
};

const logDetailsStyle = {
  fontSize: '0.8rem',
  color: '#475569',
};
