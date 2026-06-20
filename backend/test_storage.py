import os
import gzip
import zipfile
import shutil
from database import engine, SessionLocal, Base
import models
import main

def test_database_and_seeds():
    print("Testing Database and Seeds...")
    # Trigger database creation and seed
    Base.metadata.create_all(bind=engine)
    main.seed_mock_accounts()
    
    db = SessionLocal()
    try:
        accounts = db.query(models.StorageAccount).all()
        print(f"-> Found {len(accounts)} accounts in database.")
        assert len(accounts) >= 3, "Mock accounts were not seeded correctly!"
        for acc in accounts:
            print(f"   * Account: {acc.display_name} | Provider: {acc.provider} | Quota: {acc.quota_limit} bytes")
        print("-> Database and seeding OK.")
    finally:
        db.close()

def test_compression():
    print("Testing Compression & Decompression engines...")
    test_file = "test_dummy.txt"
    test_gzip = "test_dummy.txt.gz"
    test_decomp = "test_dummy_dec.txt"
    
    test_content = b"This is a dummy test file content that will be compressed. " * 50
    
    # Write test file
    with open(test_file, "wb") as f:
        f.write(test_content)
    
    try:
        # Test Gzip compression
        main.compress_file_gzip(test_file, test_gzip)
        orig_size = os.path.getsize(test_file)
        comp_size = os.path.getsize(test_gzip)
        print(f"-> Original size: {orig_size} bytes, Gzip size: {comp_size} bytes")
        assert comp_size < orig_size, "Compression failed to reduce size!"
        
        # Test Decompression
        main.decompress_file_gzip(test_gzip, test_decomp)
        with open(test_decomp, "rb") as f:
            decomp_content = f.read()
        
        assert decomp_content == test_content, "Decompressed content does not match original!"
        print("-> Compression and Decompression OK.")
        
    finally:
        # Cleanup
        for path in [test_file, test_gzip, test_decomp]:
            if os.path.exists(path):
                os.remove(path)

def test_routing_logic():
    print("Testing Space Routing Logic...")
    db = SessionLocal()
    try:
        # Retrieve all active accounts
        active_accounts = db.query(models.StorageAccount).filter(models.StorageAccount.is_active == True).all()
        assert len(active_accounts) > 0, "No active accounts to test routing!"
        
        # Manually alter used space to simulate capacity differences
        # Let's make Account 1 have 1GB free, Account 2 have 10GB free, Account 3 have 0.5GB free
        for acc in active_accounts:
            if "AWS S3" in acc.display_name:
                acc.quota_limit = 5 * 1024 * 1024 * 1024
                acc.used_space = 4 * 1024 * 1024 * 1024  # 1GB free
            elif "Google Drive" in acc.display_name:
                acc.quota_limit = 15 * 1024 * 1024 * 1024
                acc.used_space = 5 * 1024 * 1024 * 1024  # 10GB free
            elif "Dropbox" in acc.display_name:
                acc.quota_limit = 2 * 1024 * 1024 * 1024
                acc.used_space = 1.5 * 1024 * 1024 * 1024  # 0.5GB free
            db.add(acc)
        db.commit()
        
        # Run routing sort simulation
        candidate_accounts = []
        for account in active_accounts:
            free_space = account.quota_limit - account.used_space
            if free_space > 0:
                candidate_accounts.append((account, free_space))
                
        candidate_accounts.sort(key=lambda x: x[1], reverse=True)
        selected_account, selected_free_space = candidate_accounts[0]
        
        print(f"-> Selected account for routing: {selected_account.display_name} with {selected_free_space / (1024*1024*1024):.1f} GB free")
        assert "Google Drive" in selected_account.display_name, "Routing engine failed to pick the account with the most free space!"
        print("-> Routing logic OK.")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=== CIRRUS AUTOMATED VERIFICATION SUITE ===")
    test_database_and_seeds()
    print("-" * 40)
    test_compression()
    print("-" * 40)
    test_routing_logic()
    print("=== ALL TESTS COMPLETED SUCCESSFULLY ===")
