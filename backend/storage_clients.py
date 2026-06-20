import os
import json
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Any

from crypto_utils import decrypt_data

# Lazy loading wrappers to handle missing dependencies or authentication failures
class StorageProviderClient(ABC):
    @abstractmethod
    def get_used_space(self) -> int:
        pass

    @abstractmethod
    def upload_file(self, file_path: str, filename: str) -> str:
        """Uploads file and returns its remote unique stored name/ID"""
        pass

    @abstractmethod
    def download_file(self, stored_name: str, download_path: str):
        pass

    @abstractmethod
    def delete_file(self, stored_name: str):
        pass


class MockStorageClient(StorageProviderClient):
    def __init__(self, account_id: str):
        self.storage_dir = os.path.join(os.path.dirname(__file__), "mock_storage", account_id)
        os.makedirs(self.storage_dir, exist_ok=True)

    def get_used_space(self) -> int:
        total = 0
        for entry in os.scandir(self.storage_dir):
            if entry.is_file():
                total += entry.stat().st_size
        return total

    def upload_file(self, file_path: str, filename: str) -> str:
        dest_path = os.path.join(self.storage_dir, filename)
        shutil.copy2(file_path, dest_path)
        return filename

    def download_file(self, stored_name: str, download_path: str):
        src_path = os.path.join(self.storage_dir, stored_name)
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Mock file {stored_name} not found.")
        shutil.copy2(src_path, download_path)

    def delete_file(self, stored_name: str):
        src_path = os.path.join(self.storage_dir, stored_name)
        if os.path.exists(src_path):
            os.remove(src_path)


class S3StorageClient(StorageProviderClient):
    def __init__(self, credentials: Dict[str, Any]):
        import boto3
        self.bucket_name = credentials.get("bucket_name")
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=credentials.get("access_key_id"),
            aws_secret_access_key=credentials.get("secret_access_key"),
            region_name=credentials.get("region", "us-east-1")
        )

    def get_used_space(self) -> int:
        total = 0
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name):
            for obj in page.get("Contents", []):
                total += obj["Size"]
        return total

    def upload_file(self, file_path: str, filename: str) -> str:
        self.s3.upload_file(file_path, self.bucket_name, filename)
        return filename

    def download_file(self, stored_name: str, download_path: str):
        self.s3.download_file(self.bucket_name, stored_name, download_path)

    def delete_file(self, stored_name: str):
        self.s3.delete_object(Bucket=self.bucket_name, Key=stored_name)


class GCSStorageClient(StorageProviderClient):
    def __init__(self, credentials: Dict[str, Any]):
        from google.cloud import storage
        self.bucket_name = credentials.get("bucket_name")
        service_account_info = credentials.get("service_account_json")
        if isinstance(service_account_info, str):
            service_account_info = json.loads(service_account_info)
        self.client = storage.Client.from_service_account_info(service_account_info)
        self.bucket = self.client.bucket(self.bucket_name)

    def get_used_space(self) -> int:
        total = 0
        blobs = self.client.list_blobs(self.bucket)
        for blob in blobs:
            total += blob.size
        return total

    def upload_file(self, file_path: str, filename: str) -> str:
        blob = self.bucket.blob(filename)
        blob.upload_from_filename(file_path)
        return filename

    def download_file(self, stored_name: str, download_path: str):
        blob = self.bucket.blob(stored_name)
        blob.download_to_filename(download_path)

    def delete_file(self, stored_name: str):
        blob = self.bucket.blob(stored_name)
        if blob.exists():
            blob.delete()


class GoogleDriveStorageClient(StorageProviderClient):
    def __init__(self, credentials: Dict[str, Any]):
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials as OAuthCredentials
        from google.auth.transport.requests import Request

        # Support both Service Account and User OAuth tokens
        service_account_info = credentials.get("service_account_json")
        if service_account_info:
            if isinstance(service_account_info, str):
                service_account_info = json.loads(service_account_info)
            creds = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
        else:
            # Fallback to OAuth credentials
            creds = OAuthCredentials(
                token=credentials.get("access_token"),
                refresh_token=credentials.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=credentials.get("client_id"),
                client_secret=credentials.get("client_secret"),
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            # Refresh-token-only credentials have no access token yet (and no
            # expiry), so refresh whenever the creds aren't currently valid.
            if not creds.valid and creds.refresh_token:
                creds.refresh(Request())

        self.service = build("drive", "v3", credentials=creds)
        self.folder_id = credentials.get("folder_id")  # Optional folder limit

    def get_used_space(self) -> int:
        # Google Drive quota endpoint returns overall account usage and limit
        about = self.service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})
        used = int(quota.get("usage", 0))
        return used

    def upload_file(self, file_path: str, filename: str) -> str:
        from googleapiclient.http import MediaFileUpload
        file_metadata = {"name": filename}
        if self.folder_id:
            file_metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        return file.get("id")

    def download_file(self, stored_name: str, download_path: str):
        # Here, stored_name holds the actual Google Drive File ID returned by upload_file
        from googleapiclient.http import MediaIoBaseDownload
        import io
        request = self.service.files().get_media(fileId=stored_name)
        with open(download_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

    def delete_file(self, stored_name: str):
        try:
            self.service.files().delete(fileId=stored_name).execute()
        except Exception:
            pass

    def get_web_link(self, stored_name: str) -> str:
        # stored_name is the Drive file ID; this opens the file directly in Drive.
        return f"https://drive.google.com/file/d/{stored_name}/view"

    def get_total_quota(self):
        about = self.service.about().get(fields="storageQuota").execute()
        q = about.get("storageQuota", {})
        return int(q["limit"]) if q.get("limit") else None


class OneDriveStorageClient(StorageProviderClient):
    """Microsoft OneDrive via Graph API, using a stored refresh token."""
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    GRAPH = "https://graph.microsoft.com/v1.0"
    SCOPE = "Files.ReadWrite offline_access User.Read"

    def __init__(self, credentials: Dict[str, Any]):
        import requests
        self.requests = requests
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.refresh_token = credentials["refresh_token"]
        self.token = self._refresh()

    def _refresh(self) -> str:
        r = self.requests.post(self.TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "scope": self.SCOPE,
        })
        r.raise_for_status()
        return r.json()["access_token"]

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get_used_space(self) -> int:
        r = self.requests.get(f"{self.GRAPH}/me/drive", headers=self._h())
        r.raise_for_status()
        return int(r.json().get("quota", {}).get("used", 0))

    def upload_file(self, file_path: str, filename: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        url = f"{self.GRAPH}/me/drive/root:/CIRRUS/{filename}:/content"
        r = self.requests.put(url, headers={**self._h(), "Content-Type": "application/octet-stream"}, data=data)
        r.raise_for_status()
        return r.json()["id"]  # stored_name = Graph item id

    def download_file(self, stored_name: str, download_path: str):
        r = self.requests.get(f"{self.GRAPH}/me/drive/items/{stored_name}/content", headers=self._h())
        r.raise_for_status()
        with open(download_path, "wb") as f:
            f.write(r.content)

    def delete_file(self, stored_name: str):
        try:
            self.requests.delete(f"{self.GRAPH}/me/drive/items/{stored_name}", headers=self._h())
        except Exception:
            pass

    def get_web_link(self, stored_name: str):
        try:
            r = self.requests.get(f"{self.GRAPH}/me/drive/items/{stored_name}?select=webUrl", headers=self._h())
            return r.json().get("webUrl")
        except Exception:
            return None


class DropboxStorageClient(StorageProviderClient):
    """Dropbox via HTTP API, using a stored refresh token (long-lived)."""
    def __init__(self, credentials: Dict[str, Any]):
        import requests
        self.requests = requests
        self.refresh_token = credentials.get("refresh_token")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.token = credentials.get("access_token")
        if self.refresh_token:
            self.token = self._refresh()

    def _refresh(self) -> str:
        r = self.requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            auth=(self.client_id, self.client_secret),
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get_used_space(self) -> int:
        r = self.requests.post("https://api.dropboxapi.com/2/users/get_space_usage", headers=self._h())
        r.raise_for_status()
        return int(r.json().get("used", 0))

    def get_total_quota(self):
        r = self.requests.post("https://api.dropboxapi.com/2/users/get_space_usage", headers=self._h())
        r.raise_for_status()
        allocated = r.json().get("allocation", {}).get("allocated")
        return int(allocated) if allocated else None

    def upload_file(self, file_path: str, filename: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        arg = {"path": f"/{filename}", "mode": "add", "autorename": True, "mute": True}
        r = self.requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers={**self._h(), "Content-Type": "application/octet-stream", "Dropbox-API-Arg": json.dumps(arg)},
            data=data,
        )
        r.raise_for_status()
        return r.json()["path_lower"]  # stored_name = dropbox path

    def download_file(self, stored_name: str, download_path: str):
        r = self.requests.post(
            "https://content.dropboxapi.com/2/files/download",
            headers={**self._h(), "Dropbox-API-Arg": json.dumps({"path": stored_name})},
        )
        r.raise_for_status()
        with open(download_path, "wb") as f:
            f.write(r.content)

    def delete_file(self, stored_name: str):
        try:
            self.requests.post(
                "https://api.dropboxapi.com/2/files/delete_v2",
                headers={**self._h(), "Content-Type": "application/json"},
                data=json.dumps({"path": stored_name}),
            )
        except Exception:
            pass

    def get_web_link(self, stored_name: str):
        try:
            r = self.requests.post(
                "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
                headers={**self._h(), "Content-Type": "application/json"},
                data=json.dumps({"path": stored_name}),
            )
            if r.status_code == 200:
                return r.json().get("url")
            # Link already exists — fetch it.
            r2 = self.requests.post(
                "https://api.dropboxapi.com/2/sharing/list_shared_links",
                headers={**self._h(), "Content-Type": "application/json"},
                data=json.dumps({"path": stored_name}),
            )
            links = r2.json().get("links", [])
            return links[0]["url"] if links else None
        except Exception:
            return None


def get_storage_client(account) -> StorageProviderClient:
    """Helper to instantiate client from DB Account record"""
    if account.is_mock:
        return MockStorageClient(account.id)

    # Browser-automation providers need no stored credentials — they reuse a
    # persistent browser profile keyed by the account id (see browser_drive.py).
    from browser_drive import BROWSER_PROVIDERS, get_browser_client
    if account.provider in BROWSER_PROVIDERS:
        return get_browser_client(account.provider, account.id)

    # Decrypt credentials
    creds_str = decrypt_data(account.credentials_json)
    if not creds_str:
        raise ValueError("Unable to decrypt credentials for this storage account.")
    
    credentials = json.loads(creds_str)
    
    if account.provider == "s3":
        return S3StorageClient(credentials)
    elif account.provider == "gcs":
        return GCSStorageClient(credentials)
    elif account.provider == "gdrive":
        return GoogleDriveStorageClient(credentials)
    elif account.provider == "onedrive":
        return OneDriveStorageClient(credentials)
    elif account.provider == "dropbox":
        return DropboxStorageClient(credentials)
    else:
        raise ValueError(f"Unknown storage provider: {account.provider}")
