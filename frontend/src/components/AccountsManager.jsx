import React, { useState } from 'react';
import { HardDrive, Plus, Trash2, Info } from 'lucide-react';

const META = {
  gdrive: { label: 'Google Drive', color: '#34a853' },
  dropbox: { label: 'Dropbox', color: '#0061fe' },
};

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

export default function AccountsManager({ accounts, providersInfo, onConnect, onDeleteAccount, loading }) {
  const formatBytes = (bytes) => {
    if (bytes == null) return '—';
    if (bytes === 0) return '0 Bytes';
    const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const providerKeys = Object.keys(META);

  return (
    <div style={containerStyle}>
      <header>
        <h1 style={{ display: 'flex', alignItems: 'center' }}>
          Cloud Connections
          <InfoTooltip text="Link your personal cloud drives to pool their storage spaces. You can link multiple accounts of the same type!" />
        </h1>
        <p className="subtitle">Connect your accounts — pool them all into one storage box. No passwords stored.</p>
      </header>

      {/* Add accounts */}
      <div>
        <h2 style={{ ...subHeadStyle, display: 'flex', alignItems: 'center' }}>
          Add an account
          <InfoTooltip text="Clicking a button opens a secure, direct browser login tab with the provider. CIRRUS only stores an OAuth refresh token securely in your database." />
        </h2>
        <div style={connectGridStyle}>
          {providerKeys.map((k) => {
            const info = providersInfo[k] || {};
            const enabled = info.configured && info.supported;
            const count = accounts.filter((a) => a.provider === k).length;
            const m = META[k];
            const hint = !info.supported ? 'Coming soon' : !info.configured ? 'Add client secret on server' : `Sign in with ${m.label}`;
            return (
              <button
                key={k}
                className="btn"
                onClick={() => onConnect(k)}
                disabled={loading || !enabled}
                title={hint}
                style={{ ...connectBtnStyle, borderColor: 'rgba(0, 0, 0, 0.08)', opacity: enabled ? 1 : 0.5 }}
              >
                <span style={{ ...brandTagStyle, background: `${m.color}15`, color: m.color }}>{m.label[0]}</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{count ? `Add another ${m.label}` : `Connect ${m.label}`}</span>
                <Plus size={16} color="var(--text-secondary)" style={{ marginLeft: 'auto' }} />
              </button>
            );
          })}
        </div>
        <p style={hintStyle}>You can connect several Google accounts — CIRRUS pools all their free space into one box.</p>
      </div>

      {/* Connected */}
      <div>
        <h2 style={subHeadStyle}>Connected ({accounts.length})</h2>
        {accounts.length === 0 ? (
          <div className="glass-card" style={emptyStyle}>
            <HardDrive size={32} color="#64748b" style={{ marginBottom: '10px' }} />
            <p>No accounts connected yet. Use the connection panel above.</p>
          </div>
        ) : (
          <div style={listStyle}>
            {accounts.map((a) => {
              const m = META[a.provider_type] || META[a.provider] || { label: a.provider, color: '#be123c' };
              const free = Math.max(0, (a.quota_limit || 0) - (a.used_space || 0));
              return (
                <div className="glass-card" key={a.id} style={itemStyle}>
                  <div style={metaStyle}>
                    <div style={{ ...iconBgStyle, background: `rgba(190, 18, 60, 0.04)`, border: `1px solid rgba(190, 18, 60, 0.08)` }}>
                      <HardDrive size={20} color="#be123c" />
                    </div>
                    <div>
                      <h3 style={nameStyle}>{a.display_name}</h3>
                      <div style={detailStyle}>
                        <span className="badge badge-primary" style={badgeStyle}>{m.label}</span>
                        <span>•</span>
                        <span>{formatBytes(a.used_space)} used / {formatBytes(a.quota_limit)}</span>
                        <span>•</span>
                        <span style={{ color: '#10b981', fontWeight: 600 }}>{formatBytes(free)} free</span>
                      </div>
                    </div>
                  </div>
                  <button className="btn btn-danger" onClick={() => onDeleteAccount(a.id)} style={{ padding: '8px 14px' }}>
                    <Trash2 size={16} /><span>Disconnect</span>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const containerStyle = { display: 'flex', flexDirection: 'column', gap: '28px' };
const subHeadStyle = { fontSize: '1.1rem', marginBottom: '14px', color: 'var(--text-primary)' };
const connectGridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' };
const connectBtnStyle = { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', background: '#ffffff', border: '1px solid rgba(0, 0, 0, 0.08)', borderRadius: '8px', cursor: 'pointer', boxShadow: '0 1px 3px rgba(0,0,0,0.01)' };
const brandTagStyle = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold' };
const hintStyle = { fontSize: '0.8rem', color: '#64748b', marginTop: '10px' };
const listStyle = { display: 'flex', flexDirection: 'column', gap: '15px' };
const itemStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px' };
const metaStyle = { display: 'flex', alignItems: 'center', gap: '16px' };
const iconBgStyle = { padding: '12px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' };
const nameStyle = { fontSize: '1.05rem', fontWeight: '600', color: '#1e293b', marginBottom: '4px' };
const detailStyle = { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#475569', flexWrap: 'wrap' };
const badgeStyle = { fontSize: '0.65rem', padding: '2px 8px' };
const emptyStyle = { padding: '40px', textAlign: 'center', color: '#64748b', display: 'flex', flexDirection: 'column', alignItems: 'center' };

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
