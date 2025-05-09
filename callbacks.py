# callbacks.py
import streamlit as st

# Import necessary custom modules
try:
    import data
    # state_manager에서 MOVE_TYPE_OPTIONS를 가져오도록 시도
    from state_manager import MOVE_TYPE_OPTIONS
except ImportError:
    # state_manager 또는 해당 변수를 찾을 수 없는 경우를 위한 폴백(Fallback)
    st.warning("state_manager로부터 MOVE_TYPE_OPTIONS를 가져오지 못했습니다. callbacks.py에서 기본값을 사용합니다.")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] # Fallback
except Exception as e:
    st.error(f"Callbacks: 모듈 로딩 중 오류 - {e}")
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] # Fallback


# --- Callback Functions ---

def update_basket_quantities():
    """
    선택된 차량에 따라 final_selected_vehicle을 업데이트하고,
    그 결과에 맞춰 포장 자재(바구니)의 기본 수량을 세션 상태에 업데이트합니다.
    """
    # print("\n--- update_basket_quantities CALLED ---") # 디버깅용 로그 시작

    vehicle_choice = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    _selected_vehicle_candidate = None # 최종 선택될 차량 후보, 명확히 None으로 초기화

    # 현재 이사 유형 및 해당 유형에 가격이 책정된 차량 목록 가져오기
    # MOVE_TYPE_OPTIONS는 이 파일 상단에서 임포트 또는 폴백 처리됨
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
                # print(f"DEBUG CB: Auto - Set candidate to '{_selected_vehicle_candidate}'")
            else:
                # 추천은 되었으나 현재 이사 유형에 가격이 없는 차량이거나 목록에 없는 경우
                _selected_vehicle_candidate = None 
                # print(f"DEBUG CB: Auto - recommended_auto '{recommended_auto}' not in available_trucks. Candidate is None.")
        else:
            # 추천이 없거나 (None), 물량 초과인 경우
            _selected_vehicle_candidate = None 
            # print(f"DEBUG CB: Auto - No valid recommendation or 초과. recommended_auto='{recommended_auto}'. Candidate is None.")
            
    else: # 수동으로 차량 선택
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        # print(f"DEBUG CB: Manual mode - manual_choice='{manual_choice}'")
        if manual_choice and manual_choice in available_trucks_for_type:
            _selected_vehicle_candidate = manual_choice
            # print(f"DEBUG CB: Manual - Set candidate to '{_selected_vehicle_candidate}'")
        else:
            # 유효하지 않은 수동 선택이거나 manual_choice가 None일 경우
            _selected_vehicle_candidate = None
            # print(f"DEBUG CB: Manual - Invalid or no manual choice. Candidate is None.")
    
    st.session_state.final_selected_vehicle = _selected_vehicle_candidate
    # print(f"DEBUG CB: final_selected_vehicle UPDATED TO: {st.session_state.final_selected_vehicle}")

    # --- 포장 자재 수량 업데이트 ---
    final_vehicle_for_baskets = st.session_state.final_selected_vehicle # 방금 업데이트된 값 사용
    basket_section_name = "포장 자재 📦"
    
    item_defs_for_type = {} # 현재 이사 유형에 대한 품목 정의
    if hasattr(data, 'item_definitions') and current_move_type in data.item_definitions:
        item_defs_for_type = data.item_definitions[current_move_type]

    basket_items_in_def = [] # 현재 이사 유형의 "포장 자재" 섹션에 정의된 품목들
    if isinstance(item_defs_for_type, dict):
        basket_items_in_def = item_defs_for_type.get(basket_section_name, [])

    if not hasattr(data, 'default_basket_quantities'):
        # print("ERROR CB: data.default_basket_quantities not found.")
        return # 필수 데이터 없으면 바구니 업데이트 불가

    if final_vehicle_for_baskets and final_vehicle_for_baskets in data.default_basket_quantities:
        # 선택된 차량이 있고, 해당 차량에 대한 기본 바구니 수량 정보가 있는 경우
        defaults = data.default_basket_quantities[final_vehicle_for_baskets]
        # print(f"DEBUG CB: Baskets - Using defaults for '{final_vehicle_for_baskets}': {defaults}")
        for item_name, qty in defaults.items():
            # 기본 수량에 정의된 각 바구니 품목에 대해
            if item_name in basket_items_in_def: # 현재 이사 유형의 포장자재 목록에도 해당 품목이 정의되어 있다면
                key = f"qty_{current_move_type}_{basket_section_name}_{item_name}"
                st.session_state[key] = qty # 세션 상태의 해당 바구니 수량 업데이트
                # print(f"DEBUG CB: Baskets - Set {key} = {qty}")
            # else: # 기본 수량에는 있지만 현재 이사 유형의 포장재 목록에는 없는 경우 (예: 사무실 이사에는 책바구니 없음)
                # print(f"DEBUG CB: Baskets - Item '{item_name}' from defaults not in current move_type's basket definition for '{current_move_type}'.")
    else:
        # print(f"DEBUG CB: Baskets - No vehicle selected ('{final_vehicle_for_baskets}') or no defaults. Setting all defined baskets for this move type to 0.")
        # 차량이 선택되지 않았거나, 선택된 차량에 대한 기본 바구니 수량 정보가 없는 경우
        # 현재 이사 유형에 정의된 모든 포장 자재 품목의 수량을 0으로 설정
        for item_name_basket in basket_items_in_def:
            key_basket = f"qty_{current_move_type}_{basket_section_name}_{item_name_basket}"
            st.session_state[key_basket] = 0
            # print(f"DEBUG CB: Baskets - Set {key_basket} = 0")
            
    # print("--- update_basket_quantities END ---\n")


def sync_move_type(widget_key):
    """Callback to sync base_move_type across tabs and trigger basket/vehicle update."""
    # MOVE_TYPE_OPTIONS는 이 파일 상단에서 임포트 또는 폴백 처리됨
    if not MOVE_TYPE_OPTIONS: 
        st.error("이사 유형 옵션을 찾을 수 없어 동기화할 수 없습니다.")
        return

    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if new_value not in MOVE_TYPE_OPTIONS:
            # print(f"Warning: Invalid move type selected in widget {widget_key}: {new_value}. Ignoring change.")
            return # 유효하지 않은 값이면 변경 무시

        if st.session_state.get('base_move_type') != new_value:
            st.session_state.base_move_type = new_value
            # 다른 탭의 이사 유형 위젯 값도 동기화
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state:
                st.session_state[other_widget_key] = new_value
            
            # 이사 유형이 변경되었으므로, 차량 추천 및 바구니 수량 업데이트 필요.
            # app.py에서 이사 유형 변경 후 전체 로직이 재실행되면서 recommend_vehicle 및 update_basket_quantities가
            # 호출될 것이므로, 여기서 직접 update_basket_quantities를 호출하는 것이 최선이 아닐 수 있음.
            # app.py의 메인 로직 흐름에 맡기는 것이 상태 일관성에 더 유리할 수 있다.
            # 만약 app.py의 호출만으로 부족하다면 아래 주석 해제 고려.
            # print(f"DEBUG CB: sync_move_type - base_move_type changed to {new_value}. Triggering update_basket_quantities.")
            # update_basket_quantities() # app.py에서 이미 처리하므로 중복 호출 방지 또는 신중한 호출 필요
            pass # app.py에서 다음 rerun 시 처리하도록 함


def update_selected_gdrive_id():
    """Callback to update the selected Google Drive file ID based on filename selection."""
    selected_name = st.session_state.get("gdrive_selected_filename_widget")
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        st.session_state.gdrive_selected_filename = selected_name

# process_and_clear_on_upload 함수는 제거되었으므로 해당 내용 없음