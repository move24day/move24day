# google_drive_helper.py (Streamlit Secrets 사용, 덮어쓰기 기능, 이름 포함 검색 기능 추가)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload, HttpError
import io
import os
import streamlit as st
import json # JSON 파싱 위해 추가

# Streamlit Secrets에서 서비스 계정 정보 읽기
# secrets.toml 파일에 다음과 같이 설정해야 합니다:
# [gcp_service_account]
# type = "service_account"
# project_id = "your-project-id"
# ... (나머지 서비스 계정 정보) ...

def get_drive_service():
    """Streamlit Secrets를 사용하여 Google Drive 서비스 객체를 반환합니다."""
    try:
        # secrets.toml의 'gcp_service_account' 섹션 전체를 사용
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except KeyError:
        st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
        st.stop()
    except Exception as e:
        st.error(f"Google Drive 서비스 연결 중 오류 발생: {e}")
        st.stop()

def download_json_file(file_id):
    """지정된 파일 ID의 JSON 파일을 다운로드하여 내용을 반환합니다."""
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            # print(f"Download {int(status.progress() * 100)}%.") # 진행률 표시 (필요시)
        fh.seek(0)
        return fh.read().decode("utf-8")
    except HttpError as error:
        st.error(f"파일 다운로드 중 오류 발생 (ID: {file_id}): {error}")
        return None
    except Exception as e:
        st.error(f"파일 다운로드 처리 중 예외 발생: {e}")
        return None

def find_file_id_by_exact_name(exact_file_name, mime_type="application/json", folder_id=None):
    """지정된 정확한 이름과 MIME 유형을 가진 파일 ID를 찾습니다 (특정 폴더 내에서 검색 가능)."""
    service = get_drive_service()
    # 파일 이름에 작은 따옴표가 포함될 경우 이스케이프 처리 필요
    escaped_file_name = exact_file_name.replace("'", "\\'")
    query = f"name = '{escaped_file_name}' and mimeType='{mime_type}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1 # 정확히 일치하는 첫번째 파일만 필요
        ).execute()
        items = results.get('files', [])
        if items:
            return items[0].get('id') # 첫 번째 일치하는 파일 ID 반환
        return None
    except HttpError as error:
        # 권한 오류 등일 수 있음
        print(f"Google Drive API Error (find_file_id_by_exact_name): {error}")
        st.error(f"정확한 파일 검색 중 오류 발생 (Name: {exact_file_name}). 권한 또는 폴더 ID를 확인하세요.")
        return None
    except Exception as e:
        st.error(f"정확한 파일 검색 처리 중 예외 발생: {e}")
        return None

def upload_or_update_json_to_drive(file_name, json_content, folder_id=None):
    """
    JSON 데이터를 Google Drive에 업로드하거나 동일한 이름의 파일이 있으면 업데이트합니다.
    Returns:
        dict: {'id': file_id, 'status': 'created' or 'updated'} 또는 오류 시 None
    """
    service = get_drive_service()
    existing_file_id = find_file_id_by_exact_name(file_name, folder_id=folder_id)

    fh = io.BytesIO(json_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype="application/json", resumable=True)

    try:
        if existing_file_id:
            # 파일 업데이트
            updated_file = service.files().update(
                fileId=existing_file_id,
                media_body=media,
                fields="id, name" # 필요한 필드 요청 (디버깅용)
            ).execute()
            print(f"File updated: ID={updated_file.get('id')}, Name={updated_file.get('name')}") # 로그 추가
            return {'id': existing_file_id, 'status': 'updated'}
        else:
            # 파일 생성
            file_metadata = {"name": file_name, "mimeType": "application/json"}
            if folder_id:
                file_metadata["parents"] = [folder_id] # 부모 폴더 설정
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name" # 필요한 필드 요청
            ).execute()
            print(f"File created: ID={created_file.get('id')}, Name={created_file.get('name')}") # 로그 추가
            return {'id': created_file.get("id"), 'status': 'created'}
    except HttpError as error:
        print(f"Google Drive API Error (upload_or_update_json_to_drive): {error}")
        st.error(f"Google Drive 업로드/업데이트 중 오류 발생 (Name: {file_name}). 권한 또는 폴더 ID를 확인하세요.")
        return None
    except Exception as e:
        st.error(f"Google Drive 업로드/업데이트 처리 중 예외 발생: {e}")
        return None

def find_files_by_name_contains(name_query, mime_type="application/json", folder_id=None):
    """
    지정된 문자열을 이름에 포함하고 지정된 MIME 유형을 가진 파일 목록을 찾습니다 (폴더 지정 가능).
    (기존 find_files_by_prefix 에서 startswith 검사 제거)
    """
    service = get_drive_service()
    # 검색어에 작은 따옴표 이스케이프 처리
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