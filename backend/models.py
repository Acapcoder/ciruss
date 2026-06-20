import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("StorageAccount", back_populates="user", cascade="all, delete-orphan")
    files = relationship("StoredFile", back_populates="user", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class Folder(Base):
    __tablename__ = "folders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # nullable for backward compatibility
    name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("folders.id"), nullable=True)  # null = root
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="folders")

class StorageAccount(Base):
    __tablename__ = "storage_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # nullable for backward compatibility
    provider = Column(String, nullable=False)  # s3, gcs, gdrive, dropbox, mock
    display_name = Column(String, nullable=False)
    credentials_json = Column(String, nullable=True)  # encrypted string
    quota_limit = Column(BigInteger, default=5 * 1024 * 1024 * 1024)  # 5 GB default
    used_space = Column(BigInteger, default=0)
    is_active = Column(Boolean, default=True)
    is_mock = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="accounts")
    files = relationship("StoredFile", back_populates="account", cascade="all, delete-orphan")

class StoredFile(Base):
    __tablename__ = "stored_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # nullable for backward compatibility
    folder_id = Column(String, ForeignKey("folders.id"), nullable=True)  # null = root
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False)
    compression_type = Column(String, nullable=False)  # gzip, zip, none
    original_size = Column(BigInteger, nullable=False)
    compressed_size = Column(BigInteger, nullable=False)
    cloud_provider = Column(String, nullable=False)  # display name of provider
    web_link = Column(String, nullable=True)  # link to open the file on the provider's web dashboard
    account_id = Column(String, ForeignKey("storage_accounts.id"), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="files")
    account = relationship("StorageAccount", back_populates="files")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # nullable for system/non-user logs
    action = Column(String, nullable=False)  # UPLOAD, DOWNLOAD, DELETE, LOGIN, SIGNUP, etc.
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")
