# mms_utils.py
import streamlit as st
import requests # MMS 게이트웨이 연동 시 필요할 수 있는 라이브러리 (예시)
import traceback
import re # 전화번호 정규화용

def normalize_phone_number(phone_number_str):
    """
    국제 표준 형식(예: +821012345678) 또는 국내 형식(01012345678)으로 변환 시도.
    실제 사용하시는 MMS 게이트웨이가 요구하는 형식으로 맞춰야 합니다.
    이 함수는 매우 기본적인 정규화만 수행합니다.
    """
    if not phone_number_str or not isinstance(phone_number_str, str):
        return None
    
    # 모든 비숫자 문자 제거
    digits = re.sub(r'\D', '', phone_number_str)

    if not digits:
        return None

    # 예시: 010으로 시작하고 11자리인 경우 (한국 휴대폰)
    if digits.startswith('010') and len(digits) == 11:
        # 게이트웨이에 따라 '+8210...' 또는 '010...' 형태를 요구할 수 있음
        # 여기서는 '010...' 형태를 기본으로 반환
        return digits
    # 예시: 10으로 시작하고 10자리인 경우 (0 제외)
    elif digits.startswith('10') and len(digits) == 10:
        return '0' + digits
    # 기타 국제번호 형식 등은 게이트웨이 문서 참조하여 추가 규칙 필요
    
    # 위 조건에 맞지 않으면, 일단 숫자만 반환 (게이트웨이가 처리할 수도 있음)
    # 하지만, 대부분의 게이트웨이는 특정 형식을 요구합니다.
    st.warning(f"전화번호({phone_number_str})가 표준 형식에 맞지 않을 수 있습니다. MMS 게이트웨이 요구사항을 확인하세요.")
    return digits


def send_mms_with_image(recipient_phone, image_bytes, filename="견적서.jpg", text_message="견적서가 도착했습니다."):
    """
    이미지를 MMS로 발송합니다. (실제 게이트웨이 연동 필요)
    recipient_phone: 수신자 전화번호 (문자열)
    image_bytes: 발송할 이미지의 바이트 데이터
    filename: 이미지 파일명 (MMS 전송 시 사용될 수 있음)
    text_message: 이미지와 함께 전송될 문자 메시지
    """
    st.info(f"MMS 기능은 `mms_utils.py`에 실제 게이트웨이 연동 코드를 작성해야 합니다.")
    st.info(f"요청 정보: 수신자={recipient_phone}, 파일명={filename}")

    if not recipient_phone:
        st.error("MMS 발송 실패: 수신자 전화번호가 없습니다.")
        return False
    
    normalized_phone = normalize_phone_number(recipient_phone)
    if not normalized_phone:
        st.error(f"MMS 발송 실패: 유효하지 않은 수신자 전화번호 형식입니다 ({recipient_phone}).")
        return False

    if not image_bytes:
        st.error("MMS 발송 실패: 발송할 이미지 데이터가 없습니다.")
        return False

    try:
        # --- Streamlit Secrets에서 MMS 게이트웨이 자격 증명 및 정보 로드 ---
        # 실제 사용하는 키 이름으로 secrets.toml 파일에 맞춰 수정해야 합니다.
        mms_creds = st.secrets.get("mms_credentials", {})
        api_key = mms_creds.get("api_key")
        api_secret = mms_creds.get("api_secret") # 또는 username/password 등
        sender_number = mms_creds.get("sender_number") # 발신번호
        gateway_url = mms_creds.get("gateway_url") # MMS API 엔드포인트

        if not all([api_key, sender_number, gateway_url]):
            st.error("MMS 발송 실패: Streamlit Secrets에 MMS 설정이 완전하지 않습니다. "
                     "('.streamlit/secrets.toml' 파일에 [mms_credentials] 섹션과 "
                     "api_key, sender_number, gateway_url 등을 확인하세요.)")
            return False

        # --- !!! 아래는 실제 MMS 게이트웨이 API 호출 로직으로 대체되어야 합니다 !!! ---
        # 사용 중인 MMS 서비스 제공업체의 API 문서를 참조하여 작성하세요.
        # 다음은 일반적인 `requests` 라이브러리 사용 예시이며, 실제로는 매우 다를 수 있습니다.

        st.warning(f"실제 MMS 발송 로직은 `mms_utils.py` 파일의 이 부분에 {gateway_url} 게이트웨이 연동 코드를 작성해야 합니다.")
        print(f"DEBUG [MMS]: Attempting to send MMS via {gateway_url}")
        print(f"DEBUG [MMS]: To: {normalized_phone}, From: {sender_number}, Text: {text_message}, Image: {filename} ({len(image_bytes)} bytes)")
        print(f"DEBUG [MMS]: API Key: {api_key[:4]}...") # 실제 키 전체를 로그에 남기지 않도록 주의

        # # 예시: requests 라이브러리를 사용한 API 호출 (실제 게이트웨이마다 다름)
        # headers = {
        #     # "Authorization": f"Bearer {api_key}", # 인증 방식에 따라 다름
        #     # "Content-Type": "multipart/form-data" # 파일 첨부 시 일반적
        # }
        # payload = {
        #     'api_key': api_key, # 또는 다른 인증 파라미터
        #     'api_secret': api_secret,
        #     'to': normalized_phone, # 수신번호 (쉼표로 여러명 가능할 수도 있음)
        #     'from': sender_number, # 발신번호
        #     'message': text_message, # 문자 메시지
        #     'subject': f"{st.session_state.get('customer_name','고객')}님 견적서", # MMS 제목 (지원 시)
        #     # 'type': 'MMS', # 메시지 타입 (LMS, SMS 등 구분)
        #     # 기타 필요한 파라미터 (예: 국가 코드, 예약 발송 등)
        # }
        # files = {
        #     'image': (filename, image_bytes, 'image/jpeg') # 파일 파라미터 이름, 파일명, 데이터, MIME 타입
        # }
        #
        # # response = requests.post(gateway_url, headers=headers, data=payload, files=files, timeout=30)
        # # response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        #
        # # 게이트웨이 응답 처리 (성공/실패 판단 로직은 API 문서 참조)
        # response_data = response.json() # 응답이 JSON 형태일 경우
        # if response_data.get("result_code") == "success": # 또는 response.status_code == 200 등
        #     print(f"DEBUG [MMS]: MMS sent successfully via gateway. Response: {response_data}")
        #     # st.success(f"{normalized_phone}(으)로 견적서 MMS 발송 성공!") # 실제 성공 시 이 메시지 사용
        #     return True # 실제 성공 시 True 반환
        # else:
        #     error_msg = response_data.get("message", "알 수 없는 게이트웨이 오류")
        #     print(f"ERROR [MMS]: MMS gateway error. Code: {response_data.get('result_code')}, Msg: {error_msg}")
        #     # st.error(f"MMS 발송 실패 (게이트웨이): {error_msg}") # 실제 실패 시 이 메시지 사용
        #     return False # 실제 실패 시 False 반환

        # 현재는 실제 구현이 없으므로 False 반환
        return False 
        # --- !!! 실제 API 호출 로직 끝 !!! ---

    except KeyError as e:
        st.error(f"MMS 발송 실패: Streamlit Secrets 설정 오류 ({e}). "
                 "'.streamlit/secrets.toml'의 [mms_credentials] 섹션을 확인하세요.")
        traceback.print_exc()
        return False
    except requests.exceptions.RequestException as e: # requests 사용 시 발생 가능
        st.error(f"MMS API 요청 중 네트워크 오류 발생: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        st.error(f"MMS 발송 중 예상치 못한 오류 발생: {e}")
        traceback.print_exc()
        return False
