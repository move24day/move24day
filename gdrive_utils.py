# gdrive_utils.py

import streamlit as st
import io
import json
import os
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError

# --- Configuration ---
# !!! 중요: 실제 Google Drive 폴더 ID로 교체하세요 !!!
# 예: '1aBcDeFgHiJkLmNoPqRsTuVwXyZ12345'
# 해당 폴더는 반드시 서비스 계정 이메일 주소와 공유되어야 합니다.
TARGET_FOLDER_ID = "1S4_msysMqLDN_gGwj32Poy6qbGE63lOf"

# !!! 중요: 'credentials.json' 파일을 앱과 같은 디렉토리에 두거나 정확한 경로를 지정하세요. !!!
# 이 파일은 Git 등 버전 관리에 포함시키지 마세요 (.gitignore에 추가).
creds_json = st.secrets["gcp_service_account"]
creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)

# --- Authentication ---
@st.cache_resource(ttl=3600) # 1시간 동안 자격 증명 캐시
def get_credentials():
    """서비스 계정 자격 증명을 로드하고 반환합니다."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"Google Drive 연동 오류: '{SERVICE_ACCOUNT_FILE}' 파일을 찾을 수 없습니다. Service Account Key 파일이 필요합니다.")
        st.stop() # 파일 없으면 앱 중지
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return creds
    except Exception as e:
        st.error(f"Google Drive 연동 오류: Service Account 인증 중 오류 발생 - {e}")
        traceback.print_exc()
        st.stop() # 인증 오류 시 앱 중지
        return None

@st.cache_resource(ttl=3600) # 1시간 동안 서비스 객체 캐시
def get_drive_service():
    """Google Drive API 서비스 객체를 생성하고 반환합니다."""
    creds = get_credentials()
    if creds:
        try:
            # cache_discovery=False 는 특히 Streamlit 환경에서 발생할 수 있는 문제를 방지합니다.
            service = build('drive', 'v3', credentials=creds, cache_discovery=False)
            # 서비스가 제대로 생성되었는지 간단한 테스트 (폴더 존재 여부 확인 등)
            service.files().get(fileId=TARGET_FOLDER_ID, fields='id').execute()
            return service
        except HttpError as http_err:
            if http_err.resp.status == 404:
                st.error(f"Google Drive 연동 오류: 지정된 폴더 ID '{TARGET_FOLDER_ID}'를 찾을 수 없습니다. ID를 확인하거나 서비스 계정에 폴더 접근 권한을 부여하세요.")
            else:
                st.error(f"Google Drive 연동 오류: 서비스 연결 테스트 실패 - {http_err}")
            traceback.print_exc()
            st.stop()
            return None
        except Exception as e:
            st.error(f"Google Drive 연동 오류: 서비스 연결 중 오류 발생 - {e}")
            traceback.print_exc()
            st.stop()
            return None
    return None

# --- Core Functions ---
def search_files(search_term):
    """지정된 폴더 내에서 검색어를 포함하는 .json 파일을 찾습니다."""
    service = get_drive_service()
    if not service:
        return []

    files_found = []
    page_token = None
    try:
        query = f"name contains '{search_term}' and '{TARGET_FOLDER_ID}' in parents and mimeType='application/json' and trashed = false"
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()

            for file in response.get('files', []):
                files_found.append({"name": file.get('name'), "id": file.get('id')})

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        # 이름순으로 정렬 (최신 날짜가 위로 오도록)
        files_found.sort(key=lambda x: x['name'], reverse=True)
        return files_found
    except HttpError as error:
        st.error(f"파일 검색 중 오류 발생: {error}")
        traceback.print_exc()
        return []
    except Exception as e:
        st.error(f"파일 검색 중 예상치 못한 오류 발생: {e}")
        traceback.print_exc()
        return []

def load_file(file_id):
    """파일 ID로 Google Drive에서 파일을 다운로드하고 내용을 파싱합니다."""
    service = get_drive_service()
    if not service:
        return None

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print(f"Download {int(status.progress() * 100)}%.") # 진행률 표시 (디버깅용)

        fh.seek(0)
        file_content = fh.read().decode('utf-8') # UTF-8로 디코딩 가정
        return json.loads(file_content) # JSON 파싱하여 dict 반환

    except HttpError as error:
        st.error(f"파일 로딩 중 오류 발생 (ID: {file_id}): {error}")
        traceback.print_exc()
        return None
    except json.JSONDecodeError:
        st.error(f"파일 로딩 중 오류 발생 (ID: {file_id}): 파일이 유효한 JSON 형식이 아닙니다.")
        return None
    except Exception as e:
        st.error(f"파일 로딩 중 예상치 못한 오류 발생 (ID: {file_id}): {e}")
        traceback.print_exc()
        return None
    finally:
        if fh:
            fh.close()

def save_file(filename, data_dict):
    """데이터를 JSON 형식으로 Google Drive 폴더에 저장 (업데이트 또는 생성)"""
    service = get_drive_service()
    if not service:
        return False

    # 1. 동일한 이름의 파일이 있는지 검색
    file_id_to_update = None
    try:
        query = f"name = '{filename}' and '{TARGET_FOLDER_ID}' in parents and mimeType='application/json' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        if files:
            file_id_to_update = files[0].get('id')
            # print(f"기존 파일 발견: '{filename}' (ID: {file_id_to_update}), 업데이트합니다.") # 디버깅
    except HttpError as error:
        st.error(f"파일 존재 여부 확인 중 오류 발생: {error}")
        traceback.print_exc()
        return False
    except Exception as e:
        st.error(f"파일 존재 여부 확인 중 예상치 못한 오류 발생: {e}")
        traceback.print_exc()
        return False

    # 2. 메모리 내 파일 준비
    try:
        json_data = json.dumps(data_dict, indent=4, ensure_ascii=False)
        fh = io.BytesIO(json_data.encode('utf-8')) # BytesIO로 변환
    except Exception as e:
        st.error(f"저장할 데이터(JSON) 변환 중 오류 발생: {e}")
        traceback.print_exc()
        return False

    # 3. 파일 업로드 (업데이트 또는 생성)
    media = MediaIoBaseUpload(fh, mimetype='application/json', resumable=True)
    file_metadata = {'name': filename}

    try:
        if file_id_to_update:
            # 업데이트
            updated_file = service.files().update(
                fileId=file_id_to_update,
                media_body=media,
                fields='id'
            ).execute()
            # print(f"파일 업데이트 완료. ID: {updated_file.get('id')}") # 디버깅
        else:
            # 생성
            file_metadata['parents'] = [TARGET_FOLDER_ID]
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            # print(f"파일 생성 완료. ID: {created_file.get('id')}") # 디버깅
        return True # 성공
    except HttpError as error:
        st.error(f"파일 저장 중 오류 발생: {error}")
        traceback.print_exc()
        return False
    except Exception as e:
        st.error(f"파일 저장 중 예상치 못한 오류 발생: {e}")
        traceback.print_exc()
        return False
    finally:
        if fh:
            fh.close()

# --- Google Drive 서비스 초기 연결 시도 ---
# 앱 시작 시 서비스 연결을 시도하여 오류가 있으면 미리 알림
get_drive_service()