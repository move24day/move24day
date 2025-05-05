# google_drive_helper.py (Updated for Image Handling)

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload, MediaFileUpload
import io
import json
import mimetypes # To guess image mime types

# === Authentication and Service Object Creation ===
def get_drive_service():
    """Connects to Google Drive API using service account credentials."""
    try:
        # Ensure secrets are loaded correctly
        if "gcp_service_account" not in st.secrets:
            st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
            st.stop()
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=["https://www.googleapis.com/auth/drive"] # Full drive access scope
        )
        return build("drive", "v3", credentials=creds)
    except KeyError:
        # This case is handled above, but kept for safety
        st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
        st.stop()
    except Exception as e:
        st.error(f"Google Drive 서비스 연결 중 오류 발생: {e}")
        # Consider logging the full error traceback here for debugging
        st.stop()

# === Download File Content (Generic Bytes) ===
def download_file_bytes(file_id):
    """Downloads the content of a file from Google Drive as bytes."""
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            # You could potentially add progress reporting here if needed
        fh.seek(0)
        return fh.getvalue() # Return raw bytes
    except Exception as e:
        st.error(f"파일 다운로드 중 오류 발생 (ID: {file_id}): {e}")
        return None

# === Download JSON File Content (Specific helper) ===
def download_json_file(file_id):
    """Downloads and decodes a JSON file."""
    file_bytes = download_file_bytes(file_id)
    if file_bytes:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            st.error(f"다운로드된 파일(ID: {file_id})을 UTF-8로 디코딩하는 데 실패했습니다.")
            return None
    return None # Return None if download failed

# === Find File ID by Exact Name (Handles different mime types) ===
def find_file_id_by_exact_name(exact_file_name, mime_type=None, folder_id=None):
    """Finds a file ID by its exact name, optionally filtering by mime type."""
    service = get_drive_service()
    # Escape single quotes in the file name for the query
    escaped_file_name = exact_file_name.replace("'", "\\'")
    query = f"name = '{escaped_file_name}' and trashed = false"
    if mime_type:
        query += f" and mimeType='{mime_type}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1 # We only expect one file with an exact name match
        ).execute()
        items = results.get('files', [])
        if items:
            return items[0].get('id')
        return None # Return None if no file found
    except Exception as e:
        st.error(f"정확한 파일 검색 오류 ('{exact_file_name}'): {e}")
        return None

# === Upload or Update ANY File (Handles BytesIO or FilePath) ===
def upload_or_update_file(file_name, file_content, mime_type, folder_id=None):
    """
    Uploads a new file or updates an existing file on Google Drive.
    Handles file content as bytes or a file path.
    """
    service = get_drive_service()
    # Find if a file with the same name already exists
    existing_file_id = find_file_id_by_exact_name(file_name, mime_type=mime_type, folder_id=folder_id)

    try:
        # Prepare media upload object
        if isinstance(file_content, bytes):
            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
        elif isinstance(file_content, io.BytesIO):
             file_content.seek(0) # Ensure cursor is at the start
             media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
        elif isinstance(file_content, str) and os.path.exists(file_content): # If it's a file path
            media = MediaFileUpload(file_content, mimetype=mime_type, resumable=True)
        else:
            st.error("잘못된 파일 콘텐츠 타입입니다. Bytes, BytesIO, 또는 유효한 파일 경로여야 합니다.")
            return None

        file_metadata = {"name": file_name, "mimeType": mime_type}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        if existing_file_id:
            # Update existing file
            updated_file = service.files().update(
                fileId=existing_file_id,
                body=file_metadata, # Update metadata like name if needed
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': existing_file_id, 'name': updated_file.get('name'), 'status': 'updated'}
        else:
            # Create new file
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': created_file.get("id"), 'name': created_file.get('name'), 'status': 'created'}
    except Exception as e:
        st.error(f"Google Drive 업로드/업데이트 오류 ('{file_name}'): {e}")
        import traceback
        traceback.print_exc() # Print detailed error for debugging
        return None

# === Find Files by Name Contains (Modified for flexibility) ===
def find_files_by_name_contains(name_query, mime_types=None, folder_id=None):
    """Searches for files containing name_query, optionally filtering by mime types."""
    service = get_drive_service()
    escaped_query = name_query.replace("'", "\\'")
    query = f"name contains '{escaped_query}' and trashed = false"

    # Handle mime type filtering
    if isinstance(mime_types, str): # Single mime type
        query += f" and mimeType='{mime_types}'"
    elif isinstance(mime_types, list) and mime_types: # List of mime types
        mime_query_parts = [f"mimeType='{mt}'" for mt in mime_types]
        query += f" and ({' or '.join(mime_query_parts)})"
    # If mime_types is None or empty, no mime type filter is applied

    if folder_id:
        query += f" and '{folder_id}' in parents"

    found_files = []
    try:
        page_token = None
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)', # Request mimeType too
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                found_files.append({
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mimeType': file.get('mimeType') # Include mimeType in results
                })
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        return found_files
    except Exception as e:
        st.error(f"파일 검색 중 오류 발생 ('{name_query}'): {e}")
        return []

# === Specific Save/Load for JSON (Using the generic upload function) ===
def save_json_file(file_name, data_dict, folder_id=None):
    """Saves a dictionary as a JSON file on Google Drive."""
    try:
        json_string = json.dumps(data_dict, ensure_ascii=False, indent=2)
        json_bytes = json_string.encode('utf-8')
        return upload_or_update_file(file_name, json_bytes, "application/json", folder_id)
    except Exception as e:
        st.error(f"JSON 저장 실패 ('{file_name}'): {e}")
        return None

def load_json_file(file_id):
    """Loads and parses a JSON file from Google Drive."""
    json_string = download_json_file(file_id) # Assumes download_json_file decodes
    if json_string:
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            st.error(f"불러온 파일(ID: {file_id})을 JSON으로 파싱하는 데 실패했습니다: {e}")
            return None
    return None

# === Specific Save for Images (Using the generic upload function) ===
def save_image_file(file_name, image_bytes, folder_id=None):
    """Saves image bytes as an image file on Google Drive."""
    # Guess mime type from filename, default to png if unknown
    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type or not mime_type.startswith('image/'):
         # Try common extensions if guessing failed
         if file_name.lower().endswith('.png'): mime_type = 'image/png'
         elif file_name.lower().endswith('.jpg') or file_name.lower().endswith('.jpeg'): mime_type = 'image/jpeg'
         else: mime_type = 'image/png' # Default fallback

    return upload_or_update_file(file_name, image_bytes, mime_type, folder_id)