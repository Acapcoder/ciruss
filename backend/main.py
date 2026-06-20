import os
import json
import uuid
import gzip
import zipfile
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
import schemas
from crypto_utils import encrypt_data, hash_password, verify_password, create_access_token, decode_access_token
from storage_clients import get_storage_client
from oauth_routes import router as oauth_router

# Ensure DB tables are initialized
Base.metadata.create_all(bind=engine)


def ensure_schema():
    """Lightweight migration: add columns that create_all won't add to
    pre-existing tables (e.g. folder_id/user_id when upgrading)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    try:
        # Check users columns
        users_cols = [c["name"] for c in insp.get_columns("users")]
        if "full_name" not in users_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR"))

        # Check folders columns
        folders_cols = [c["name"] for c in insp.get_columns("folders")]
        if "user_id" not in folders_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE folders ADD COLUMN user_id VARCHAR"))
                
        # Check storage_accounts columns
        sa_cols = [c["name"] for c in insp.get_columns("storage_accounts")]
        if "user_id" not in sa_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE storage_accounts ADD COLUMN user_id VARCHAR"))

        # Check stored_files columns
        sf_cols = [c["name"] for c in insp.get_columns("stored_files")]
        if "folder_id" not in sf_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE stored_files ADD COLUMN folder_id VARCHAR"))
        if "user_id" not in sf_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE stored_files ADD COLUMN user_id VARCHAR"))
    except Exception as e:
        print(f"Schema check/migration skipped: {e}")


ensure_schema()

# Create folders for temporary processing
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_processing")
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI(title="CIRRUS Cloud Storage Backend")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth "Connect with …" flow (authorization-code, stores refresh tokens).
app.include_router(oauth_router)


# Audit Logs Helper
def log_action(db: Session, user_id: str, action: str, details: str = None):
    try:
        new_log = models.AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to record audit log: {e}")


# Auth dependency
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    payload = decode_access_token(authorization)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# Compression Helpers
def compress_file_gzip(input_path: str, output_path: str):
    with open(input_path, 'rb') as f_in:
        with gzip.open(output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def compress_file_zip(input_path: str, output_path: str, filename: str):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(input_path, arcname=filename)


def decompress_file_gzip(input_path: str, output_path: str):
    with gzip.open(input_path, 'rb') as f_in:
        with open(output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def decompress_file_zip(input_path: str, output_path: str, original_filename: str):
    with zipfile.ZipFile(input_path, 'r') as zipf:
        zipf.extract(original_filename, path=TEMP_DIR)
        extracted_path = os.path.join(TEMP_DIR, original_filename)
        if extracted_path != output_path:
            shutil.move(extracted_path, output_path)


# Authentication API Endpoints
@app.post("/api/auth/signup", response_model=schemas.TokenResponse)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    user_in.email = user_in.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed = hash_password(user_in.password)
    new_user = models.User(email=user_in.email, hashed_password=hashed, full_name=user_in.full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_action(db, new_user.id, "SIGNUP", f"User registered: {new_user.email}")
    
    token = create_access_token(new_user.id, new_user.email)
    return {"access_token": token, "token_type": "bearer", "user": new_user}


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user_in.email = user_in.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    log_action(db, user.id, "LOGIN", f"User logged in: {user.email}")
    
    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer", "user": user}


# User Audit Logs Endpoint
@app.get("/api/logs", response_model=List[schemas.AuditLogResponse])
def get_logs(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.AuditLog).filter(models.AuditLog.user_id == current_user.id).order_by(models.AuditLog.timestamp.desc()).limit(15).all()


# Core Storage Accounts API
@app.get("/api/accounts", response_model=List[schemas.AccountResponse])
def list_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    accounts = db.query(models.StorageAccount).filter(models.StorageAccount.user_id == current_user.id).all()
    # Update current used space for all active accounts on query
    for account in accounts:
        if account.is_active:
            try:
                client = get_storage_client(account)
                account.used_space = client.get_used_space()
            except Exception as e:
                print(f"Error checking space for account {account.display_name}: {e}")
    db.commit()
    return accounts


@app.post("/api/accounts", response_model=schemas.AccountResponse)
def create_account(account_in: schemas.AccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    valid_providers = ["gdrive_browser", "onedrive_browser", "dropbox_browser"]
    if account_in.provider not in valid_providers:
        raise HTTPException(status_code=400, detail="Invalid storage provider")
        
    encrypted_creds = None
    if not account_in.is_mock and account_in.credentials:
        creds_str = json.dumps(account_in.credentials)
        encrypted_creds = encrypt_data(creds_str)

    is_mock = account_in.is_mock or (account_in.provider == "mock")

    new_account = models.StorageAccount(
        user_id=current_user.id,
        provider=account_in.provider,
        display_name=account_in.display_name,
        credentials_json=encrypted_creds,
        quota_limit=account_in.quota_limit,
        is_mock=is_mock,
        is_active=True
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    from browser_drive import BROWSER_PROVIDERS
    if new_account.provider not in BROWSER_PROVIDERS:
        try:
            client = get_storage_client(new_account)
            new_account.used_space = client.get_used_space()
            db.commit()
            db.refresh(new_account)
        except Exception as e:
            print(f"Error calculating initial space: {e}")

    log_action(db, current_user.id, "CONNECT_ACCOUNT", f"Created mock/browser connection: {new_account.display_name}")
    return new_account


@app.post("/api/accounts/{account_id}/login", response_model=schemas.AccountResponse)
def browser_login(account_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account = db.query(models.StorageAccount).filter(
        models.StorageAccount.id == account_id,
        models.StorageAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Storage account not found")

    from browser_drive import BROWSER_PROVIDERS, get_browser_client
    if account.provider not in BROWSER_PROVIDERS:
        raise HTTPException(status_code=400, detail="This provider does not use browser sign-in")

    try:
        client = get_browser_client(account.provider, account.id)
        client.connect(timeout=300)
        try:
            account.used_space = client.get_used_space()
        except Exception as e:
            print(f"Logged in but could not read space for {account.display_name}: {e}")
        db.commit()
        db.refresh(account)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sign-in failed: {str(e)}")

    log_action(db, current_user.id, "CONNECT_ACCOUNT", f"Authenticated browser connection: {account.display_name}")
    return account


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    account = db.query(models.StorageAccount).filter(
        models.StorageAccount.id == account_id,
        models.StorageAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Storage account not found")
    
    if account.is_mock:
        mock_dir = os.path.join(os.path.dirname(__file__), "storage_clients", "mock_storage", account.id)
        if os.path.exists(mock_dir):
            shutil.rmtree(mock_dir)
            
    log_action(db, current_user.id, "DISCONNECT_ACCOUNT", f"Disconnected cloud account: {account.display_name}")
    db.delete(account)
    db.commit()
    return {"status": "success", "message": f"Account {account_id} disconnected"}


# Core Stored Files API
@app.get("/api/files", response_model=List[schemas.FileResponse])
def list_files(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.StoredFile).filter(models.StoredFile.user_id == current_user.id).order_by(models.StoredFile.upload_time.desc()).all()


# Core Virtual Folders API
@app.get("/api/folders", response_model=List[schemas.FolderResponse])
def list_folders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Folder).filter(models.Folder.user_id == current_user.id).all()


@app.post("/api/folders", response_model=schemas.FolderResponse)
def create_folder(folder_in: schemas.FolderCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    name = (folder_in.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required")
        
    folder = models.Folder(name=name, parent_id=folder_in.parent_id or None, user_id=current_user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
    log_action(db, current_user.id, "CREATE_FOLDER", f"Created virtual folder: {folder.name}")
    return folder


@app.delete("/api/folders/{folder_id}")
def delete_folder(folder_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    folder = db.query(models.Folder).filter(
        models.Folder.id == folder_id,
        models.Folder.user_id == current_user.id
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    has_sub = db.query(models.Folder).filter(models.Folder.parent_id == folder_id).first()
    has_files = db.query(models.StoredFile).filter(models.StoredFile.folder_id == folder_id).first()
    if has_sub or has_files:
        raise HTTPException(status_code=400, detail="Folder is not empty — delete its contents first")
        
    log_action(db, current_user.id, "DELETE_FOLDER", f"Deleted virtual folder: {folder.name}")
    db.delete(folder)
    db.commit()
    return {"status": "success"}


# Core Upload / Compression Endpoint
@app.post("/api/upload", response_model=schemas.FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    compression: str = Form("gzip"),
    folder_id: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    active_accounts = db.query(models.StorageAccount).filter(
        models.StorageAccount.is_active == True,
        models.StorageAccount.user_id == current_user.id
    ).all()
    if not active_accounts:
        raise HTTPException(status_code=400, detail="No active storage accounts found. Please connect an account first.")

    candidate_accounts = []
    for account in active_accounts:
        try:
            client = get_storage_client(account)
            account.used_space = client.get_used_space()
            db.add(account)
            
            free_space = account.quota_limit - account.used_space
            if free_space > 0:
                candidate_accounts.append((account, free_space))
        except Exception as e:
            print(f"Skipping storage account {account.display_name} due to error: {e}")
    
    db.commit()

    if not candidate_accounts:
        raise HTTPException(status_code=507, detail="All storage accounts are full or offline.")

    candidate_accounts.sort(key=lambda x: x[1], reverse=True)
    selected_account, selected_free_space = candidate_accounts[0]

    temp_id = str(uuid.uuid4())
    input_file_path = os.path.join(TEMP_DIR, f"{temp_id}_input_{file.filename}")
    
    with open(input_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    original_size = os.path.getsize(input_file_path)

    compression = compression.lower()
    if compression == "gzip":
        compressed_filename = f"{file.filename}.gz"
        output_file_path = os.path.join(TEMP_DIR, f"{temp_id}_{compressed_filename}")
        compress_file_gzip(input_file_path, output_file_path)
    elif compression == "zip":
        compressed_filename = f"{file.filename}.zip"
        output_file_path = os.path.join(TEMP_DIR, f"{temp_id}_{compressed_filename}")
        compress_file_zip(input_file_path, output_file_path, file.filename)
    else:
        compression = "none"
        compressed_filename = file.filename
        output_file_path = os.path.join(TEMP_DIR, f"{temp_id}_{compressed_filename}")
        shutil.copy2(input_file_path, output_file_path)

    compressed_size = os.path.getsize(output_file_path)

    if compressed_size > selected_free_space:
        os.remove(input_file_path)
        os.remove(output_file_path)
        raise HTTPException(status_code=507, detail=f"File exceeds free space on {selected_account.display_name}")

    try:
        client = get_storage_client(selected_account)
        stored_cloud_name = f"{uuid.uuid4()}_{compressed_filename}"
        remote_stored_id = client.upload_file(output_file_path, stored_cloud_name)

        web_link = None
        if hasattr(client, "get_web_link"):
            try:
                web_link = client.get_web_link(remote_stored_id)
            except Exception:
                web_link = None

        provider_displays = {
            "s3": "AWS S3",
            "gcs": "GCP Cloud Storage",
            "gdrive": "Google Drive",
            "dropbox": "Dropbox",
            "mock": "Mock Drive"
        }
        display_cloud = provider_displays.get(selected_account.provider, "Cloud Storage")
        if selected_account.is_mock:
            display_cloud = f"Mock {display_cloud}"

        stored_file = models.StoredFile(
            user_id=current_user.id,
            original_name=file.filename,
            stored_name=remote_stored_id,
            compression_type=compression,
            original_size=original_size,
            compressed_size=compressed_size,
            cloud_provider=display_cloud,
            web_link=web_link,
            folder_id=(folder_id or None),
            account_id=selected_account.id
        )
        
        db.add(stored_file)
        selected_account.used_space += compressed_size
        db.add(selected_account)
        db.commit()
        db.refresh(stored_file)
        
        log_action(db, current_user.id, "UPLOAD", f"Uploaded file: {file.filename} to {display_cloud} ({compression})")
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {str(e)}")
    finally:
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)

    return stored_file


# Download & Decompression Endpoint
@app.get("/api/download/{file_id}")
def download_file(file_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    stored_file = db.query(models.StoredFile).filter(
        models.StoredFile.id == file_id,
        models.StoredFile.user_id == current_user.id
    ).first()
    if not stored_file:
        raise HTTPException(status_code=404, detail="File metadata not found in registry")

    account = db.query(models.StorageAccount).filter(
        models.StorageAccount.id == stored_file.account_id,
        models.StorageAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Associated storage account not connected")

    temp_download_id = str(uuid.uuid4())
    compressed_temp_path = os.path.join(TEMP_DIR, f"{temp_download_id}_comp_{stored_file.original_name}")
    decompressed_temp_path = os.path.join(TEMP_DIR, f"{temp_download_id}_dec_{stored_file.original_name}")

    try:
        client = get_storage_client(account)
        client.download_file(stored_file.stored_name, compressed_temp_path)

        comp_type = stored_file.compression_type.lower()
        if comp_type == "gzip":
            decompress_file_gzip(compressed_temp_path, decompressed_temp_path)
        elif comp_type == "zip":
            decompress_file_zip(compressed_temp_path, decompressed_temp_path, stored_file.original_name)
        else:
            shutil.copy2(compressed_temp_path, decompressed_temp_path)

    except Exception as e:
        if os.path.exists(compressed_temp_path):
            os.remove(compressed_temp_path)
        if os.path.exists(decompressed_temp_path):
            os.remove(decompressed_temp_path)
        raise HTTPException(status_code=500, detail=f"Retrieval / Decompression failed: {str(e)}")

    if os.path.exists(compressed_temp_path):
        os.remove(compressed_temp_path)

    log_action(db, current_user.id, "DOWNLOAD", f"Downloaded file: {stored_file.original_name}")

    def iter_file():
        try:
            with open(decompressed_temp_path, mode="rb") as f_like:
                yield from f_like
        finally:
            if os.path.exists(decompressed_temp_path):
                os.remove(decompressed_temp_path)

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={stored_file.original_name}"}
    )


# File Registry Deletion
@app.delete("/api/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    stored_file = db.query(models.StoredFile).filter(
        models.StoredFile.id == file_id,
        models.StoredFile.user_id == current_user.id
    ).first()
    if not stored_file:
        raise HTTPException(status_code=404, detail="File registry record not found")

    account = db.query(models.StorageAccount).filter(
        models.StorageAccount.id == stored_file.account_id,
        models.StorageAccount.user_id == current_user.id
    ).first()
    if account:
        try:
            client = get_storage_client(account)
            client.delete_file(stored_file.stored_name)
            account.used_space = client.get_used_space()
            db.add(account)
        except Exception as e:
            account.used_space = max(0, account.used_space - stored_file.compressed_size)
            db.add(account)
            print(f"Error deleting cloud file or updating space: {e}")

    log_action(db, current_user.id, "DELETE_FILE", f"Deleted file: {stored_file.original_name}")

    db.delete(stored_file)
    db.commit()
    return {"status": "success", "message": "File deleted"}


# Aggregated Metrics API
@app.get("/api/stats", response_model=schemas.DashboardStats)
def get_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    files = db.query(models.StoredFile).filter(models.StoredFile.user_id == current_user.id).all()
    accounts = db.query(models.StorageAccount).filter(models.StorageAccount.user_id == current_user.id).all()

    total_files = len(files)
    original_size_total = sum(f.original_size for f in files)
    compressed_size_total = sum(f.compressed_size for f in files)
    space_saved_bytes = max(0, original_size_total - compressed_size_total)
    
    saving_ratio = 0.0
    if original_size_total > 0:
        saving_ratio = round((space_saved_bytes / original_size_total) * 100, 1)

    provider_distribution = {}
    for f in files:
        provider_distribution[f.cloud_provider] = provider_distribution.get(f.cloud_provider, 0) + 1

    account_usage = []
    for account in accounts:
        if account.is_active:
            try:
                client = get_storage_client(account)
                account.used_space = client.get_used_space()
                if hasattr(client, "get_total_quota"):
                    tq = client.get_total_quota()
                    if tq:
                        account.quota_limit = tq
            except Exception:
                pass
        
        provider_displays = {
            "s3": "AWS S3",
            "gcs": "GCP Cloud Storage",
            "gdrive": "Google Drive",
            "dropbox": "Dropbox",
            "mock": "Mock Drive"
        }
        provider_name = provider_displays.get(account.provider, "Mock Drive")
        if account.is_mock:
            provider_name = f"Mock {provider_name}"
            
        account_usage.append({
            "id": account.id,
            "display_name": account.display_name,
            "provider": provider_name,
            "provider_type": account.provider,
            "quota_limit": account.quota_limit,
            "used_space": account.used_space,
            "is_mock": account.is_mock,
            "is_active": account.is_active
        })
    
    db.commit()

    return {
        "total_files": total_files,
        "original_size_total": original_size_total,
        "compressed_size_total": compressed_size_total,
        "space_saved_bytes": space_saved_bytes,
        "saving_ratio": saving_ratio,
        "provider_distribution": provider_distribution,
        "account_usage": account_usage
    }
