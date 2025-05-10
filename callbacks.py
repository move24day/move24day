# callbacks.py (이미지 처리 콜백 제거)
import streamlit as st

# Import necessary custom modules
try:
    import data
    from state_manager import MOVE_TYPE_OPTIONS
except ImportError as e:
    st.error(f"Callbacks: 필수 모듈 로딩 실패 - {e}")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
except Exception as e:
    st.error(f"Callbacks: 모듈 로딩 중 오류 - {e}")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] # Fallback


# --- Callback Functions ---

def update_basket_quantities():
    """Callback to update basket quantities based on the final selected vehicle."""
    vehicle_choice = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    selected_vehicle = None

    current_move_type_options_cb = globals().get('MOVE_TYPE_OPTIONS') # Get options safely
    default_move_type_cb = current_move_type_options_cb[0] if current_move_type_options_cb else "가정 이사 🏠"
    current_move_type = st.session_state.get('base_move_type', default_move_type_cb)
    if current_move_type_options_cb and current_move_type not in current_move_type_options_cb:
         current_move_type = default_move_type_cb # Fallback

    available_trucks_for_type = data.vehicle_prices.get(current_move_type, {}).keys() if hasattr(data, 'vehicle_prices') else []

    if vehicle_choice == "자동 추천 차량 사용":
        recommended_auto = st.session_state.get('recommended_vehicle_auto')
        if recommended_auto and "초과" not in recommended_auto and recommended_auto in available_trucks_for_type:
             selected_vehicle = recommended_auto
    else: # Manual selection
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        if manual_choice and manual_choice in available_trucks_for_type:
            selected_vehicle = manual_choice

    st.session_state.final_selected_vehicle = selected_vehicle

    basket_section_name = "포장 자재 📦"
    item_defs_for_type = data.item_definitions.get(current_move_type, {}) if hasattr(data, 'item_definitions') else {}
    basket_items_in_def = item_defs_for_type.get(basket_section_name, [])

    if not hasattr(data, 'default_basket_quantities'):
        print("Error: data.default_basket_quantities not found in update_basket_quantities")
        return

    if selected_vehicle and selected_vehicle in data.default_basket_quantities:
        defaults = data.default_basket_quantities[selected_vehicle]
        for item, qty in defaults.items():
            if item in basket_items_in_def:
                key = f"qty_{current_move_type}_{basket_section_name}_{item}"
                if key in st.session_state: st.session_state[key] = qty
                else: st.session_state[key] = qty; print(f"Warning: Initialized missing basket key during update: {key}")
    else:
        for item in basket_items_in_def:
             key = f"qty_{current_move_type}_{basket_section_name}_{item}"
             if key in st.session_state: st.session_state[key] = 0


def sync_move_type(widget_key):
    """Callback to sync base_move_type across tabs and update baskets."""
    current_move_type_options_cb = globals().get('MOVE_TYPE_OPTIONS')
    if not current_move_type_options_cb: st.error("이사 유형 옵션을 찾을 수 없어 동기화할 수 없습니다."); return

    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if new_value not in current_move_type_options_cb:
            print(f"Warning: Invalid move type selected in widget {widget_key}: {new_value}. Ignoring change.")
            return

        if st.session_state.get('base_move_type') != new_value:
            st.session_state.base_move_type = new_value
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state: st.session_state[other_widget_key] = new_value
            update_basket_quantities()


def update_selected_gdrive_id():
    """Callback to update the selected Google Drive file ID based on filename selection."""
    selected_name = st.session_state.get("gdrive_selected_filename_widget")
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        st.session_state.gdrive_selected_filename = selected_name

# --- process_and_clear_on_upload 함수 제거 ---
# (만약 이 파일에 있었다면 해당 함수 정의를 삭제합니다)