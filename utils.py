# utils.py (get_item_qty 함수 추가됨)

import re
from datetime import datetime
import pytz # 시간대 처리를 위해 필요

# data 모듈 임포트 시도 (get_item_qty에서 필요)
try:
    import data
except ImportError:
    # data 모듈 로드 실패 시 경고 출력 및 None으로 설정
    print("Warning [utils.py]: data.py not found, get_item_qty might not work correctly.")
    data = None

def get_current_kst_time_str(format="%Y-%m-%d %H:%M"):
    """
    현재 한국 표준시(KST) 기준의 날짜와 시간을 지정된 형식의 문자열로 반환합니다.
    pytz 라이브러리가 없거나 시간대 변환 실패 시 시스템 기본 시간 사용.
    """
    try:
        # 한국 시간대 객체 생성
        kst = pytz.timezone("Asia/Seoul")
        # 현재 KST 시간 가져오기
        now_kst = datetime.now(kst)
        # 지정된 포맷으로 변환하여 반환
        return now_kst.strftime(format)
    except Exception as e:
        # 시간대 변환 실패 시 경고 출력 및 시스템 기본 시간 사용
        print(f"Warning [get_current_kst_time_str]: KST time conversion failed ({e}). Using system time.")
        return datetime.now().strftime(format)

def extract_phone_number_part(phone_str, length=4, default="번호없음"):
    """
    전화번호 문자열에서 숫자만 추출하여 뒤에서부터 지정된 길이만큼 반환합니다.
    유효한 숫자 부분이 없거나 부족하면 default 값을 반환합니다.
    """
    # 입력값이 문자열이 아니거나 비어있으면 기본값 반환
    if not phone_str or not isinstance(phone_str, str):
        return default
    # 정규식을 사용하여 숫자만 추출
    digits = re.sub(r'\D', '', phone_str) # '\D'는 숫자가 아닌 모든 문자를 의미
    # 추출된 숫자의 길이가 요구 길이보다 길거나 같으면 뒤에서부터 자름
    if len(digits) >= length:
        return digits[-length:]
    # 추출된 숫자가 있지만 요구 길이보다 짧으면, 있는 숫자라도 반환
    elif len(digits) > 0:
        return digits
    # 추출된 숫자가 없으면 기본값 반환
    else:
        return default

# --- get_item_qty 함수 정의 (excel_filler.py에서 이동) ---
def get_item_qty(state_data, item_name_to_find):
    """
    state_data에서 특정 품목명의 수량을 찾아 반환합니다.
    현재 설정된 이사 유형에 따라 data.py에 정의된 섹션을 검색합니다.

    Args:
        state_data (dict): Streamlit의 session state 딕셔너리.
        item_name_to_find (str): 찾고자 하는 품목의 이름.

    Returns:
        int: 해당 품목의 수량. 찾지 못하거나 오류 발생 시 0 반환.
    """
    # data 모듈 또는 필요한 속성이 로드되지 않았는지 확인
    if not data or not hasattr(data, 'item_definitions') or not hasattr(data, 'items'):
        print(f"Warning [get_item_qty]: data module or definitions missing for item '{item_name_to_find}'")
        return 0 # 필수 데이터 없으면 0 반환

    # state_data에서 현재 이사 유형 가져오기
    current_move_type = state_data.get('base_move_type')
    if not current_move_type:
        # 이사 유형이 설정되지 않았으면 경고 출력 (선택적)
        # print(f"Warning [get_item_qty]: base_move_type not found in state_data for item '{item_name_to_find}'")
        return 0 # 이사 유형 없으면 검색 불가

    # 해당 이사 유형에 대한 품목 정의 가져오기 (없으면 빈 딕셔너리)
    item_definitions_for_type = data.item_definitions.get(current_move_type, {})

    # 품목 정의가 딕셔너리 형태인지 확인
    if isinstance(item_definitions_for_type, dict):
        # 정의된 모든 섹션(예: "주요 품목", "기타" 등) 순회
        for section, item_list in item_definitions_for_type.items():
            # 각 섹션의 품목 리스트가 실제 리스트 형태이고,
            # 찾고자 하는 품목 이름이 해당 리스트 안에 있는지 확인
            if isinstance(item_list, list) and item_name_to_find in item_list:
                # state_data에서 해당 품목의 수량 키 생성
                # (예: qty_가정 이사 🏠_주요 품목_장롱)
                key = f"qty_{current_move_type}_{section}_{item_name_to_find}"
                # state_data에 해당 키가 존재하면 값 반환 시도
                if key in state_data:
                    try:
                        # state_data에서 값 가져오기 (값이 None일 경우 0으로 처리)
                        value = state_data.get(key, 0)
                        # 값을 정수로 변환하여 반환 (정수 변환 실패 시 0 반환)
                        return int(value or 0)
                    except (ValueError, TypeError):
                        # 값 변환 중 오류 발생 시 경고 출력 (선택적)
                        # print(f"Warning [get_item_qty]: Could not convert value for key '{key}' to int.")
                        return 0 # 변환 실패 시 0 반환
                # else: 키가 state_data에 없으면 다음 섹션 검색 계속

    else:
         # 이사 유형에 대한 정의가 딕셔너리가 아닌 경우 경고 출력
         print(f"Warning [get_item_qty]: item_definitions for '{current_move_type}' is not a dictionary.")

    # 모든 섹션을 검색했지만 품목을 찾지 못한 경우 경고 출력 (선택적)
    # print(f"Warning [get_item_qty]: Item '{item_name_to_find}' not found in any section for move type '{current_move_type}'.")
    return 0 # 최종적으로 못 찾으면 0 반환
# --- 함수 추가 완료 ---
