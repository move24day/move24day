# callbacks.py
import streamlit as st
import traceback

try:
    import data
    import calculations
    from state_manager import MOVE_TYPE_OPTIONS
except ImportError as ie:
    st.warning(f"콜백 모듈: 필수 모듈(data, calculations, state_manager.MOVE_TYPE_OPTIONS) 로딩 실패 - {ie}. 기능이 제한될 수 있습니다.")
    if 'MOVE_TYPE_OPTIONS' not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    if 'calculations' not in globals():
        class DummyCalculations:
            def calculate_total_volume_weight(self, s, m): return 0.0, 0.0
            def recommend_vehicle(self, v, w, m): return None, 0.0
        calculations = DummyCalculations()
    if 'data' not in globals(): data = None
except Exception as e:
    st.error(f"Callbacks: 모듈 로딩 중 예외 발생 - {e}")
    if 'MOVE_TYPE_OPTIONS' not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    if 'calculations' not in globals():
        class DummyCalculationsOnError:
            def calculate_total_volume_weight(self, s, m): return 0.0, 0.0
            def recommend_vehicle(self, v, w, m): return None, 0.0
        calculations = DummyCalculationsOnError()
    if 'data' not in globals(): data = None


def update_basket_quantities():
    """
    선택된 차량(자동 또는 수동)을 결정하고,
    만약 차량이 이전 실행과 비교하여 실제로 변경되었다면, 해당 차량의 기본 바구니 수량으로 업데이트합니다.
    차량 변경이 없다면 사용자가 수동 입력한 바구니 수량을 유지합니다.
    """
    # print(f"\nDEBUG CB: --- update_basket_quantities CALLED ---")

    vehicle_choice_method = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    current_move_type = st.session_state.get('base_move_type', MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠")

    available_trucks_for_type = []
    if hasattr(data, 'vehicle_prices') and data and isinstance(data.vehicle_prices, dict) and current_move_type in data.vehicle_prices:
        available_trucks_for_type = list(data.vehicle_prices[current_move_type].keys())

    _determined_vehicle = None
    if vehicle_choice_method == "자동 추천 차량 사용":
        recommended_auto = st.session_state.get('recommended_vehicle_auto')
        if recommended_auto and "초과" not in recommended_auto and recommended_auto in available_trucks_for_type:
            _determined_vehicle = recommended_auto
    else: # Manual selection
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        if manual_choice and manual_choice in available_trucks_for_type:
            _determined_vehicle = manual_choice
        # 수동 선택 시 _determined_vehicle이 None이 될 수 있음 (예: 목록에 없는 차량이거나, 목록이 비었을 때)
        # 이 경우 아래 로직에서 final_selected_vehicle도 None이 됨.

    # 이전 최종 선택 차량 정보 가져오기
    prev_final_vehicle = st.session_state.get("prev_final_selected_vehicle")
    st.session_state.final_selected_vehicle = _determined_vehicle # 현재 결정된 차량으로 final_selected_vehicle 업데이트

    # print(f"DEBUG CB: prev_final_vehicle='{prev_final_vehicle}', current_final_selected_vehicle='{st.session_state.final_selected_vehicle}'")

    # 차량이 실제로 변경되었는지, 또는 첫 실행(prev_final_vehicle이 없을 때)이고 차량이 결정되었는지 확인
    vehicle_has_actually_changed = (prev_final_vehicle != st.session_state.final_selected_vehicle)

    if vehicle_has_actually_changed:
        # print(f"DEBUG CB: Vehicle changed from '{prev_final_vehicle}' to '{st.session_state.final_selected_vehicle}'. Updating basket defaults.")
        vehicle_for_baskets = st.session_state.final_selected_vehicle # 이 값을 사용
        basket_section_name = "포장 자재 📦" # data.py에 정의된 섹션명과 일치해야 함

        item_defs_for_move_type = {}
        if hasattr(data, 'item_definitions') and data and isinstance(data.item_definitions, dict) and current_move_type in data.item_definitions:
            item_defs_for_move_type = data.item_definitions[current_move_type]

        defined_basket_items_in_section = [] # 현재 이사 유형의 "포장 자재 📦" 섹션에 정의된 모든 품목명
        if isinstance(item_defs_for_move_type, dict):
            defined_basket_items_in_section = item_defs_for_move_type.get(basket_section_name, [])

        if not hasattr(data, 'default_basket_quantities') or not data:
            # print("ERROR CB: data.default_basket_quantities not found or data module issue. Zeroing defined baskets.")
            for item_name_in_def in defined_basket_items_in_section:
                st.session_state[f"qty_{current_move_type}_{basket_section_name}_{item_name_in_def}"] = 0
            # 이전 차량 상태 업데이트는 함수 마지막에서 한 번만 수행
            # st.session_state.prev_final_selected_vehicle = st.session_state.final_selected_vehicle
            # return # 여기서 리턴하면 prev_final_selected_vehicle 업데이트 안될 수 있음.

        # 차량이 결정되었고, 해당 차량에 대한 기본 바구니 수량 정보가 있을 때
        if vehicle_for_baskets and hasattr(data, 'default_basket_quantities') and isinstance(data.default_basket_quantities,dict) and vehicle_for_baskets in data.default_basket_quantities:
            basket_vehicle_defaults = data.default_basket_quantities[vehicle_for_baskets]
            # print(f"DEBUG CB: Baskets - Using defaults for '{vehicle_for_baskets}': {basket_vehicle_defaults}")

            for defined_item_name in defined_basket_items_in_section: # '바구니', '중박스', '책바구니' 등
                default_qty = 0 # 기본값은 0으로 시작
                # 차량 기본값에서 해당 포장재의 수량을 찾음
                if defined_item_name in basket_vehicle_defaults:
                    default_qty = basket_vehicle_defaults[defined_item_name]
                elif defined_item_name == "중박스" and "중자바구니" in basket_vehicle_defaults:
                    # item_definitions에는 "중박스", default_basket_quantities에는 "중자바구니"로 되어 있을 경우 호환
                    default_qty = basket_vehicle_defaults["중자바구니"]
                # 다른 바구니 품목에 대한 유사한 호환성 로직이 필요하면 여기에 추가

                item_ss_key = f"qty_{current_move_type}_{basket_section_name}_{defined_item_name}"
                st.session_state[item_ss_key] = default_qty
                # print(f"DEBUG CB: Baskets - Set {item_ss_key} = {default_qty} (due to vehicle change to {vehicle_for_baskets})")
        else: # 차량이 선택되지 않았거나, 선택된 차량에 대한 기본 바구니 정보가 없는 경우
            # print(f"DEBUG CB: Baskets - No valid vehicle ('{vehicle_for_baskets}') for defaults or no defaults defined for it. Setting all defined baskets for this section to 0.")
            for item_name_in_def in defined_basket_items_in_section:
                key_to_zero_no_vehicle_data = f"qty_{current_move_type}_{basket_section_name}_{item_name_in_def}"
                st.session_state[key_to_zero_no_vehicle_data] = 0
    # else: # 차량이 변경되지 않았다면
        # print(f"DEBUG CB: Vehicle has NOT changed ('{st.session_state.final_selected_vehicle}'). Manually entered basket quantities will be preserved.")
        pass

    # 함수가 끝날 때 이전 차량 상태를 현재 차량 상태로 업데이트
    st.session_state.prev_final_selected_vehicle = st.session_state.final_selected_vehicle
    # print("DEBUG CB: --- update_basket_quantities END ---\n")


def handle_item_update():
    """
    품목 수량 변경 또는 이사 유형 변경 시 호출됩니다.
    총 부피/무게를 다시 계산하고, 차량을 추천합니다.
    마지막으로 update_basket_quantities를 호출하여 final_selected_vehicle을 결정하고,
    필요한 경우 (차량 변경 시) 바구니 기본값을 업데이트합니다.
    """
    # print("DEBUG CB: handle_item_update CALLED")
    try:
        current_move_type = st.session_state.get('base_move_type', MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠")
        if not current_move_type or not calculations or not data:
            st.session_state.update({"total_volume": 0.0, "total_weight": 0.0, "recommended_vehicle_auto": None, "remaining_space": 0.0})
            if callable(update_basket_quantities):
                update_basket_quantities() # prev_final_vehicle 비교 로직이 있으므로 그냥 호출
            return

        vol, wt = calculations.calculate_total_volume_weight(st.session_state.to_dict(), current_move_type)
        st.session_state.total_volume = vol
        st.session_state.total_weight = wt

        rec_vehicle, rem_space = calculations.recommend_vehicle(vol, wt, current_move_type)
        st.session_state.recommended_vehicle_auto = rec_vehicle
        st.session_state.remaining_space = rem_space
        # print(f"DEBUG CB (handle_item_update): Recalculated: Vol={vol}, Wt={wt}, RecVehicle='{rec_vehicle}'")
    except Exception as e:
        st.error(f"실시간 업데이트 중 계산 오류: {e}")
        traceback.print_exc() # 콘솔에 상세 오류 출력
        st.session_state.update({"total_volume": 0.0, "total_weight": 0.0, "recommended_vehicle_auto": None, "remaining_space": 0.0})

    # update_basket_quantities는 항상 호출되어 final_selected_vehicle을 결정하고,
    # 내부 로직에 따라 (prev_final_selected_vehicle 비교) 바구니 수량을 업데이트하거나 유지합니다.
    if callable(update_basket_quantities):
        update_basket_quantities()
    # print("DEBUG CB: handle_item_update FINISHED")


def sync_move_type(widget_key):
    """
    탭 간 이사 유형을 동기화하고, 이사 유형 변경 시 관련 계산 및 바구니 수량 업데이트를 트리거합니다.
    """
    # print(f"DEBUG CB: sync_move_type CALLED with widget_key='{widget_key}'")
    if not MOVE_TYPE_OPTIONS: # MOVE_TYPE_OPTIONS가 로드되지 않았으면 중단
        # st.error("이사 유형 옵션 로드 실패.") # 사용자에게 오류를 계속 표시할 필요는 없을 수 있음
        return

    if widget_key in st.session_state:
        new_move_type = st.session_state[widget_key]
        if new_move_type not in MOVE_TYPE_OPTIONS: # 유효하지 않은 이사 유형이면 중단
            # print(f"Warning CB (sync_move_type): Invalid move type '{new_move_type}' selected.")
            return

        previous_move_type = st.session_state.get('base_move_type')
        if previous_move_type != new_move_type:
            st.session_state.base_move_type = new_move_type # 현재 이사 유형 업데이트
            # print(f"DEBUG CB (sync_move_type): base_move_type changed from '{previous_move_type}' to '{new_move_type}'")

            # 다른 탭의 이사 유형 위젯도 동기화
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state:
                st.session_state[other_widget_key] = new_move_type

            # 이사 유형이 변경되었으므로, 품목 및 차량 관련 모든 것을 재계산해야 함.
            # handle_item_update를 호출하면 그 안에서 update_basket_quantities가 호출되고,
            # update_basket_quantities 내부에서 prev_final_selected_vehicle 비교를 통해
            # 차량 변경 여부를 판단하여 바구니 기본값을 설정합니다.
            # 이사 유형이 바뀌면 차량 추천도 바뀔 가능성이 매우 높으므로,
            # 이 과정에서 바구니는 새 차량의 기본값으로 설정될 것입니다.
            if callable(handle_item_update):
                # print("DEBUG CB (sync_move_type): Calling handle_item_update due to move type change.")
                handle_item_update()
        # else: # 이사 유형이 변경되지 않았다면 아무것도 하지 않음
            # print(f"DEBUG CB (sync_move_type): Move type '{new_move_type}' is the same as previous. No action.")
    # else: # widget_key가 세션 상태에 없으면 (비정상적 상황)
        # print(f"Warning CB (sync_move_type): widget_key '{widget_key}' not in session_state.")
        pass


def update_selected_gdrive_id():
    """Google Drive 파일 선택 시 ID를 업데이트하는 콜백입니다."""
    selected_name = st.session_state.get("gdrive_selected_filename_widget_tab1") # Tab1의 위젯 키 사용
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        if file_id:
            st.session_state.gdrive_selected_file_id = file_id
            st.session_state.gdrive_selected_filename = selected_name
            # print(f"DEBUG CB (update_selected_gdrive_id): Selected GDrive file: '{selected_name}', ID: '{file_id}'")
        # else: # 선택된 이름에 해당하는 ID가 맵에 없을 경우 (오류 상황)
            # print(f"Warning CB (update_selected_gdrive_id): No ID found for GDrive file name '{selected_name}' in map.")
    # else: # 선택된 파일 이름이 없거나 파일 맵이 없는 경우
        # print(f"DEBUG CB (update_selected_gdrive_id): No GDrive file selected or map not ready.")
        pass