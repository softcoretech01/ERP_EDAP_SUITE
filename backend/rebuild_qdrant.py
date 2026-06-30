import os
import shutil
import sys
import argparse

def rebuild_qdrant(force_delete=False):
    print("=========================================")
    print(" Qdrant Dimension Mismatch Fixer         ")
    print("=========================================")
    print("This script will delete your local Qdrant database to resolve dimension mismatches.")
    print("The backend server will automatically recreate the database with the correct 384 dimensions on its next startup.")
    print("WARNING: This will clear all cached schemas and documents. You will need to re-run the Schema Scanner.")
    
    qdrant_path = os.path.join(os.getcwd(), "qdrant_data")
    
    if not os.path.exists(qdrant_path):
        print(f"\n[INFO] Qdrant data directory not found at {qdrant_path}.")
        print("Nothing to do!")
        return

    if not force_delete:
        confirm = input("\nAre you sure you want to delete the Qdrant database? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    try:
        shutil.rmtree(qdrant_path)
        print("\n[SUCCESS] Successfully deleted the qdrant_data directory.")
        print("Please start your backend server (uvicorn). The new schema collections will be generated automatically!")
    except PermissionError:
        print("\n[ERROR] Permission denied. The folder is locked.")
        print("CRITICAL: You MUST stop the backend server (Ctrl+C on your uvicorn terminal) before running this script!")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild Qdrant Database")
    parser.add_argument("--force", action="store_true", help="Force deletion without prompt")
    args = parser.parse_args()
    rebuild_qdrant(force_delete=args.force)
