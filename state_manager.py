# state_manager.py
# state_manager.py (도착 예정일, 경유지, 보관 전기사용 옵션 추가)
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
# storage_use_electricity 추가
STATE_KEYS_TO_SAVE = [
    "base_move_type", "is_storage_move", "storage_type", "apply_long_distance",
    "customer_name", "customer_phone", "customer_email",
    "from_location", "to_location", "moving_date", "arrival_date",
    "from_floor", "from_method", "to_floor", "to_method", "special_notes",
    "storage_duration", "storage_use_electricity", # 전기사용 추가
    "long_distance_selector", "vehicle_select_radio",
    "manual_vehicle_select_value", "final_selected_vehicle", "sky_hours_from",
    "sky_hours_final",
    "add_men", "add_women",
    "has_waste_check", "waste_tons_input",
    "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
    "date_opt_3_widget", "date_opt_4_widget",
    # UI key 와 다른 접두사 붙은 키 (저장/로드용)
    "tab3_deposit_amount",
    "tab3_adjustment_amount",
    "tab3_regional_ladder_surcharge",
    "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
    "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
    "remove_base_housewife",
    "prev_final_selected_vehicle",
    "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t",
    # 경유지 관련 키
    "has_via_point", "via_point_location", "via_point_method", "via_point_surcharge",
    # Item keys (qty_...) are added dynamically below
]

# --- Session State Initialization ---
def initialize_session_state(update_basket_callback=None):
    """Initializes session state variables."""
    # print("DEBUG SM: initialize_session_state CALLED")
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()

    # --- defaults 딕셔너리 수정 ---
    # storage_use_electricity 기본값 추가
    defaults = {
        "base_move_type": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "is_storage_move": False,
        "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "",
        "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date,
        "arrival_date": default_date, # 도착일 기본값
        "from_floor": "",
        "from_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "to_floor": "",
        "to_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1,
        "storage_use_electricity": False, # 전기사용 기본값 False
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, 'long_distance_options') and data.long_distance_options else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용", 
        "manual_vehicle_select_value": None, # 초기에는 수동 선택 차량 없음
        "final_selected_vehicle": None, # 초기에는 최종 선택 차량 없음
        "recommended_vehicle_auto": None, # 초기에는 자동 추천 차량 없음
        "sky_hours_from": 1, "sky_hours_final": 1,
        "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False,
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "total_volume": 0.0, "total_weight": 0.0, 
        'pdf_data_customer': None, 'final_excel_data': None,
        "deposit_amount": 0,
        "adjustment_amount": 0,
        "regional_ladder_surcharge": 0,
        "via_point_surcharge": 0,
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
        "has_via_point": False,
        "via_point_location": "",
        "via_point_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "_app_initialized": True # Mark as initialized
    }
    # Initialize state
    for key, value in defaults.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            # print(f"DEBUG SM: Initialized st.session_state.{key} = {value}")

    # Sync widget states
    if st.session_state.base_move_type_widget_tab1 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
    if st.session_state.base_move_type_widget_tab3 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type

    # --- Type conversion 수정 ---
    # storage_duration도 int_keys에 포함
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
                "via_point_surcharge",
                "tab3_deposit_amount", "tab3_adjustment_amount", "tab3_regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount", "tab3_adjustment_amount"]
    # bool 키에 storage_use_electricity, has_via_point 추가
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife",
                 "storage_use_electricity", # 전기사용 추가
                 "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget", "date_opt_3_widget", "date_opt_4_widget",
                 "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
                 "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
                 "has_via_point"]

    for k in int_keys + float_keys + bool_keys:
        default_val_k = defaults.get(k)
        if k not in st.session_state: st.session_state[k] = default_val_k

        # 타입 변환 로직
        try:
            val = st.session_state.get(k)
            if val is None: st.session_state[k] = default_val_k; continue

            if k in bool_keys:
                 if isinstance(val, str): st.session_state[k] = val.lower() in ['true', 'yes', '1', 'on']
                 else: st.session_state[k] = bool(val)
            elif k in int_keys:
                 if isinstance(val, str) and val.strip() == '': st.session_state[k] = default_val_k; continue
                 converted_val = int(val)
                 if k in allow_negative_keys: st.session_state[k] = converted_val
                 else: st.session_state[k] = max(0, converted_val)
                 if k == 'storage_duration': st.session_state[k] = max(1, st.session_state[k])
            elif k in float_keys:
                 if isinstance(val, str) and val.strip() == '': st.session_state[k] = default_val_k; continue
                 converted_val = float(val)
                 st.session_state[k] = max(0.0, converted_val)
        except (ValueError, TypeError): st.session_state[k] = default_val_k
        except KeyError:
             if k in int_keys: st.session_state[k] = defaults.get(k, 0)
             elif k in float_keys: st.session_state[k] = defaults.get(k, 0.0)
             elif k in bool_keys: st.session_state[k] = defaults.get(k, False)


    # Dynamically initialize item keys
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
                                if key not in st.session_state and key not in processed_init_keys: 
                                    st.session_state[key] = 0
                                    # print(f"DEBUG SM: Initialized item key {key} = 0")
                                processed_init_keys.add(key)
    # else: print("Warning: data.item_definitions not found or empty during state initialization.")
    STATE_KEYS_TO_SAVE = list(set(STATE_KEYS_TO_SAVE + item_keys_to_save))
    if 'prev_final_selected_vehicle' not in st.session_state: st.session_state['prev_final_selected_vehicle'] = st.session_state.get('final_selected_vehicle')

    # After all other initializations, call the basket update callback if provided
    # This ensures that initial basket quantities are set based on the initial (likely "1톤") vehicle state.
    if callable(update_basket_callback):
        # print("DEBUG SM: Calling update_basket_callback during initialization.")
        update_basket_callback()
    # else:
        # print("DEBUG SM: update_basket_callback not callable or not provided during init.")
    # print("DEBUG SM: initialize_session_state FINISHED")

# --- State Save/Load Helpers ---
def prepare_state_for_save():
    """Prepares the current session state for saving (e.g., to JSON)."""
    state_to_save = {}
    keys_to_exclude = {
        '_app_initialized', # Do not save this internal flag
        'base_move_type_widget_tab1', 'base_move_type_widget_tab3',
        'gdrive_selected_filename_widget',
        'pdf_data_customer', 'final_excel_data',
        'gdrive_search_results', 'gdrive_file_options_map',
        # UI용 키들은 STATE_KEYS_TO_SAVE 에서 정의된 저장용 키로 대체됨
        "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
        "via_point_surcharge",
        # date_opt_widget 키는 저장용으로 포함되어 있음 (STATE_KEYS_TO_SAVE 확인)
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
    # storage_use_electricity 기본값 포함
    defaults_for_recovery = {
        "base_move_type": current_move_type_options[0] if current_move_type_options else "가정 이사 🏠",
        "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "", "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date,
        "arrival_date": default_date, # 도착일 기본값
        "from_floor": "",
        "from_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1,
        "storage_use_electricity": False, # 전기사용 기본값
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, 'long_distance_options') and data.long_distance_options else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용", "manual_vehicle_select_value": None,
        "final_selected_vehicle": None, "prev_final_selected_vehicle": None,
        "sky_hours_from": 1, "sky_hours_final": 1, "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        # Tab 3용 접두사 붙은 키 기본값
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "tab3_deposit_amount": 0,
        "tab3_adjustment_amount": 0,
        "tab3_regional_ladder_surcharge": 0,
        "remove_base_housewife": False,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        # 경유지 관련 기본값
        "has_via_point": False,
        "via_point_location": "",
        "via_point_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "via_point_surcharge": 0, # 저장 키 기준 (STATE_KEYS_TO_SAVE)
    }
    dynamic_keys = [key for key in STATE_KEYS_TO_SAVE if key.startswith("qty_")]
    for key in dynamic_keys:
        if key not in defaults_for_recovery: defaults_for_recovery[key] = 0

    # --- Load loop 수정 ---
    # storage_duration, storage_use_electricity 포함
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "tab3_deposit_amount", "tab3_adjustment_amount", "tab3_regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t",
                "via_point_surcharge"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["tab3_adjustment_amount"]
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife",
                 "storage_use_electricity", # 전기사용 추가
                 "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
                 "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
                 "has_via_point"]
    list_keys = []
    load_success_count = 0; load_error_count = 0
    all_expected_keys = list(set(STATE_KEYS_TO_SAVE))

    for key in all_expected_keys:
        if key in loaded_data:
            value = loaded_data[key]; original_value = value
            try:
                target_value = None
                if key in ['moving_date', 'arrival_date']:
                    if isinstance(value, str): target_value = datetime.fromisoformat(value).date()
                    elif isinstance(value, date): target_value = value
                    else: raise ValueError("Invalid date format")
                elif key.startswith("qty_"): converted_val = int(value) if value is not None else 0; target_value = max(0, converted_val)
                elif key in int_keys:
                    converted_val = int(value) if value is not None else 0
                    if key in allow_negative_keys: target_value = converted_val
                    else: target_value = max(0, converted_val)
                    if key == 'storage_duration': target_value = max(1, target_value) # 로드 시에도 최소 1일
                elif key in float_keys: converted_val = float(value) if value is not None else 0.0; target_value = max(0.0, converted_val)
                elif key in bool_keys:
                    if isinstance(value, str): target_value = value.lower() in ['true', 'yes', '1', 'on']
                    else: target_value = bool(value)
                elif key in list_keys: target_value = list(value) if value is not None else [] 
                else: target_value = value # For strings and other types
                st.session_state[key] = target_value
                load_success_count += 1
            except (ValueError, TypeError) as e:
                st.warning(f"키 '{key}' 로드 중 오류 (값: {original_value}, 타입: {type(original_value)}): {e}. 기본값으로 대체합니다.")
                st.session_state[key] = defaults_for_recovery.get(key)
                load_error_count += 1
        else: # Key not in loaded_data, set to default
            st.session_state[key] = defaults_for_recovery.get(key)

    # Sync base_move_type with widgets after loading
    if 'base_move_type' in st.session_state:
        st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
        st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type
    
    # After loading all state, call the basket update callback
    if callable(update_basket_callback):
        # print("DEBUG SM: Calling update_basket_callback after loading state.")
        update_basket_callback()
    # else:
        # print("DEBUG SM: update_basket_callback not callable or not provided after loading state.")

    if load_error_count > 0:
        st.warning(f"{load_error_count}개의 항목을 로드하는 중 오류가 발생하여 기본값으로 대체되었습니다.")
    st.success(f"{load_success_count}개의 항목을 성공적으로 로드했습니다.")
    return True

