# utils.py (최종 수정본)

import re
from datetime import datetime
import pytz # 시간대 처리를 위해 필요

def get_current_kst_time_str(format="%Y-%m-%d %H:%M"):
    """
    현재 한국 표준시(KST) 기준의 날짜와 시간을 지정된 형식의 문자열로 반환합니다.
    pytz 라이브러리가 없거나 시간대 변환 실패 시 시스템 기본 시간 사용.
    """
    try:
        kst = pytz.timezone("Asia/Seoul")
        now_kst = datetime.now(kst)
        return now_kst.strftime(format)
    except Exception as e:
        print(f"Warning: KST 시간 변환 실패 ({e}). 시스템 시간 사용.")
        return datetime.now().strftime(format)

def extract_phone_number_part(phone_str, length=4, default="번호없음"):
    """
    전화번호 문자열에서 숫자만 추출하여 뒤에서부터 지정된 길이만큼 반환합니다.
    유효한 숫자 부분이 없거나 부족하면 default 값을 반환합니다.
    """
    if not phone_str or not isinstance(phone_str, str):
        return default
    digits = re.sub(r'\D', '', phone_str) # 숫자 외 문자 제거
    if len(digits) >= length:
        return digits[-length:] # 뒤 length 자리 반환
    elif len(digits) > 0:
        return digits # 짧으면 있는 숫자라도 반환
    else:
        return default # 숫자가 없으면 기본값 반환