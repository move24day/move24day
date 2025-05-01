# app.py (UI/자동로드 원복, 이사 유형 선택만 동기화 적용 버전)

# 1. streamlit 라이브러리를 가장 먼저 임포트합니다.
import streamlit as st

# 2. 다른 st 명령어보다 반드시 먼저 set_page_config를 호출합니다.
st.set_page_config(page_title="이삿날 포장이사 견적서", layout="wide", page_icon="🚚") # 아이콘 유지

# 3. 그 다음에 다른 라이브러리들을 임포트합니다.
import pandas as pd
from datetime import datetime, date
import pytz
import base64
import math
import re
import traceback # 오류 추적용
import os
import json # JSON 처리를 위해 추가
import io # 엑셀 데이터 메모리 처리용
import excel_filler  # 새로 만든 모듈

# 4. 직접 만든 모듈들을 임포트합니다.
try:
    import data # data.py 필요
    import utils # utils.py 필요
    import pdf_generator # pdf_generator.py 필요
    import calculations # calculations.py 필요
    import gdrive_utils # gdrive_utils.py 필요
except ImportError as ie:
    st.error(f"필수 모듈 로딩 실패: {ie}. (app.py와 같은 폴더에 모든 .py 파일이 있는지 확인하세요)")
    st.stop()
except Exception as e:
    st.error(f"모듈 로딩 중 오류 발생: {e}")
    st.stop()


# --- 타이틀 ---
st.markdown("<h1 style='text-align: center; color: #1E90FF;'>🚚 이삿날 스마트 견적 시스템 🚚</h1>", unsafe_allow_html=True) # UI 개선 유지
st.write("")

# ========== 상태 저장/불러오기를 위한 키 목록 정의 ==========
# (이전과 동일)
STATE_KEYS_TO_SAVE = [
    "base_move_type", "is_storage_move", "storage_type", "apply_long_distance",
    "customer_name", "customer_phone", "from_location", "to_location", "moving_date",
    "from_floor", "from_method", "to_floor", "to_method", "special_notes",
    "storage_duration", "long_distance_selector", "vehicle_select_radio",
    "manual_vehicle_select_value", "final_selected_vehicle", "sky_hours_from",
    "sky_hours_final", "add_men", "add_women", "has_waste_check", "waste_tons_input",
    "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
    "date_opt_3_widget", "date_opt_4_widget",
    "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
    "remove_base_housewife",
    "prev_final_selected_vehicle",
    "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"
]
# =========================================================

# --- === 이사 유형 동기화 콜백 함수 정의 === ---
MOVE_TYPE_OPTIONS = list(data.item_definitions.keys()) if hasattr(data, 'item_definitions') else ["가정 이사 🏠", "사무실 이사 🏢"]

def sync_move_type(widget_key):
    """이사 유형 라디오 버튼 변경 시 호출되어 상태 동기화"""
    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if st.session_state.base_move_type != new_value:
            st.session_state.base_move_type = new_value
            # 위젯 상태도 함께 업데이트하여 즉시 반영되도록 함
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state:
                 st.session_state[other_widget_key] = new_value
            # 필요 시 rerun()을 호출하여 다른 UI 요소 업데이트
            # st.rerun()
# --- ==================================== ---

# --- 세션 상태 초기화 ---
def initialize_session_state():
    """세션 상태 변수들 초기화"""
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()
    defaults = {
        "base_move_type": MOVE_TYPE_OPTIONS[0],
        "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE,
        "apply_long_distance": False, "customer_name": "", "customer_phone": "",
        "from_location": "", "to_location": "", "moving_date": default_date,
        "from_floor": "", "from_method": data.METHOD_OPTIONS[0],
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0],
        "special_notes": "", "storage_duration": 1,
        "long_distance_selector": data.long_distance_options[0],
        "vehicle_select_radio": "자동 추천 차량 사용", "manual_vehicle_select_value": None,
        "final_selected_vehicle": None, "sky_hours_from": 1, "sky_hours_final": 1,
        "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False, "total_volume": 0.0,
        "total_weight": 0.0, "recommended_vehicle_auto": None, 'pdf_data_customer': None,
        "deposit_amount": 0, "adjustment_amount": 0, "regional_ladder_surcharge": 0,
        "remove_base_housewife": False, "prev_final_selected_vehicle": None,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "gdrive_search_term": "", "gdrive_search_results": [],
        "gdrive_file_options_map": {}, "gdrive_selected_filename": None, # 불러오기 버튼용 상태 유지
        "gdrive_selected_file_id": None, # 불러오기 버튼용 상태 유지
        "base_move_type_widget_tab1": MOVE_TYPE_OPTIONS[0], # 위젯 상태 추가/유지
        "base_move_type_widget_tab3": MOVE_TYPE_OPTIONS[0], # 위젯 상태 추가/유지
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

    # 위젯 상태 동기화
    if st.session_state.base_move_type_widget_tab1 != st.session_state.base_move_type:
        st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
    if st.session_state.base_move_type_widget_tab3 != st.session_state.base_move_type:
        st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type

    # (숫자 타입 변환 로직 등은 이전과 동일)
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount"]
    for k in int_keys + float_keys:
        try:
            val = st.session_state.get(k, defaults.get(k))
            target_type = int if k in int_keys else float
            if val is None or (isinstance(val, str) and val.strip() == ''): st.session_state[k] = defaults.get(k); continue
            converted_val = target_type(val)
            if k in int_keys:
                if k in allow_negative_keys: st.session_state[k] = converted_val
                else: st.session_state[k] = max(0, converted_val)
            else: st.session_state[k] = max(0.0, converted_val)
        except (ValueError, TypeError): st.session_state[k] = defaults.get(k)
        except KeyError: st.session_state[k] = 0 if k in int_keys else 0.0

    # (동적 품목 키 초기화 로직 등은 이전과 동일)
    processed_init_keys = set(); item_keys_to_save = []
    if hasattr(data, 'item_definitions'):
        for move_type, sections in data.item_definitions.items():
            if isinstance(sections, dict):
                for section, item_list in sections.items():
                    if section == "폐기 처리 품목 🗑️": continue
                    if isinstance(item_list, list):
                        for item in item_list:
                            if item in data.items:
                                key = f"qty_{move_type}_{section}_{item}"
                                item_keys_to_save.append(key)
                                if key not in st.session_state and key not in processed_init_keys:
                                    st.session_state[key] = 0
                                processed_init_keys.add(key)
    else: print("Warning: data.item_definitions not found during initialization.")
    global STATE_KEYS_TO_SAVE
    dispatched_keys = ["dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    STATE_KEYS_TO_SAVE = list(set(STATE_KEYS_TO_SAVE + item_keys_to_save + dispatched_keys))
    if 'prev_final_selected_vehicle' not in st.session_state:
        st.session_state['prev_final_selected_vehicle'] = st.session_state.get('final_selected_vehicle')

# ========== 상태 저장/불러오기 도우미 함수 ==========
# (prepare_state_for_save 내용은 이전과 동일, 위젯키 제외 확인)
def prepare_state_for_save(keys_to_save):
    state_to_save = {}
    actual_keys_to_save = list(set(keys_to_save + ['prev_final_selected_vehicle']) - set(['base_move_type_widget_tab1', 'base_move_type_widget_tab3']))
    for key in actual_keys_to_save:
        if key in st.session_state:
            value = st.session_state[key]
            if isinstance(value, date): state_to_save[key] = value.isoformat()
            elif isinstance(value, (str, int, float, bool, list, dict)) or value is None: state_to_save[key] = value
            else:
                 try: state_to_save[key] = str(value)
                 except: print(f"Warning: Skipping non-serializable key '{key}' of type {type(value)} during save.")
    return state_to_save

# (load_state_from_data 수정: GDrive 상태 초기화 방식 변경)
def load_state_from_data(loaded_data):
    if not isinstance(loaded_data, dict): st.error("잘못된 형식의 파일입니다 (딕셔너리가 아님)."); return False
    defaults_for_recovery = { # 기본값 정의
        "base_move_type": MOVE_TYPE_OPTIONS[0], "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE,
        "apply_long_distance": False, "customer_name": "", "customer_phone": "", "from_location": "",
        "to_location": "", "moving_date": date.today(), "from_floor": "", "from_method": data.METHOD_OPTIONS[0],
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0], "special_notes": "", "storage_duration": 1,
        "long_distance_selector": data.long_distance_options[0], "vehicle_select_radio": "자동 추천 차량 사용",
        "manual_vehicle_select_value": None, "final_selected_vehicle": None, "prev_final_selected_vehicle": None,
        "sky_hours_from": 1, "sky_hours_final": 1, "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False, "deposit_amount": 0, "adjustment_amount": 0,
        "regional_ladder_surcharge": 0, "remove_base_housewife": False,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
    }
    dynamic_keys = [key for key in STATE_KEYS_TO_SAVE if key.startswith("qty_")]
    for key in dynamic_keys:
        if key not in defaults_for_recovery: defaults_for_recovery[key] = 0
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women", "deposit_amount", "adjustment_amount", "regional_ladder_surcharge", "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount"]
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife", "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget", "date_opt_3_widget", "date_opt_4_widget"]
    load_success_count = 0; load_error_count = 0
    all_expected_keys = list(set(STATE_KEYS_TO_SAVE))
    for key in all_expected_keys:
        if key in loaded_data:
            value = loaded_data[key]; original_value = value
            try:
                target_value = None
                if key == 'moving_date':
                    if isinstance(value, str): target_value = datetime.fromisoformat(value).date()
                    elif isinstance(value, date): target_value = value
                    else: raise ValueError("Invalid date format")
                elif key.startswith("qty_"): converted_val = int(value) if value is not None else 0; target_value = max(0, converted_val)
                elif key in int_keys:
                    converted_val = int(value) if value is not None else 0
                    if key in allow_negative_keys: target_value = converted_val
                    else: target_value = max(0, converted_val)
                elif key in float_keys: converted_val = float(value) if value is not None else 0.0; target_value = max(0.0, converted_val)
                elif key in bool_keys: target_value = bool(value)
                else: target_value = value
                if key in st.session_state: st.session_state[key] = target_value; load_success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                load_error_count += 1; default_val = defaults_for_recovery.get(key)
                if key in st.session_state: st.session_state[key] = default_val
    if load_error_count > 0: st.warning(f"일부 항목({load_error_count}개) 로딩 중 오류가 발생하여 기본값으로 설정되었거나 무시되었습니다.")

    # === 로드 후 GDrive 관련 상태 초기화 (selectbox 연결 상태 직접 수정 방지) ===
    st.session_state.gdrive_search_results = []
    st.session_state.gdrive_file_options_map = {}
    # st.session_state.gdrive_selected_filename = None # <<<--- 이 라인을 삭제하거나 주석 처리하세요.
    st.session_state.gdrive_selected_file_id = None
    # 위젯 상태 동기화 로직은 유지
    if 'base_move_type' in st.session_state:
        loaded_move_type = st.session_state.base_move_type
        st.session_state.base_move_type_widget_tab1 = loaded_move_type
        st.session_state.base_move_type_widget_tab3 = loaded_move_type
    return True
# ================================================

# --- 메인 애플리케이션 로직 ---
initialize_session_state()

# --- 탭 생성 ---
tab1, tab2, tab3 = st.tabs(["👤 고객 정보", "📋 물품 선택", "💰 견적 및 비용"])

# --- 탭 1: 고객 정보 (레이아웃 원복, 불러오기 버튼 복구) ---
with tab1:
    # === Google Drive 섹션 (버튼 복구) ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        with col_load: # 불러오기
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 검색 중..."): results = gdrive_utils.search_files(search_term_strip)
                    if results:
                        st.session_state.gdrive_search_results = results
                        st.session_state.gdrive_file_options_map = {res['name']: res['id'] for res in results}
                        # 검색 결과 중 첫 번째 파일의 ID를 기본 선택 ID로 설정
                        st.session_state.gdrive_selected_file_id = results[0]['id']
                        st.success(f"✅ {len(results)}개 파일 검색 완료.")
                    else:
                        st.session_state.gdrive_search_results = []; st.session_state.gdrive_file_options_map = {}
                        st.session_state.gdrive_selected_file_id = None; st.warning("⚠️ 검색 결과가 없습니다.")
                else: st.warning("⚠️ 검색어를 입력하세요.")

            if st.session_state.gdrive_search_results:
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                # selectbox에서 선택된 이름으로 ID 업데이트
                selected_filename = st.selectbox(
                    "불러올 파일 선택:",
                    options=file_options_display,
                    key="gdrive_selected_filename",
                    index=file_options_display.index(next((name for name, fid in st.session_state.gdrive_file_options_map.items() if fid == st.session_state.gdrive_selected_file_id), file_options_display[0])) if st.session_state.gdrive_selected_file_id else 0
                )
                if selected_filename: st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_filename)

            # --- 불러오기 버튼 복구 ---
            load_button_disabled = not bool(st.session_state.gdrive_selected_file_id)
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                file_id = st.session_state.gdrive_selected_file_id
                if file_id:
                    with st.spinner(f"🔄 견적 파일 로딩 중..."):
                        loaded_data = gdrive_utils.load_file(file_id)
                    if loaded_data:
                        load_success = load_state_from_data(loaded_data)
                        if load_success:
                            st.success("✅ 견적 정보를 성공적으로 불러왔습니다.")
                            st.rerun() # UI 업데이트
                    # load_state_from_data 또는 gdrive_utils.load_file 에서 오류 처리
            # --- ----------------- ---

        with col_save: # 저장
            st.markdown("**현재 견적 저장**")
            try: kst_ex = pytz.timezone("Asia/Seoul"); now_ex_str = datetime.now(kst_ex).strftime('%y%m%d')
            except: now_ex_str = datetime.now().strftime('%y%m%d')
            phone_ex = utils.extract_phone_number_part(st.session_state.customer_phone, length=4, default="XXXX")
            example_fname = f"{now_ex_str}-{phone_ex}.json"
            st.caption(f"파일명 형식: `{example_fname}`")
            if st.button("💾 Google Drive에 저장", key="save_gdrive_btn"):
                try: kst_save = pytz.timezone("Asia/Seoul"); now_save = datetime.now(kst_save)
                except: now_save = datetime.now()
                date_str = now_save.strftime('%y%m%d')
                phone_part = utils.extract_phone_number_part(st.session_state.customer_phone, length=4)
                if phone_part == "번호없음" or not st.session_state.customer_phone.strip(): st.error("⚠️ 저장 실패: 고객 전화번호(뒤 4자리 포함)를 먼저 입력해주세요.")
                else:
                    save_filename = f"{date_str}-{phone_part}.json"
                    state_data_to_save = prepare_state_for_save(STATE_KEYS_TO_SAVE)
                    with st.spinner(f"🔄 '{save_filename}' 파일 저장 중..."): save_success = gdrive_utils.save_file(save_filename, state_data_to_save)
                    if save_success: st.success(f"✅ '{save_filename}' 파일 저장/업데이트 완료.")
                    else: st.error(f"❌ '{save_filename}' 파일 저장 중 오류 발생.")
            st.caption("동일 파일명 존재 시 덮어씁니다(업데이트).")

    st.divider() # 구분선 원복

    # --- 고객 정보 입력 필드 (레이아웃 원복) ---
    st.header("📝 고객 기본 정보") # 헤더 원복

    # 이사 유형 선택 (탭 1)
    try: current_index_tab1 = MOVE_TYPE_OPTIONS.index(st.session_state.base_move_type)
    except ValueError: current_index_tab1 = 0
    st.radio( # 라벨 원복
        "🏢 **기본 이사 유형**",
        options=MOVE_TYPE_OPTIONS, index=current_index_tab1, horizontal=True,
        key="base_move_type_widget_tab1", on_change=sync_move_type, args=("base_move_type_widget_tab1",)
    )
    # 체크박스 위치 원복
    col_opts1, col_opts2 = st.columns(2)
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move") # 라벨 원복
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance") # 라벨 원복
    st.write("") # 공백 제거 또는 유지 (선택사항)

    col1, col2 = st.columns(2) # 컬럼 레이아웃 원복
    with col1: # 왼쪽 컬럼 내용 원복
        st.text_input("👤 고객명", key="customer_name")
        st.text_input("📍 출발지 주소", key="from_location") # 라벨 원복
        if st.session_state.get('apply_long_distance'):
            st.selectbox("🛣️ 장거리 구간 선택", data.long_distance_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3")
        st.selectbox("🛠️ 출발지 작업 방법", data.METHOD_OPTIONS, key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택") # 라벨/help 원복

    with col2: # 오른쪽 컬럼 내용 원복
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678") # placeholder 원복
        st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소") # placeholder 원복
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5")
        st.selectbox("🛠️ 도착지 작업 방법", data.METHOD_OPTIONS, key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택") # help 원복
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date):
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date") # 라벨 원복
        st.caption(f"⏱️ 견적 생성일: {utils.get_current_kst_time_str()}") # 라벨 원복

    st.divider() # 구분선 원복

    # 보관 이사 정보 위치 원복
    if st.session_state.get('is_storage_move'):
        # container 제거 또는 유지 (선택사항)
        # with st.container(border=True):
        st.subheader("📦 보관이사 추가 정보") # subheader 원복
        st.radio("보관 유형 선택:", options=data.STORAGE_TYPE_OPTIONS, key="storage_type", horizontal=True)
        st.number_input("보관 기간 (일)", min_value=1, step=1, key="storage_duration") # 라벨 원복

    st.divider() # 구분선 원복

    # 고객 요구사항 위치/헤더 원복
    st.header("🗒️ 고객 요구사항") # 헤더 원복
    st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes", placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등")


# =============================================================================
# === Vehicle Selection and Auto-Basket Logic (이전과 동일) ===
# =============================================================================
# (이 부분 코드는 변경 없음)
prev_vehicle = st.session_state.get('final_selected_vehicle')
prev_prev_vehicle_state = st.session_state.get('prev_final_selected_vehicle')
vehicle_radio_choice = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
manual_vehicle_choice = st.session_state.get('manual_vehicle_select_value')
recommended_vehicle_auto = st.session_state.get('recommended_vehicle_auto')
current_move_type_logic = st.session_state.base_move_type
vehicle_prices_options_logic = data.vehicle_prices.get(current_move_type_logic, {})
available_trucks_logic = sorted(vehicle_prices_options_logic.keys(), key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))
selected_vehicle_logic = None
valid_auto_logic = (recommended_vehicle_auto and "초과" not in recommended_vehicle_auto and recommended_vehicle_auto in available_trucks_logic)
if vehicle_radio_choice == "자동 추천 차량 사용":
    if valid_auto_logic: selected_vehicle_logic = recommended_vehicle_auto
    else: selected_vehicle_logic = None
elif vehicle_radio_choice == "수동으로 차량 선택":
    if manual_vehicle_choice in available_trucks_logic: selected_vehicle_logic = manual_vehicle_choice
    else: selected_vehicle_logic = None
else: selected_vehicle_logic = None
vehicle_changed_flag = False
if selected_vehicle_logic != prev_vehicle:
    if prev_vehicle == prev_prev_vehicle_state:
        st.session_state.final_selected_vehicle = selected_vehicle_logic
        st.session_state.prev_final_selected_vehicle = selected_vehicle_logic
        vehicle_changed_flag = True
        if selected_vehicle_logic in data.default_basket_quantities:
            defaults = data.default_basket_quantities[selected_vehicle_logic]
            basket_section_name = "포장 자재 📦"
            current_move_type_auto = st.session_state.base_move_type
            for item, qty in defaults.items():
                key = f"qty_{current_move_type_auto}_{basket_section_name}_{item}"
                if key in st.session_state: st.session_state[key] = qty
    else:
        st.session_state.final_selected_vehicle = selected_vehicle_logic
        st.session_state.prev_final_selected_vehicle = selected_vehicle_logic
else:
    st.session_state.final_selected_vehicle = selected_vehicle_logic
# =============================================================================


# --- 탭 2: 물품 선택 (UI 원복 없음 - 개선된 상태 유지) ---
# (이전 UI 개선 버전의 Tab 2 코드 유지)
with tab2:
    st.header("📋 이사 품목 선택 및 수량 입력")
    st.caption(f"현재 선택된 기본 이사 유형: **{st.session_state.base_move_type}**")
    st.session_state.total_volume, st.session_state.total_weight = calculations.calculate_total_volume_weight(st.session_state.to_dict(), st.session_state.base_move_type)
    st.session_state.recommended_vehicle_auto, remaining_space = calculations.recommend_vehicle(st.session_state.total_volume, st.session_state.total_weight)
    with st.container(border=True):
        st.subheader("품목별 수량 입력")
        item_category_to_display = data.item_definitions.get(st.session_state.base_move_type, {})
        basket_section_name_check = "포장 자재 📦"
        for section, item_list in item_category_to_display.items():
            if section == "폐기 처리 품목 🗑️": continue
            valid_items_in_section = [item for item in item_list if item in data.items]
            if not valid_items_in_section: continue
            expander_label = f"{section} 품목 선택"
            expanded_default = section == basket_section_name_check
            with st.expander(expander_label, expanded=expanded_default):
                if section == basket_section_name_check:
                    selected_truck_tab2 = st.session_state.get("final_selected_vehicle")
                    if selected_truck_tab2 and selected_truck_tab2 in data.default_basket_quantities:
                        defaults = data.default_basket_quantities[selected_truck_tab2]
                        basket_qty = defaults.get('바구니', 0); med_box_qty = defaults.get('중박스', defaults.get('중자바구니', 0)); book_qty = defaults.get('책바구니', 0)
                        st.info(f"💡 **{selected_truck_tab2}** 추천 기본값: 바구니 {basket_qty}개, 중박스 {med_box_qty}개, 책 {book_qty}개 (현재 값이며, 직접 수정 가능합니다)")
                    else: st.info("💡 비용 탭에서 차량 선택 시 추천 기본 바구니 개수가 여기에 표시됩니다.")
                num_columns = 2; cols = st.columns(num_columns); num_items = len(valid_items_in_section)
                items_per_col = math.ceil(num_items / len(cols)) if num_items > 0 and len(cols) > 0 else 1
                for idx, item in enumerate(valid_items_in_section):
                    col_index = idx // items_per_col if items_per_col > 0 else 0
                    if col_index < len(cols):
                        with cols[col_index]:
                            unit = "칸" if item == "장롱" else "개"; key_prefix = "qty"
                            widget_key = f"{key_prefix}_{st.session_state.base_move_type}_{section}_{item}"
                            if widget_key not in st.session_state: st.session_state[widget_key] = 0
                            try: st.number_input(label=f"{item}", min_value=0, step=1, key=widget_key, help=f"{item}의 수량 ({unit})")
                            except Exception as e: st.error(f"표시 오류: {item}. 상태 초기화."); st.session_state[widget_key] = 0; st.number_input(label=f"{item}", min_value=0, step=1, key=widget_key, help=f"{item}의 수량 ({unit})")
    st.write("---")
    with st.container(border=True):
        st.subheader("📊 현재 선택된 품목 및 예상 물량")
        move_selection_display = {}
        processed_items_summary_move = set()
        original_item_defs_move = data.item_definitions.get(st.session_state.base_move_type, {})
        if isinstance(original_item_defs_move, dict):
            for section_move, item_list_move in original_item_defs_move.items():
                if section_move == "폐기 처리 품목 🗑️": continue
                if isinstance(item_list_move, list):
                    for item_move in item_list_move:
                        if item_move in processed_items_summary_move: continue
                        widget_key_move = f"qty_{st.session_state.base_move_type}_{section_move}_{item_move}"
                        if widget_key_move in st.session_state:
                            qty = 0; raw_qty_m = st.session_state.get(widget_key_move)
                            try: qty = int(raw_qty_m) if raw_qty_m is not None else 0
                            except Exception: qty = 0
                            if qty > 0 and item_move in data.items: unit_move = "칸" if item_move == "장롱" else "개"; move_selection_display[item_move] = (qty, unit_move)
                        processed_items_summary_move.add(item_move)
        if move_selection_display:
            st.markdown("**선택 품목 목록:**")
            cols_disp_m = st.columns(2)
            item_list_disp_m = list(move_selection_display.items())
            items_per_col_disp_m = math.ceil(len(item_list_disp_m)/len(cols_disp_m)) if len(item_list_disp_m)>0 and len(cols_disp_m)>0 else 1
            for i, (item_disp, (qty_disp, unit_disp)) in enumerate(item_list_disp_m):
                col_idx_disp = i // items_per_col_disp_m if items_per_col_disp_m > 0 else 0
                # === 아래 코드 블록 수정 ===
                if col_idx_disp < len(cols_disp_m):
                    with cols_disp_m[col_idx_disp]:
                        # st.write를 with 블록 안으로 들여쓰기
                        st.write(f"- {item_disp}: {qty_disp} {unit_disp}")
            st.write(""); st.markdown("**예상 물량 및 추천 차량:**")
            st.info(f"📊 **총 부피:** {st.session_state.total_volume:.2f} m³ | **총 무게:** {st.session_state.total_weight:.2f} kg")
            recommended_vehicle_display = st.session_state.get('recommended_vehicle_auto'); final_vehicle_tab2_display = st.session_state.get('final_selected_vehicle')
            if recommended_vehicle_display and "초과" not in recommended_vehicle_display:
                rec_text = f"✅ 추천 차량: **{recommended_vehicle_display}** ({remaining_space:.1f}% 여유 공간 예상)"; spec = data.vehicle_specs.get(recommended_vehicle_display);
                if spec: rec_text += f" (최대: {spec['capacity']}m³, {spec['weight_capacity']:,}kg)"; st.success(rec_text)
                if final_vehicle_tab2_display and final_vehicle_tab2_display != recommended_vehicle_display: st.warning(f"⚠️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 수동 선택되어 있습니다.")
                elif not final_vehicle_tab2_display: st.info("💡 비용계산 탭에서 차량을 최종 선택해주세요.")
            elif recommended_vehicle_display and "초과" in recommended_vehicle_display:
                st.error(f"❌ 추천 차량: **{recommended_vehicle_display}**. 선택된 물량이 너무 많습니다. 물량을 줄이거나 더 큰 차량을 수동 선택해야 합니다.")
                if final_vehicle_tab2_display: st.info(f"ℹ️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 수동 선택되어 있습니다.")
            else:
                if st.session_state.total_volume > 0 or st.session_state.total_weight > 0: st.warning("⚠️ 추천 차량: 자동 추천 불가. 비용계산 탭에서 차량을 수동 선택해주세요.")
                else: st.info("ℹ️ 이사할 품목이 없습니다. 품목을 선택해주세요.")
                if final_vehicle_tab2_display: st.info(f"ℹ️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 수동 선택되어 있습니다.")
        else: st.info("ℹ️ 선택된 이사 품목이 없습니다. 위에서 품목을 선택해주세요.");


# --- 탭 3: 견적 및 비용 (UI 원복 없음, 이사 유형 선택만 추가) ---
with tab3:
    st.header("💰 계산 및 옵션 ") # 헤더 원복

    # --- === 이사 유형 선택 위젯 (탭 3) === ---
    st.subheader("🏢 이사 유형 확인/변경")
    try: current_index_tab3 = MOVE_TYPE_OPTIONS.index(st.session_state.base_move_type)
    except ValueError: current_index_tab3 = 0
    st.radio( # 라벨 원복
        "기본 이사 유형:",
        options=MOVE_TYPE_OPTIONS, index=current_index_tab3, horizontal=True,
        key="base_move_type_widget_tab3", on_change=sync_move_type, args=("base_move_type_widget_tab3",)
    )
    st.divider() # 구분선 원복
    # --- ============================== ---

    with st.container(border=True): # 차량 선택 컨테이너 유지
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget: st.radio("차량 선택 방식:", ["자동 추천 차량 사용", "수동으로 차량 선택"], key="vehicle_select_radio", help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.")
        with col_v2_widget:
            # ... (이전 변수 정의 코드 동일) ...
            final_vehicle_widget = st.session_state.get('final_selected_vehicle')
            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
            current_move_type_widget = st.session_state.base_move_type
            vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
            available_trucks_widget = sorted(vehicle_prices_options_widget.keys(), key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))
            valid_auto_widget = (recommended_vehicle_auto_widget and "초과" not in recommended_vehicle_auto_widget and recommended_vehicle_auto_widget in available_trucks_widget)

            # 자동 추천 사용 시
            if use_auto_widget:
                if valid_auto_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_widget}**")
                    # === 아래 라인을 추가하여 spec 변수를 정의합니다 ===
                    spec = data.vehicle_specs.get(final_vehicle_widget)
                    # === ----------------------------------------- ===
                    # 이제 spec 변수가 정의되었으므로 아래 코드가 정상 작동합니다.
                    if spec:
                         st.caption(f"선택차량 최대 용량: {spec['capacity']}m³, {spec['weight_capacity']:,}kg")
                         st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
                else: # 자동 추천 불가 시
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_widget and "초과" in recommended_vehicle_auto_widget: error_msg += f"물량 초과({recommended_vehicle_auto_widget}). 수동 선택 필요."
                    elif not recommended_vehicle_auto_widget and (st.session_state.get('total_volume', 0.0) > 0 or st.session_state.get('total_weight', 0.0) > 0): error_msg += "계산/정보 부족. 수동 선택 필요."
                    else: error_msg += "물품 미선택 또는 정보 부족. 수동 선택 필요."
                    st.error(error_msg)

            # 수동 선택 사용 시 또는 자동 추천 불가 시 드롭다운 표시
            # (이하 수동 선택 로직은 변경 없음)
            if not use_auto_widget or (use_auto_widget and not valid_auto_widget):
                if not available_trucks_widget: st.error("❌ 선택 가능한 차량 정보가 없습니다.")
                else:
                    # ... (수동 선택 드롭다운 및 정보 표시 로직) ...
                    # (수동 선택 부분에서는 spec 정의가 이미 올바르게 되어 있습니다)
                    default_manual_vehicle_widget = recommended_vehicle_auto_widget if valid_auto_widget else (available_trucks_widget[0] if available_trucks_widget else None)
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    try:
                        if current_manual_selection_widget in available_trucks_widget: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        elif default_manual_vehicle_widget in available_trucks_widget: current_index_widget = available_trucks_widget.index(default_manual_vehicle_widget); st.session_state.manual_vehicle_select_value = default_manual_vehicle_widget
                        else: current_index_widget = 0; st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                    except ValueError: current_index_widget = 0; st.session_state.manual_vehicle_select_value = available_trucks_widget[0] if available_trucks_widget else None
                    st.selectbox("차량 직접 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value")
                    manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                    if manual_selected_display:
                        st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                        spec = data.vehicle_specs.get(manual_selected_display) # 수동 선택 시에는 여기서 spec 정의됨
                        if spec:
                            st.caption(f"선택차량 최대 용량: {spec['capacity']}m³, {spec['weight_capacity']:,}kg")
                            st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")

    st.divider() # 구분선 원복
    with st.container(border=True): # 작업 옵션 컨테이너 유지
        st.subheader("🛠️ 작업 조건 및 추가 옵션") # 서브헤더 원복
        sky_from = st.session_state.get('from_method')=="스카이 🏗️"; sky_to = st.session_state.get('to_method')=="스카이 🏗️"
        if sky_from or sky_to: # 스카이 로직 원복
            st.warning("스카이 작업 선택됨 - 시간 입력 필요", icon="🏗️")
            cols_sky = st.columns(2)
            with cols_sky[0]:
                if sky_from: st.number_input("출발 스카이 시간(h)", min_value=1, step=1, key="sky_hours_from")
                else: st.empty()
            with cols_sky[1]:
                if sky_to: st.number_input("도착 스카이 시간(h)", min_value=1, step=1, key="sky_hours_final")
                else: st.empty()
            st.write("")
        # 추가 인원 UI 원복
        col_add1, col_add2 = st.columns(2)
        with col_add1: st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2: st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        st.write("") # 공백 제거 또는 유지
        # 실제 투입 차량 UI 원복
        st.subheader("🚚 실제 투입 차량") # subheader 원복
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.") # 캡션 원복
        st.write("") # 공백 제거 또는 유지
        # 여성 제외 옵션 UI 원복
        base_w=0; remove_opt=False; final_vehicle_for_options = st.session_state.get('final_selected_vehicle'); current_move_type_options = st.session_state.base_move_type
        vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})
        if final_vehicle_for_options and final_vehicle_for_options in vehicle_prices_options_display: base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {}); base_w = base_info.get('housewife', 0);
        if base_w > 0: remove_opt = True
        if remove_opt: st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{data.ADDITIONAL_PERSON_COST * base_w:,}원)", key="remove_base_housewife")
        else:
            if 'remove_base_housewife' in st.session_state: st.session_state.remove_base_housewife = False
        # 폐기물 처리 UI 원복
        col_waste1, col_waste2 = st.columns([1, 2]) # 컬럼 비율 유지 또는 ([1,1]로) 변경
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.") # 라벨/help 원복
        with col_waste2:
            if st.session_state.get('has_waste_check'):
                st.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input", format="%.1f")
                st.caption(f"💡 1톤당 {data.WASTE_DISPOSAL_COST_PER_TON:,}원 추가 비용 발생") # 아이콘 추가 또는 제거
            else: st.empty()
        # 날짜 할증 UI 원복
        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)") # 라벨 원복
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]; date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options)) # 컬럼 개수 원복
        for i, option in enumerate(date_options):
            with cols_date[i]: st.checkbox(option, key=date_keys[i])
    st.divider() # 구분선 원복
    with st.container(border=True): # 비용 조정 컨테이너 유지
        st.subheader("💰 비용 조정 및 계약금") # 서브헤더 원복
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        with col_adj1: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력") # 라벨 원복
        with col_adj2: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d") # 라벨 원복
        with col_adj3: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용") # 라벨 원복
    if vehicle_changed_flag: st.rerun()
    st.divider() # 구분선 원복
    st.header("💵 최종 견적 결과") # 헤더 원복

    total_cost = 0; cost_items = []; personnel_info = {}; excel_data = None
    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle')
    if final_selected_vehicle_calc:
        total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())
        total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
        try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0))
        except (ValueError, TypeError): deposit_amount_num = 0
        remaining_balance_num = total_cost_num - deposit_amount_num
        # --- 비용 요약 (st.metric -> st.subheader 원복) ---
        st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
        st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
        st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
        # ---------------------------------------------
        st.write("") # 공백 제거 또는 유지
        # 비용 상세 내역 (expander 제거, UI 원복)
        st.subheader("📊 비용 상세 내역") # 서브헤더 원복
        error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
        if error_item: st.error(f"비용 계산 오류: {error_item[2]}")
        elif cost_items:
            df_display = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"])
            st.dataframe(df_display.style.format({"금액": "{:,.0f}"}).set_properties(**{'text-align':'right'}, subset=['금액']).set_properties(**{'text-align':'left'}, subset=['항목','비고']), use_container_width=True, hide_index=True) # 스타일 원복
        else: st.info("ℹ️ 계산된 비용 항목이 없습니다.")
        st.write("") # 공백 제거 또는 유지
        special_notes_display = st.session_state.get('special_notes')
        if special_notes_display and special_notes_display.strip(): # 고객 요구사항 위치/스타일 원복
             st.subheader("📝 고객요구사항")
             st.info(special_notes_display)

        # 이사 정보 요약 (st.text() 사용 유지)
        st.subheader("📋 이사 정보 요약")
        summary_generated = False # ... (이하 요약 로직 및 st.text() 출력은 동일하게 유지) ...
        try:
            excel_data = pdf_generator.generate_excel(st.session_state.to_dict(), cost_items, total_cost, personnel_info)
            if excel_data:
                excel_buffer = io.BytesIO(excel_data); xls = pd.ExcelFile(excel_buffer)
                df_info = xls.parse("견적 정보", header=None); df_cost = xls.parse("비용 내역 및 요약", header=None)
                info_dict = {}
                if not df_info.empty and len(df_info.columns) > 1: info_dict = dict(zip(df_info[0].astype(str), df_info[1].astype(str)))
                def format_money_kor(amount):
                    try: amount_str = str(amount).replace(",", "").split()[0]; amount_float = float(amount_str); amount_int = int(amount_float)
                    except: return "금액오류"
                    if amount_int >= 10000: return f"{amount_int // 10000}만원"
                    elif amount_int != 0: return f"{amount_int}원"
                    else: return "0원"
                def format_address(address_string):
                    if not isinstance(address_string, str) or not address_string.strip() or address_string.lower() == 'nan': return ""
                    return address_string.strip()
                def get_cost_value_abbr(keyword, abbr, cost_df):
                    if cost_df.empty or len(cost_df.columns) < 2: return f"{abbr} 정보 없음"
                    for i in range(len(cost_df)):
                        cell_value = cost_df.iloc[i, 0]
                        if pd.notna(cell_value) and str(cell_value).strip().startswith(keyword): formatted_amount = format_money_kor(cost_df.iloc[i, 1]); return f"{abbr} {formatted_amount}"
                    return f"{abbr} 정보 없음"
                def format_work_method(method_str):
                    method_str = str(method_str).strip()
                    if "사다리차" in method_str: return "사"
                    elif "승강기" in method_str: return "승"
                    elif "계단" in method_str: return "계"
                    elif "스카이" in method_str: return "스카이"
                    else: return "?"
                from_address_full = format_address(info_dict.get("출발지", ""))
                to_address_full = format_address(info_dict.get("도착지", ""))
                phone = info_dict.get("고객 연락처", "")
                work_from_raw = info_dict.get("출발 작업", ""); work_to_raw = info_dict.get("도착 작업", "")
                vehicle_type = final_selected_vehicle_calc if final_selected_vehicle_calc else info_dict.get("선택 차량", "")
                special_note = format_address(info_dict.get("고객요구사항", ""))
                p_info_calc = personnel_info; final_men_calc = p_info_calc.get('final_men', 0); final_women_calc = p_info_calc.get('final_women', 0)
                personnel_formatted = f"{final_men_calc}+{final_women_calc}" if final_women_calc > 0 else f"{final_men_calc}"
                basket_section_name = "포장 자재 📦"; current_move_type_summary = st.session_state.base_move_type
                key_basket = f"qty_{current_move_type_summary}_{basket_section_name}_바구니"; key_med_box = f"qty_{current_move_type_summary}_{basket_section_name}_중박스"; key_book_basket = f"qty_{current_move_type_summary}_{basket_section_name}_책바구니"
                try: qty_basket = int(st.session_state.get(key_basket, 0))
                except: qty_basket = 0
                try: qty_medium_box = int(st.session_state.get(key_med_box, 0))
                except: qty_medium_box = 0
                try: qty_book_basket = int(st.session_state.get(key_book_basket, 0))
                except: qty_book_basket = 0
                basket_formatted = f"바{qty_basket} 중{qty_medium_box} 책{qty_book_basket}" if (qty_basket + qty_medium_box + qty_book_basket > 0) else ""
                contract_fee_str = get_cost_value_abbr("계약금 (-)", "계", df_cost); remaining_fee_str = get_cost_value_abbr("잔금 (VAT 별도)", "잔", df_cost)
                work_from_abbr = format_work_method(work_from_raw); work_to_abbr = format_work_method(work_to_raw); work_method_formatted = f"출{work_from_abbr}도{work_to_abbr}"
                st.text(f"{from_address_full} - {to_address_full} {vehicle_type}"); st.text("")
                if phone and phone != '-': st.text(f"{phone}"); st.text("")
                st.text(f"{vehicle_type} | {personnel_formatted}"); st.text("")
                if basket_formatted: st.text(basket_formatted); st.text("")
                st.text(work_method_formatted); st.text("")
                st.text(f"{contract_fee_str} / {remaining_fee_str}"); st.text("")
                if special_note and special_note.strip() and special_note.strip().lower() != 'nan' and special_note != '-': st.text(f"{special_note.strip()}")
                summary_generated = True
            else: st.warning("⚠️ 요약 정보 생성 실패 (엑셀 데이터 오류)")
        except Exception as e: st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}"); traceback.print_exc()
        if not summary_generated and final_selected_vehicle_calc: st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")
        st.divider() # 구분선 원복

        # 다운로드 섹션 UI 원복 (버튼 3개 버전, 마지막 버튼은 숨김 처리됨)
        st.subheader("📄 견적서 파일 다운로드")
        has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False
        can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error
        cols_dl = st.columns(3) # 3열 레이아웃 유지

        with cols_dl[0]: # Final 견적서
             st.markdown("**① Final 견적서 (Excel)**")
             if st.button("📄 생성: Final 견적서"):
                filled_excel_data = excel_filler.fill_final_excel_template(st.session_state.to_dict(), cost_items, total_cost, personnel_info)
                if filled_excel_data: st.session_state['final_excel_data'] = filled_excel_data; st.success("✅ 생성 완료!")
                else:
                    if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']
                    st.error("❌ 생성 실패.")
             if st.session_state.get('final_excel_data'):
                 ph_part_final = utils.extract_phone_number_part(st.session_state.customer_phone, length=4, default="0000"); now_final_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d') if pytz else datetime.now().strftime('%y%m%d')
                 final_excel_fname = f"{ph_part_final}_{now_final_str}_Final견적서.xlsx"
                 st.download_button(label="📥 다운로드 (Excel)", data=st.session_state['final_excel_data'], file_name=final_excel_fname, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='final_excel_download_button')
             else: st.caption("생성 버튼을 눌러주세요.")

        with cols_dl[1]: # PDF 견적서
            st.markdown("**② 고객용 견적서 (PDF)**")
            if can_gen_pdf:
                if st.button("📄 생성: PDF 견적서"):
                    latest_total_cost_pdf, latest_cost_items_pdf, latest_personnel_info_pdf = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                    pdf_data_bytes = pdf_generator.generate_pdf(st.session_state.to_dict(), latest_cost_items_pdf, latest_total_cost_pdf, latest_personnel_info_pdf)
                    st.session_state['pdf_data_customer'] = pdf_data_bytes
                    if pdf_data_bytes: st.success("✅ 생성 완료!")
                    else: st.error("❌ 생성 실패.")
                if st.session_state.get('pdf_data_customer'):
                    ph_part_pdf = utils.extract_phone_number_part(st.session_state.customer_phone, length=4, default="0000"); now_pdf_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M') if pytz else datetime.now().strftime('%y%m%d_%H%M')
                    fname_pdf = f"{ph_part_pdf}_{now_pdf_str}_이삿날견적서.pdf"
                    st.download_button(label="📥 다운로드 (PDF)", data=st.session_state['pdf_data_customer'], file_name=fname_pdf, mime='application/pdf', key='pdf_download_button')
                elif not st.session_state.get('pdf_data_customer'): st.caption("생성 버튼을 눌러주세요.")
            else: st.caption("PDF 생성 불가 (차량 미선택 또는 비용 오류)")

        with cols_dl[2]: # 종합 견적서 버튼 숨김 유지
            st.empty()

    else: # 차량 미선택 시 안내 원복
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시 및 다운로드는 차량 선택 후 가능합니다.")
        # st.info 제거 또는 유지 (선택사항)
