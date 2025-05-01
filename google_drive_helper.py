# google_drive_helper.py (수정 완료: SCOPES 일관 적용, Streamlit Secrets 사용, 업로드/검색 기능 포함)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import os
import streamlit as st
import json

# ✅ 통일된 스코프 정의
SCOPES = ['https://www.googleapis.com/auth/drive']

# === 인증 및 서비스 객체 생성 ===
def get_drive_service():
    try:
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)
    except KeyError:
        st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
        st.stop()
    except Exception as e:
        st.error(f"Google Drive 서비스 연결 중 오류 발생: {e}")
        st.stop()

# === JSON 파일 다운로드 ===
def download_json_file(file_id):
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode("utf-8")
    except Exception as e:
        st.error(f"파일 다운로드 중 오류 발생 (ID: {file_id}): {e}")
        return None

# === 정확한 이름으로 파일 ID 찾기 ===
def find_file_id_by_exact_name(exact_file_name, mime_type="application/json", folder_id=None):
    service = get_drive_service()
    escaped_file_name = exact_file_name.replace("'", "\\'")
    query = f"name = '{escaped_file_name}' and mimeType='{mime_type}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        items = results.get('files', [])
        if items:
            return items[0].get('id')
        return None
    except Exception as e:
        st.error(f"정확한 파일 검색 오류: {e}")
        return None

# === 파일 업로드 또는 업데이트 ===
def upload_or_update_json_to_drive(file_name, json_content, folder_id=None):
    service = get_drive_service()
    existing_file_id = find_file_id_by_exact_name(file_name, folder_id=folder_id)

    fh = io.BytesIO(json_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype="application/json", resumable=True)

    try:
        if existing_file_id:
            updated_file = service.files().update(
                fileId=existing_file_id,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': existing_file_id, 'status': 'updated'}
        else:
            file_metadata = {"name": file_name, "mimeType": "application/json"}
            if folder_id:
                file_metadata["parents"] = [folder_id]
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': created_file.get("id"), 'status': 'created'}
    except Exception as e:
        st.error(f"Google Drive 업로드/업데이트 오류: {e}")
        return None

# === 이름 일부 포함 검색 ===
def find_files_by_name_contains(name_query, mime_type="application/json", folder_id=None):
    service = get_drive_service()
    escaped_query = name_query.replace("'", "\\'")
    query = f"name contains '{escaped_query}' and mimeType='{mime_type}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    found_files = []
    try:
        page_token = None
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                found_files.append({'id': file.get('id'), 'name': file.get('name')})
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        return found_files
    except Exception as e:
        st.error(f"파일 검색 중 오류 발생: {e}")
        return []
