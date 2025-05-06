# state_manager.py (Removed file_uploader_key_counter)
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

# --- Constants ---
MOVE_TYPE_OPTIONS = list(data.item_definitions.keys()) if hasattr(data, 'item_definitions') else ["가정 이사 🏠", "사무실 이사 🏢"]
STATE_KEYS_TO_SAVE = [
    # ... (all previous keys remain the same, excluding the counter) ...
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
    "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t",
    "gdrive_image_files"
]


# --- Session State Initialization ---
def initialize_session_state(update_basket_callback):
    """세션 상태 변수들 초기화"""
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()

    defaults = {
        # ... (all previous defaults remain the same) ...
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
        'final_excel_data': None,
        "deposit_amount": 0, "adjustment_amount": 0, "regional_ladder_surcharge": 0,
        "remove_base_housewife": False, "prev_final_selected_vehicle": None,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "gdrive_search_term": "", "gdrive_search_results": [],
        "gdrive_file_options_map": {}, "gdrive_selected_filename": None,
        "gdrive_selected_file_id": None,
        "base_move_type_widget_tab1": MOVE_TYPE_OPTIONS[0],
        "base_move_type_widget_tab3": MOVE_TYPE_OPTIONS[0],
        "uploaded_images": None, # Default for file uploader
        "gdrive_image_files": [],
        "loaded_images": {},
        # REMOVED: "file_uploader_key_counter": 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # (Rest of initialization remains the same)
    if 'base_move_type' not in st.session_state:
         st.session_state.base_move_type = defaults['base_move_type']
    if st.session_state.base_move_type_widget_tab1 != st.session_state.base_move_type:
        st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
    if st.session_state.base_move_type_widget_tab3 != st.session_state.base_move_type:
        st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount"]
    for k in int_keys + float_keys:
        default_val_k = defaults.get(k)
        if k not in st.session_state: st.session_state[k] = default_val_k
        try:
            val = st.session_state.get(k)
            target_type = int if k in int_keys else float
            if val is None or (isinstance(val, str) and val.strip() == ''):
                 st.session_state[k] = default_val_k; continue
            converted_val = target_type(val)
            if k in int_keys:
                if k in allow_negative_keys: st.session_state[k] = converted_val
                else: st.session_state[k] = max(0, converted_val)
            else: st.session_state[k] = max(0.0, converted_val)
        except (ValueError, TypeError): st.session_state[k] = default_val_k
        except KeyError: st.session_state[k] = 0 if k in int_keys else 0.0
    global STATE_KEYS_TO_SAVE
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
    else: print("Warning: data.item_definitions not found during state initialization.")
    STATE_KEYS_TO_SAVE = list(set(STATE_KEYS_TO_SAVE + item_keys_to_save))
    if 'prev_final_selected_vehicle' not in st.session_state:
        st.session_state['prev_final_selected_vehicle'] = st.session_state.get('final_selected_vehicle')


# --- State Save/Load Helpers ---
# (prepare_state_for_save remains the same - already excludes counter)
def prepare_state_for_save():
    state_to_save = {}
    keys_to_exclude = {
        'base_move_type_widget_tab1', 'base_move_type_widget_tab3',
        'gdrive_selected_filename_widget',
        'uploaded_images', 'loaded_images', 'pdf_data_customer',
        'final_excel_data', 'gdrive_search_results', 'gdrive_file_options_map',
        # 'file_uploader_key_counter' # Already removed
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


# (load_state_from_data remains the same - no reset needed here)
def load_state_from_data(loaded_data, update_basket_callback):
    if not isinstance(loaded_data, dict):
        st.error("잘못된 형식의 파일입니다 (딕셔너리가 아님).")
        return False
    # (Defaults dictionary remains the same)
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()
    defaults_for_recovery = {
        "base_move_type": MOVE_TYPE_OPTIONS[0], "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE,
        "apply_long_distance": False, "customer_name": "", "customer_phone": "", "from_location": "",
        "to_location": "", "moving_date": default_date, "from_floor": "", "from_method": data.METHOD_OPTIONS[0],
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0], "special_notes": "", "storage_duration": 1,
        "long_distance_selector": data.long_distance_options[0], "vehicle_select_radio": "자동 추천 차량 사용",
        "manual_vehicle_select_value": None, "final_selected_vehicle": None, "prev_final_selected_vehicle": None,
        "sky_hours_from": 1, "sky_hours_final": 1, "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False, "deposit_amount": 0, "adjustment_amount": 0,
        "regional_ladder_surcharge": 0, "remove_base_housewife": False,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "gdrive_image_files": []
    }
    dynamic_keys = [key for key in STATE_KEYS_TO_SAVE if key.startswith("qty_")]
    for key in dynamic_keys:
        if key not in defaults_for_recovery: defaults_for_recovery[key] = 0

    st.session_state.loaded_images = {} # Clear previous display data

    # (Load loop remains the same)
    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women", "deposit_amount", "adjustment_amount", "regional_ladder_surcharge", "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount"]
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check", "remove_base_housewife", "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget", "date_opt_3_widget", "date_opt_4_widget"]
    list_keys = ["gdrive_image_files"]
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
                elif key.startswith("qty_"):
                     converted_val = int(value) if value is not None else 0; target_value = max(0, converted_val)
                elif key in int_keys:
                    converted_val = int(value) if value is not None else 0
                    if key in allow_negative_keys: target_value = converted_val
                    else: target_value = max(0, converted_val)
                elif key in float_keys:
                    converted_val = float(value) if value is not None else 0.0; target_value = max(0.0, converted_val)
                elif key in bool_keys:
                    if isinstance(value, str): target_value = value.lower() in ['true', 'yes', '1', 'on']
                    else: target_value = bool(value)
                elif key in list_keys:
                     target_value = list(value) if isinstance(value, list) else defaults_for_recovery.get(key, [])
                else: target_value = value
                st.session_state[key] = target_value
                load_success_count += 1
            except (ValueError, TypeError, KeyError) as e:
                load_error_count += 1; default_val = defaults_for_recovery.get(key)
                st.session_state[key] = default_val
                print(f"Warning: Error loading key '{key}' (Value: {original_value}, Type: {type(original_value)}). Error: {e}. Used default: {default_val}")
    if load_error_count > 0: st.warning(f"일부 항목({load_error_count}개) 로딩 중 오류가 발생하여 기본값으로 설정되었거나 무시되었습니다.")
    st.session_state.gdrive_search_results = []; st.session_state.gdrive_file_options_map = {}
    st.session_state.gdrive_selected_filename = None; st.session_state.gdrive_selected_file_id = None
    if 'base_move_type' in st.session_state:
        loaded_move_type = st.session_state.base_move_type
        st.session_state.base_move_type_widget_tab1 = loaded_move_type
        st.session_state.base_move_type_widget_tab3 = loaded_move_type
    update_basket_callback()
    return True # Indicate load attempt finished
