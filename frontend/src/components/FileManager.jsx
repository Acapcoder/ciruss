import { useState, useRef } from 'react';
import {
  Upload, Download, Trash2, Search, FileText, ExternalLink,
  Folder, FolderPlus, ChevronRight, Home, Info,
} from 'lucide-react';

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

export default function FileManager({
  files, folders, onUpload, onCreateFolder, onDeleteFolder, onDelete, onDownload, loading,
}) {
  const [currentFolderId, setCurrentFolderId] = useState(null); // null = root
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [compression, setCompression] = useState('gzip');
  const [searchQuery, setSearchQuery] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(null); // {done,total}
  const fileInputRef = useRef(null);

  const fmt = (b, d = 2) => {
    if (b === 0 || b == null) return '0 B';
    const k = 1024, s = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return parseFloat((b / Math.pow(k, i)).toFixed(d)) + ' ' + s[i];
  };
  const savings = (o, c) => (o > 0 && o > c ? Math.round((1 - c / o) * 100) + '%' : '0%');

  // ---- breadcrumb path from root to current ----
  const pathTo = (id) => {
    const chain = [];
    let cur = folders.find((f) => f.id === id);
    while (cur) { chain.unshift(cur); cur = folders.find((f) => f.id === cur.parent_id); }
    return chain;
  };
  const crumbs = pathTo(currentFolderId);

  const searching = searchQuery.trim().length > 0;
  const q = searchQuery.toLowerCase();

  const subfolders = searching
    ? []
    : folders.filter((f) => (f.parent_id || null) === currentFolderId);

  const visibleFiles = (searching
    ? files.filter((f) => f.original_name.toLowerCase().includes(q) || (f.cloud_provider || '').toLowerCase().includes(q))
    : files.filter((f) => (f.folder_id || null) === currentFolderId)
  );

  const folderCount = (id) =>
    folders.filter((f) => f.parent_id === id).length + files.filter((f) => f.folder_id === id).length;

  // ---- upload handlers ----
  const pickFiles = (list) => setSelectedFiles(Array.from(list));
  const handleDrop = (e) => {
    e.preventDefault(); setDragActive(false);
    if (e.dataTransfer.files?.length) pickFiles(e.dataTransfer.files);
  };
  const submitUpload = async () => {
    if (!selectedFiles.length) return;
    setUploading(true); setProgress({ done: 0, total: selectedFiles.length });
    try {
      await onUpload(selectedFiles, compression, currentFolderId, (done, total) => setProgress({ done, total }));
      setSelectedFiles([]);
    } catch (err) {
      alert('Some uploads failed:\n' + err.message);
    } finally {
      setUploading(false); setProgress(null);
    }
  };

  const newFolder = () => {
    const name = window.prompt('New folder name:');
    if (name && name.trim()) onCreateFolder(name.trim(), currentFolderId);
  };

  return (
    <div style={wrap}>
      <header style={headRow}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center' }}>
            File Manager
            <InfoTooltip text="Pooled cloud resources display as a single unified folder tree. Files reside in the database, while physical data auto-allocates to the cloud with the most space." />
          </h1>
          <p className="subtitle">Organize your pooled storage into folders — files auto-route to the emptiest cloud.</p>
        </div>
      </header>

      {/* Toolbar: breadcrumb + actions */}
      <div style={toolbar}>
        <div style={breadcrumb}>
          <button style={crumbBtn} onClick={() => setCurrentFolderId(null)} title="Home">
            <Home size={15} color="var(--primary)" /> <span>Home</span>
          </button>
          {crumbs.map((c) => (
            <span key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ChevronRight size={14} color="var(--text-muted)" />
              <button style={crumbBtn} onClick={() => setCurrentFolderId(c.id)}>{c.name}</button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={searchWrap}>
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)' }} />
            <input style={searchInput} placeholder="Search all files…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <button className="btn btn-secondary" onClick={newFolder} disabled={searching} title="Create a folder here">
            <FolderPlus size={16} color="var(--primary)" /> <span style={{ color: 'var(--text-primary)' }}>New Folder</span>
          </button>
        </div>
      </div>

      {/* Upload card */}
      <div className="glass-card" style={{ padding: 18 }}>
        <div
          style={{ ...dropzone, borderColor: dragActive ? 'var(--primary)' : 'rgba(0, 0, 0, 0.08)', background: dragActive ? 'rgba(190,18,60,0.03)' : '#ffffff' }}
          onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
        >
          <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={(e) => pickFiles(e.target.files)} />
          <Upload size={28} color="var(--primary)" />
          {selectedFiles.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)' }}><strong>Drag files here</strong> or click to browse — you can select many at once</div>
          ) : (
            <div style={{ color: 'var(--text-primary)' }}><strong>{selectedFiles.length}</strong> file(s) ready{currentFolderId ? ` → ${crumbs[crumbs.length - 1]?.name}` : ' → Home'}</div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 12, alignItems: 'center' }}>
          <select className="form-control" value={compression} onChange={(e) => setCompression(e.target.value)} style={{ flex: 1, maxWidth: 260 }}>
            <option value="gzip">Gzip (smallest)</option>
            <option value="zip">Zip</option>
            <option value="none">No compression</option>
          </select>
          <button className="btn btn-primary" onClick={submitUpload} disabled={!selectedFiles.length || uploading || loading}>
            <Upload size={16} />
            <span>{uploading && progress ? `Uploading ${progress.done}/${progress.total}…` : `Upload ${selectedFiles.length || ''}`}</span>
          </button>
        </div>
      </div>

      {/* Folder + file grid */}
      <div style={grid}>
        {subfolders.map((f) => (
          <div key={f.id} className="glass-card" style={card} onClick={() => setCurrentFolderId(f.id)}>
            <div style={cardHead}>
              <Folder size={22} color="var(--primary)" />
              <button className="icon-btn" title="Delete folder" style={iconBtnStyle} onClick={(e) => { e.stopPropagation(); onDeleteFolder(f.id); }}>
                <Trash2 size={15} color="var(--text-muted)" />
              </button>
            </div>
            <div style={cardName} title={f.name}>{f.name}</div>
            <div style={cardMeta}>{folderCount(f.id)} item(s)</div>
          </div>
        ))}

        {visibleFiles.map((file) => (
          <div key={file.id} className="glass-card" style={card}>
            <div style={cardHead}>
              <FileText size={22} color="var(--text-muted)" />
              <div style={{ display: 'flex', gap: 4 }}>
                {file.web_link && (
                  <a className="icon-btn" style={iconBtnStyle} href={file.web_link} target="_blank" rel="noopener noreferrer" title="Open on cloud"><ExternalLink size={15} color="var(--text-muted)" /></a>
                )}
                <button className="icon-btn" style={iconBtnStyle} title="Download" onClick={() => onDownload(file.id, file.original_name)}><Download size={15} color="var(--text-muted)" /></button>
                <button className="icon-btn danger" style={iconBtnStyle} title="Delete (also removes from cloud)" onClick={() => onDelete(file.id)}><Trash2 size={15} color="var(--danger)" /></button>
              </div>
            </div>
            <div style={cardName} title={file.original_name}>{file.original_name}</div>
            <div style={cardMeta}>
              <span style={badge}>{file.cloud_provider}</span>
              <div style={{ marginTop: 6 }}>{fmt(file.compressed_size)} · <span style={{ color: 'var(--success)' }}>{savings(file.original_size, file.compressed_size)} saved</span></div>
            </div>
          </div>
        ))}

        {subfolders.length === 0 && visibleFiles.length === 0 && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--text-muted)', padding: 50 }}>
            {searching ? 'No files match your search.' : 'This folder is empty. Create a folder or upload files.'}
          </div>
        )}
      </div>
    </div>
  );
}

const wrap = { display: 'flex', flexDirection: 'column', gap: 22 };
const headRow = { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' };
const toolbar = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 };
const breadcrumb = { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' };
const crumbBtn = { display: 'flex', alignItems: 'center', gap: 5, background: 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600, padding: '4px 6px', borderRadius: 6 };
const searchWrap = { position: 'relative' };
const searchInput = { background: '#ffffff', border: '1px solid rgba(0, 0, 0, 0.1)', borderRadius: 8, padding: '8px 12px 8px 34px', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: '0.85rem', width: 200, outline: 'none' };
const dropzone = { border: '2px dashed', borderRadius: 12, padding: '22px', textAlign: 'center', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, color: 'var(--text-muted)', transition: 'all .2s' };
const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 };
const card = { padding: 16, display: 'flex', flexDirection: 'column', gap: 8, cursor: 'pointer', minHeight: 110, background: '#ffffff' };
const cardHead = { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' };
const cardName = { fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };
const cardMeta = { fontSize: '0.75rem', color: 'var(--text-muted)' };
const badge = { fontSize: '0.65rem', padding: '2px 8px', borderRadius: 10, background: 'rgba(190,18,60,0.08)', color: 'var(--primary)', border: '1px solid rgba(190,18,60,0.15)' };
const iconBtnStyle = { background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' };

const tooltipBoxStyle = {
  position: 'absolute',
  top: '24px',
  left: '50%',
  transform: 'translateX(-50%)',
  background: '#ffffff',
  border: '1px solid rgba(220, 38, 38, 0.15)',
  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
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
