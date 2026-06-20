import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, HardDrive, Files, CloudLightning, LogOut } from 'lucide-react';

export default function Sidebar({ onLogout, userEmail }) {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { id: 'accounts', name: 'Cloud Connections', icon: HardDrive, path: '/connections' },
    { id: 'files', name: 'File Manager', icon: Files, path: '/files' },
  ];

  return (
    <div className="sidebar" style={sidebarStyle}>
      <div className="logo-section" style={logoSectionStyle}>
        <img src="/logo.png" alt="" style={{ width: '38px', height: '38px', objectFit: 'contain' }} />
        <span style={logoTextStyle}>CIRRUS</span>
      </div>

      <nav style={navStyle}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <button
              key={item.id}
              onClick={() => navigate(item.path)}
              style={isActive ? activeItemStyle : itemStyle}
            >
              <Icon size={20} color={isActive ? '#be123c' : '#64748b'} />
              <span>{item.name}</span>
              {isActive && <div style={activeIndicatorStyle} />}
            </button>
          );
        })}
      </nav>

      <div style={footerStyle}>
        {userEmail && (
          <div style={emailLabelStyle} title={userEmail}>
            {userEmail}
          </div>
        )}
        <button className="btn btn-danger" onClick={onLogout} style={logoutBtnStyle}>
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}

// Styling details inside component for self-containment
const sidebarStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  bottom: 0,
  width: '260px',
  background: '#ffffff',
  borderRight: '1px solid rgba(0, 0, 0, 0.06)',
  padding: '30px 20px',
  display: 'flex',
  flexDirection: 'column',
  zIndex: 100,
  boxShadow: '1px 0 5px rgba(0, 0, 0, 0.01)',
};

const logoSectionStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  marginBottom: '40px',
  paddingLeft: '10px',
};

const logoTextStyle = {
  fontSize: '1.4rem',
  fontWeight: '800',
  letterSpacing: '0.05em',
  color: '#be123c', // Solid color, no gradient
};

const navStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  flex: 1,
};

const itemStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '14px',
  padding: '14px 16px',
  background: 'transparent',
  border: 'none',
  borderRadius: '8px',
  color: '#475569',
  fontSize: '0.95rem',
  fontWeight: '600',
  cursor: 'pointer',
  textAlign: 'left',
  width: '100%',
  transition: 'all 0.2s ease',
  position: 'relative',
};

const activeItemStyle = {
  ...itemStyle,
  color: '#be123c',
  background: 'rgba(190, 18, 60, 0.04)',
};

const activeIndicatorStyle = {
  position: 'absolute',
  right: '0px',
  top: '4px',
  bottom: '4px',
  width: '4px',
  borderRadius: '4px 0 0 4px',
  background: '#be123c',
};

const footerStyle = {
  paddingTop: '16px',
  borderTop: '1px solid rgba(0, 0, 0, 0.05)',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  alignItems: 'center',
};

const emailLabelStyle = {
  fontSize: '0.8rem',
  color: '#64748b',
  fontWeight: '600',
  maxWidth: '100%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const logoutBtnStyle = {
  width: '100%',
  padding: '8px 12px',
  fontSize: '0.85rem',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  gap: '6px',
};
