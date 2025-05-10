# state_manager.py (Adjusted for prefixed keys)
import streamlit as st
from datetime import datetime, date
import pytz
import json

# Import necessary custom modules
try:
    import data
    import utils
except ImportError as e:
    st.error(f"State Manager: 필수 모듈 로딩 실패 - {e}")
    st.stop()
except Exception as e:
    st.error(f"State Manager: 모듈 로딩 중 오류 - {e}")
    st.stop()

# --- Constants ---
try:
    MOVE_TYPE_OPTIONS = list(data.item_definitions.keys()) if hasattr(data, 'item_definitions') and data.item_definitions else ["가정 이사 🏠", "사무실 이사 🏢"]
except Exception as e:
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    st.warning(f"data.py에서 이사 유형 로딩 중 오류 발생: {e}. 기본값을 사용합니다.")

# --- STATE_KEYS_TO_SAVE 리스트 수정 ---
# 기존 키 대신 tab3_ 접두사 붙은 키 사용
# add_men, add_women 등 다른 키들도 필요시 'tab3_' 접두사 고려 (현재는 그대로 둠)
STATE_KEYS_TO_SAVE = [
    "base_move_type", "is_storage_move", "storage_type", "apply_long_distance",
    "customer_name", "customer_phone", "customer_email",
    "from_location", "to_location", "moving_date",
    "from_floor", "from_method", "to_floor", "to_method", "special_notes",
    "storage_duration", "long_distance_selector", "vehicle_select_radio",
    "manual_vehicle_select_value", "final_selected_vehicle", "sky_hours_from",
    "sky_hours_final",
    "add_men", "add_women", # key="add_men", key="add_women" (Tab3)
    "has_waste_check", "waste_tons_input", # key="has_waste_check", key="waste_tons_input" (Tab3)
    # "date_opt_0_widget" 등 원본 키 유지 (Tab3 에서 접두사 붙임)
    "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
    "date_opt_3_widget", "date_opt_4_widget",
    # --- 접두사 붙은 키 저장 ---
    "tab3_deposit_amount",
    "tab3_adjustment_amount",
    "tab3_regional_ladder_surcharge",
    # Tab3의 다른 위젯들도 접두사를 붙였다면 여기에 추가 필요
    "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
    "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
    "remove_base_housewife", # key="remove_base_housewife" (Tab3)
    "prev_final_selected_vehicle",
    "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t", # key="dispatched_..." (Tab3)
    # Item keys (qty_...) are added dynamically below
]

# --- Session State Initialization ---
def initialize_session_state(update_basket_callback):
    """Initializes session state variables."""
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()

    # --- defaults 딕셔너리 수정 ---
    defaults = {
        "base_move_type": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "is_storage_move": False,
        "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "",
        "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date,
        "from_floor": "",
        "from_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "to_floor": "",
        "to_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1,
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, 'long_distance_options') and data.long_distance_options else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용", "manual_vehicle_select_value": None,
        "final_selected_vehicle": None, "sky_hours_from": 1, "sky_hours_final": 1,
        "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
         # date_opt 원본 키는 일단 유지 (다른 곳 참조 가능성)
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False,
         # Tab 3용 새 키 기본값
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "total_volume": 0.0, "total_weight": 0.0, "recommended_vehicle_auto": None,
        'pdf_data_customer': None, 'final_excel_data': None,
        "tab3_deposit_amount": 0,
        "tab3_adjustment_amount": 0,
        "tab3_regional_ladder_surcharge": 0,
        "remove_base_housewife": False, "prev_final_selected_vehicle": None,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "gdrive_search_term": "", "gdrive_search_results": [],
        "gdrive_file_options_map": {}, "gdrive_selected_filename": None,
        "gdrive_selected_file_id": None,
        "base_move_type_widget_tab1": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "base_move_type_widget_tab3": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
    }
    # Initialize state
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

    # Sync widget states
    if 'base_move_type' not in st.session_state: st.session_state.base_move_type = defaults['base_move_type']
    if st.session_state.base_move_type_widget_tab1 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
    if st.session_state.base_move_type_widget_tab3 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type

    # --- Type conversion 수정 ---
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "tab3_deposit_amount", "tab3_adjustment_amount", "tab3_regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["tab3_adjustment_amount"] # 조정 금액은 음수 허용
    # bool 키는 Tab3에서 접두사 붙은 키를 사용하므로 해당 키들도 확인 필요
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife",
                 "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget", "date_opt_3_widget", "date_opt_4_widget",
                 "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
                 "tab3_date_opt_3_widget", "tab3_date_opt_4_widget"] # 새 키 포함

    for k in int_keys + float_keys + bool_keys: # bool_keys도 포함
        default_val_k = defaults.get(k) # Get default from potentially larger defaults dict
        if k not in st.session_state: st.session_state[k] = default_val_k

        # 타입 변환 로직 (bool 추가)
        try:
            val = st.session_state.get(k)
            if val is None: st.session_state[k] = default_val_k; continue # None이면 기본값

            if k in bool_keys:
                 if isinstance(val, str): st.session_state[k] = val.lower() in ['true', 'yes', '1', 'on']
                 else: st.session_state[k] = bool(val)
            elif k in int_keys:
                 if isinstance(val, str) and val.strip() == '': st.session_state[k] = default_val_k; continue
                 converted_val = int(val)
                 if k in allow_negative_keys: st.session_state[k] = converted_val
                 else: st.session_state[k] = max(0, converted_val)
            elif k in float_keys:
                 if isinstance(val, str) and val.strip() == '': st.session_state[k] = default_val_k; continue
                 converted_val = float(val)
                 st.session_state[k] = max(0.0, converted_val)
        except (ValueError, TypeError): st.session_state[k] = default_val_k
        except KeyError: # Should not happen with .get() but as safety
             if k in int_keys: st.session_state[k] = 0
             elif k in float_keys: st.session_state[k] = 0.0
             elif k in bool_keys: st.session_state[k] = False


    # Dynamically initialize item keys (기존과 동일)
    global STATE_KEYS_TO_SAVE; processed_init_keys = set(); item_keys_to_save = []
    if hasattr(data, 'item_definitions') and data.item_definitions:
        for move_type, sections in data.item_definitions.items():
            if isinstance(sections, dict):
                for section, item_list in sections.items():
                    if section == "폐기 처리 품목 🗑️": continue
                    if isinstance(item_list, list):
                        for item in item_list:
                            if hasattr(data, 'items') and item in data.items:
                                key = f"qty_{move_type}_{section}_{item}"; item_keys_to_save.append(key)
                                if key not in st.session_state and key not in processed_init_keys: st.session_state[key] = 0
                                processed_init_keys.add(key)
    else: print("Warning: data.item_definitions not found or empty during state initialization.")
    STATE_KEYS_TO_SAVE = list(set(STATE_KEYS_TO_SAVE + item_keys_to_save))
    if 'prev_final_selected_vehicle' not in st.session_state: st.session_state['prev_final_selected_vehicle'] = st.session_state.get('final_selected_vehicle')


# --- State Save/Load Helpers ---
def prepare_state_for_save():
    """Prepares the current session state for saving (e.g., to JSON)."""
    state_to_save = {}
    keys_to_exclude = {
        'base_move_type_widget_tab1', 'base_move_type_widget_tab3',
        'gdrive_selected_filename_widget',
        'pdf_data_customer', 'final_excel_data',
        'gdrive_search_results', 'gdrive_file_options_map',
        # 원본 date_opt 키 제외 (저장 안 함) - 새 키는 저장됨
        "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
        "date_opt_3_widget", "date_opt_4_widget",
    }
    actual_keys_to_save = list(set(STATE_KEYS_TO_SAVE) - keys_to_exclude)

    for key in actual_keys_to_save:
        if key in st.session_state:
            value = st.session_state[key]
            if isinstance(value, date):
                try: state_to_save[key] = value.isoformat()
                except Exception: print(f"Warning: Could not serialize date key '{key}' for saving.")
            elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                 state_to_save[key] = value
            else:
                 try: state_to_save[key] = str(value)
                 except Exception: print(f"Warning: Skipping non-serializable key '{key}' of type {type(value)} during save.")
    return state_to_save


def load_state_from_data(loaded_data, update_basket_callback):
    """Loads state from a dictionary (e.g., loaded from JSON)."""
    if not isinstance(loaded_data, dict):
        st.error("잘못된 형식의 파일입니다 (딕셔너리가 아님).")
        return False

    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()
    current_move_type_options = globals().get('MOVE_TYPE_OPTIONS')
    # --- defaults_for_recovery 수정 ---
    defaults_for_recovery = {
        "base_move_type": current_move_type_options[0] if current_move_type_options else "가정 이사 🏠",
        "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "", "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date, "from_floor": "",
        "from_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1,
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, 'long_distance_options') and data.long_distance_options else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용", "manual_vehicle_select_value": None,
        "final_selected_vehicle": None, "prev_final_selected_vehicle": None,
        "sky_hours_from": 1, "sky_hours_final": 1, "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        # 원본 date_opt 키는 여기서 기본값 설정 불필요 (저장 안 했으므로)
        # Tab 3 용 새 키 기본값
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "tab3_deposit_amount": 0,
        "tab3_adjustment_amount": 0,
        "tab3_regional_ladder_surcharge": 0,
        "remove_base_housewife": False,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
    }
    dynamic_keys = [key for key in STATE_KEYS_TO_SAVE if key.startswith("qty_")]
    for key in dynamic_keys:
        if key not in defaults_for_recovery: defaults_for_recovery[key] = 0

    # --- Load loop 수정 ---
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "tab3_deposit_amount", "tab3_adjustment_amount", "tab3_regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["tab3_adjustment_amount"]
    # bool 키에 새 키 포함
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife",
                 "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
                 "tab3_date_opt_3_widget", "tab3_date_opt_4_widget"]
    list_keys = []
    load_success_count = 0; load_error_count = 0
    all_expected_keys = list(set(STATE_KEYS_TO_SAVE)) # 저장된 키 목록 사용

    for key in all_expected_keys:
        if key in loaded_data: # 로드된 데이터에 키가 있으면
            value = loaded_data[key]; original_value = value
            try:
                target_value = None
                # 타입 변환 로직 (bool 키 타입 변환 추가)
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
                elif key in bool_keys: # bool 키 처리
                    if isinstance(value, str): target_value = value.lower() in ['true', 'yes', '1', 'on']
                    else: target_value = bool(value)
                elif key in list_keys: target_value = list(value) if isinstance(value, list) else defaults_for_recovery.get(key, [])
                else: target_value = value # 나머지 타입은 그대로

                st.session_state[key] = target_value; load_success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                load_error_count += 1; default_val = defaults_for_recovery.get(key); st.session_state[key] = default_val
                print(f"Warning: Error loading key '{key}' (Value: {original_value}, Type: {type(original_value)}). Error: {e}. Used default: {default_val}")
        # else: 키가 로드된 데이터에 없으면 기본값 유지 (초기화 값 사용)

    if load_error_count > 0: st.warning(f"일부 항목({load_error_count}개) 로딩 중 오류가 발생하여 기본값으로 설정되었거나 무시되었습니다.")

    # Reset GDrive search state
    st.session_state.gdrive_search_results = []; st.session_state.gdrive_file_options_map = {}
    st.session_state.gdrive_selected_filename = None; st.session_state.gdrive_selected_file_id = None

    # Sync tab widget states
    if 'base_move_type' in st.session_state:
        loaded_move_type = st.session_state.base_move_type
        valid_move_type_options_load = globals().get('MOVE_TYPE_OPTIONS')
        if not isinstance(loaded_move_type, str) or (valid_move_type_options_load and loaded_move_type not in valid_move_type_options_load):
             loaded_move_type = valid_move_type_options_load[0] if valid_move_type_options_load else "가정 이사 🏠"
             st.session_state.base_move_type = loaded_move_type
        st.session_state.base_move_type_widget_tab1 = loaded_move_type
        st.session_state.base_move_type_widget_tab3 = loaded_move_type

    update_basket_callback()

    return True