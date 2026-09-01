import os
import sys
import zipfile
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

URL = sys.argv[1]
FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")
CREDENTIALS_JSON = os.environ.get("GDRIVE_CREDENTIALS")

# Initialize Google Drive API
with open("credentials.json", "w") as f:
    f.write(CREDENTIALS_JSON)

creds = service_account.Credentials.from_service_account_file(
    "credentials.json", 
    scopes=["https://googleapis.com"]
)
drive_service = build("drive", "v3", credentials=creds)

def download_file(url, dest):
    print(f"Downloading large file: {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024): # 1MB chunks
                if chunk:
                    f.write(chunk)
    print("Download finished.")

def create_gdrive_folder(name, parent_id):
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_to_gdrive(local_path, parent_id):
    AUDIO_EXTENSIONS = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')
    
    if os.path.isdir(local_path):
        # We only want to create remote folders if they contain files
        items = os.listdir(local_path)
        if items:
            folder_name = os.path.basename(local_path)
            new_parent_id = create_gdrive_folder(folder_name, parent_id)
            for item in items:
                upload_to_gdrive(os.path.join(local_path, item), new_parent_id)
    else:
        file_name = os.path.basename(local_path)
        if file_name.lower().endswith(AUDIO_EXTENSIONS):
            print(f"Uploading music file: {file_name}")
            file_metadata = {'name': file_name, 'parents': [parent_id]}
            media = MediaFileUpload(local_path, resumable=True) # Resumable is key for large files
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def main():
    zip_tmp = "downloaded_archive.zip"
    extract_dir = "extracted_content"
    
    # 1. Download (GitHub servers handle 1.1GB easily)
    download_file(URL, zip_tmp)
    
    # 2. Extract
    print("Extracting ZIP file...")
    with zipfile.ZipFile(zip_tmp, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # 3. Upload only music
    print("Filtering and uploading music files to Google Drive...")
    for item in os.listdir(extract_dir):
        upload_to_gdrive(os.path.join(extract_dir, item), FOLDER_ID)
        
    print("Process Complete!")

if __name__ == "__main__":
    main()
