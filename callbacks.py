# callbacks.py
import streamlit as st

# Import necessary custom modules
try:
    import data
    from state_manager import MOVE_TYPE_OPTIONS
except ImportError:
    st.warning("state_manager로부터 MOVE_TYPE_OPTIONS를 가져오지 못했습니다. callbacks.py에서 기본값을 사용합니다.")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] 
except Exception as e:
    st.error(f"Callbacks: 모듈 로딩 중 오류 - {e}")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]


# --- Callback Functions ---

def update_basket_quantities():
    """
    Updates final_selected_vehicle based on the current recommendation or manual choice,
    and then updates basket item quantities in session_state accordingly.
    This function is crucial for synchronizing vehicle selection and basket defaults.
    """
    # print("\n--- update_basket_quantities CALLED ---") # For debugging

    vehicle_choice = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    _selected_vehicle_candidate = None 

    default_move_type_cb = MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠"
    current_move_type = st.session_state.get('base_move_type', default_move_type_cb)
    
    available_trucks_for_type = []
    if hasattr(data, 'vehicle_prices') and current_move_type in data.vehicle_prices:
        available_trucks_for_type = list(data.vehicle_prices[current_move_type].keys())
    
    # print(f"DEBUG CB: vehicle_choice='{vehicle_choice}', current_move_type='{current_move_type}'")
    # print(f"DEBUG CB: available_trucks_for_type={available_trucks_for_type}")

    if vehicle_choice == "자동 추천 차량 사용":
        recommended_auto = st.session_state.get('recommended_vehicle_auto')
        # print(f"DEBUG CB: recommended_auto='{recommended_auto}'")
        if recommended_auto and "초과" not in recommended_auto:
            if recommended_auto in available_trucks_for_type:
                _selected_vehicle_candidate = recommended_auto
                # print(f"DEBUG CB: Auto - Candidate set to '{_selected_vehicle_candidate}'")
            else:
                _selected_vehicle_candidate = None 
                # print(f"DEBUG CB: Auto - Recommended '{recommended_auto}' not in available trucks. Candidate is None.")
        else:
            _selected_vehicle_candidate = None 
            # print(f"DEBUG CB: Auto - No valid recommendation (None or '초과'). Candidate is None.")
            
    else: # Manual selection
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        # print(f"DEBUG CB: Manual - manual_choice='{manual_choice}'")
        if manual_choice and manual_choice in available_trucks_for_type:
            _selected_vehicle_candidate = manual_choice
            # print(f"DEBUG CB: Manual - Candidate set to '{_selected_vehicle_candidate}'")
        else:
            _selected_vehicle_candidate = None
            # print(f"DEBUG CB: Manual - Invalid or no manual choice. Candidate is None.")
    
    st.session_state.final_selected_vehicle = _selected_vehicle_candidate
    # print(f"DEBUG CB: final_selected_vehicle UPDATED TO: {st.session_state.final_selected_vehicle}")

    # --- Update basket quantities based on the now definitive final_selected_vehicle ---
    final_vehicle_for_baskets = st.session_state.final_selected_vehicle 
    basket_section_name = "포장 자재 📦"
    
    item_defs_for_type = {}
    if hasattr(data, 'item_definitions') and current_move_type in data.item_definitions:
        item_defs_for_type = data.item_definitions[current_move_type]

    basket_items_in_def = []
    if isinstance(item_defs_for_type, dict):
        basket_items_in_def = item_defs_for_type.get(basket_section_name, [])

    if not hasattr(data, 'default_basket_quantities'):
        # print("ERROR CB: data.default_basket_quantities not found.")
        return

    if final_vehicle_for_baskets and final_vehicle_for_baskets in data.default_basket_quantities:
        defaults = data.default_basket_quantities[final_vehicle_for_baskets]
        # print(f"DEBUG CB: Baskets - Using defaults for '{final_vehicle_for_baskets}': {defaults}")
        for item_name, qty in defaults.items():
            if item_name in basket_items_in_def:
                key = f"qty_{current_move_type}_{basket_section_name}_{item_name}"
                st.session_state[key] = qty 
                # print(f"DEBUG CB: Baskets - Set {key} = {qty}")
    else:
        # print(f"DEBUG CB: Baskets - No vehicle ('{final_vehicle_for_baskets}') or no defaults. Setting baskets to 0.")
        for item_name_basket in basket_items_in_def:
            key_basket = f"qty_{current_move_type}_{basket_section_name}_{item_name_basket}"
            st.session_state[key_basket] = 0
            # print(f"DEBUG CB: Baskets - Set {key_basket} = 0")
            
    # print("--- update_basket_quantities END ---\n")


def sync_move_type(widget_key):
    """Callback to sync base_move_type across tabs."""
    if not MOVE_TYPE_OPTIONS: 
        st.error("이사 유형 옵션을 찾을 수 없어 동기화할 수 없습니다.")
        return

    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if new_value not in MOVE_TYPE_OPTIONS:
            return 

        if st.session_state.get('base_move_type') != new_value:
            st.session_state.base_move_type = new_value
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state:
                st.session_state[other_widget_key] = new_value
            # Note: update_basket_quantities() is NOT called here directly.
            # The change in base_move_type will trigger a rerun of app.py,
            # which will then call recommend_vehicle and subsequently update_basket_quantities
            # with the new move_type context. This avoids potential race conditions or stale data.
            pass


def update_selected_gdrive_id():
    """Callback to update the selected Google Drive file ID based on filename selection."""
    selected_name = st.session_state.get("gdrive_selected_filename_widget")
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        st.session_state.gdrive_selected_filename = selected_name