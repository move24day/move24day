# ui_tab3.py
# ui_tab3.py (실제 투입 인력 정보 테이블 완전 삭제, 이사 정보 요약 표시)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date
import traceback
import re

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # pdf_generator 임포트 (이미지 변환 함수 포함)
    import excel_filler
    import email_utils
    import callbacks
    from state_manager import MOVE_TYPE_OPTIONS # state_manager에서 가져옴
    import mms_utils # mms_utils 임포트
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    missing_modules = []
    if hasattr(e, "name"):
        if e.name == "email_utils": missing_modules.append("email_utils.py (이메일 발송 비활성화)")
        if e.name == "mms_utils": missing_modules.append("mms_utils.py (MMS 발송 비활성화)")
        if e.name == "pdf_generator": missing_modules.append("pdf_generator.py (PDF/이미지 생성 비활성화)")
        if e.name == "excel_filler": missing_modules.append("excel_filler.py (Excel 생성 비활성화)")
    if missing_modules:
        st.warning(f"다음 모듈 로드 실패: {', '.join(missing_modules)}")

    # 필수 모듈 정의 (이것들이 없으면 탭3 기능 상당수 사용 불가)
    critical_modules = ["data", "utils", "calculations", "callbacks", "state_manager"]
    missing_critical = [name for name in critical_modules if name not in globals()]
    if missing_critical:
        st.error(f"UI Tab 3: 필수 핵심 모듈 ({', '.join(missing_critical)}) 로딩 실패. 앱 실행을 중단합니다.")
        st.stop()
    if "MOVE_TYPE_OPTIONS" not in globals(): # MOVE_TYPE_OPTIONS는 state_manager에서 오므로 critical에 포함될 수 있음
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] # 비상용 기본값
        st.warning("MOVE_TYPE_OPTIONS 로드 실패. 기본값을 사용합니다.")

except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 예상치 못한 오류 발생 - {e}")
    traceback.print_exc()
    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션 ")

    update_basket_quantities_callback = getattr(callbacks, "update_basket_quantities", None)
    sync_move_type_callback = getattr(callbacks, "sync_move_type", None)

    if not callable(update_basket_quantities_callback) or not callable(sync_move_type_callback):
        st.error("UI Tab 3: 콜백 함수(update_basket_quantities 또는 sync_move_type)를 찾을 수 없습니다. callbacks.py를 확인하세요.")
        # 여기서 return 하거나, 콜백 없이도 최소한으로 동작할 수 있는 로직 구성 필요

    # --- Move Type Selection (Tab 3) ---
    st.subheader("🏢 이사 유형 ")
    current_move_type_from_state = st.session_state.get("base_move_type")
    move_type_options_local = MOVE_TYPE_OPTIONS

    current_index_tab3 = 0
    if move_type_options_local:
        try:
            current_index_tab3 = move_type_options_local.index(current_move_type_from_state)
        except (ValueError, TypeError): # 현재 상태의 이사 유형이 옵션에 없는 경우
            current_index_tab3 = 0
            if move_type_options_local: # 옵션이 존재하면 첫 번째 값으로 강제 설정
                 st.session_state.base_move_type = move_type_options_local[0]
                 if "base_move_type_widget_tab1" in st.session_state: # Tab1 위젯도 동기화
                      st.session_state.base_move_type_widget_tab1 = move_type_options_local[0]
    else:
        st.error("이사 유형 옵션(MOVE_TYPE_OPTIONS)을 불러올 수 없습니다.")
        return

    st.radio(
        "기본 이사 유형:",
        options=move_type_options_local, index=current_index_tab3, horizontal=True,
        key="base_move_type_widget_tab3",
        on_change=sync_move_type_callback,
        args=("base_move_type_widget_tab3",) if sync_move_type_callback else None
    )
    st.divider()

    # --- Vehicle Selection ---
    with st.container(border=True):
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])

        with col_v1_widget:
            st.radio(
                "차량 선택 방식:",
                ["자동 추천 차량 사용", "수동으로 차량 선택"],
                key="vehicle_select_radio",
                help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.",
                on_change=update_basket_quantities_callback # 콜백이 있어야 제대로 동작
            )

        with col_v2_widget:
            current_move_type_for_vehicle = st.session_state.get("base_move_type")
            vehicle_prices_options_for_vehicle = {}
            available_trucks_for_vehicle_select = []

            if current_move_type_for_vehicle and hasattr(data, "vehicle_prices") and isinstance(data.vehicle_prices, dict):
                vehicle_prices_options_for_vehicle = data.vehicle_prices.get(current_move_type_for_vehicle, {})

            if vehicle_prices_options_for_vehicle and hasattr(data, "vehicle_specs") and isinstance(data.vehicle_specs, dict):
                available_trucks_for_vehicle_select = sorted(
                    [truck for truck in vehicle_prices_options_for_vehicle.keys() if truck in data.vehicle_specs],
                    key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0)
                )

            use_auto_vehicle_selection = st.session_state.get("vehicle_select_radio") == "자동 추천 차량 사용"
            recommended_vehicle_from_state = st.session_state.get("recommended_vehicle_auto")
            final_vehicle_from_state_display = st.session_state.get("final_selected_vehicle") # 최종 확정된 차량
            current_total_volume_display = st.session_state.get("total_volume", 0.0)
            current_total_weight_display = st.session_state.get("total_weight", 0.0)

            if use_auto_vehicle_selection:
                if final_vehicle_from_state_display and final_vehicle_from_state_display in available_trucks_for_vehicle_select:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_from_state_display}**")
                    spec = data.vehicle_specs.get(final_vehicle_from_state_display) if hasattr(data, "vehicle_specs") else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get('capacity', 'N/A')}m³, {spec.get('weight_capacity', 'N/A'):,}kg")
                        st.caption(f"현재 이사짐 예상: {current_total_volume_display:.2f}m³, {current_total_weight_display:.2f}kg")
                else:
                    error_msg_auto = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_from_state and "초과" in recommended_vehicle_from_state:
                        error_msg_auto += f"물량 초과({recommended_vehicle_from_state}). 수동 선택 필요."
                    elif recommended_vehicle_from_state: # 추천은 되었으나 현재 이사 유형에 없는 차량일 경우 등
                        error_msg_auto += f"추천된 차량({recommended_vehicle_from_state}) 사용 불가. 수동 선택 필요."
                    elif current_total_volume_display > 0 or current_total_weight_display > 0: # 물량은 있으나 추천 차량이 없는 경우
                        error_msg_auto += "적합 차량 없음. 수동 선택 필요."
                    else: # 물품 미선택
                        error_msg_auto += "물품 미선택. 탭2에서 물품 선택 필요."
                    st.error(error_msg_auto)

                    if not available_trucks_for_vehicle_select:
                        st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else: # 수동 선택 UI 표시 (자동 추천 불가 시)
                        current_manual_selection_for_auto_fail = st.session_state.get("manual_vehicle_select_value", available_trucks_for_vehicle_select[0] if available_trucks_for_vehicle_select else None)
                        idx_for_auto_fail = 0
                        if current_manual_selection_for_auto_fail in available_trucks_for_vehicle_select:
                            try: idx_for_auto_fail = available_trucks_for_vehicle_select.index(current_manual_selection_for_auto_fail)
                            except ValueError: idx_for_auto_fail = 0

                        st.selectbox(
                            "수동으로 차량 선택:",
                            available_trucks_for_vehicle_select, index=idx_for_auto_fail,
                            key="manual_vehicle_select_value",
                            on_change=update_basket_quantities_callback
                        )
            else: # 수동으로 차량 선택 모드
                if not available_trucks_for_vehicle_select:
                    st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection = st.session_state.get("manual_vehicle_select_value", available_trucks_for_vehicle_select[0] if available_trucks_for_vehicle_select else None)
                    current_index_manual = 0
                    if current_manual_selection in available_trucks_for_vehicle_select:
                        try: current_index_manual = available_trucks_for_vehicle_select.index(current_manual_selection)
                        except ValueError: current_index_manual = 0

                    st.selectbox(
                        "차량 직접 선택:",
                        available_trucks_for_vehicle_select, index=current_index_manual,
                        key="manual_vehicle_select_value",
                        on_change=update_basket_quantities_callback
                    )
                    # 수동 선택 시에도 최종 확정된 차량 정보 표시
                    if final_vehicle_from_state_display and final_vehicle_from_state_display in available_trucks_for_vehicle_select:
                        st.info(f"ℹ️ 수동 선택됨: **{final_vehicle_from_state_display}**")
                        spec_manual_disp = data.vehicle_specs.get(final_vehicle_from_state_display) if hasattr(data, "vehicle_specs") else None
                        if spec_manual_disp:
                            st.caption(f"선택차량 최대 용량: {spec_manual_disp.get('capacity', 'N/A')}m³, {spec_manual_disp.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {current_total_volume_display:.2f}m³, {current_total_weight_display:.2f}kg")
    st.divider()

    # --- Work Conditions & Options ---
    with st.container(border=True):
        st.subheader("🛠️ 작업 조건 및 추가 옵션")
        sky_from = st.session_state.get("from_method") == "스카이 🏗️"
        sky_to = st.session_state.get("to_method") == "스카이 🏗️"

        if sky_from or sky_to:
            st.warning("스카이 작업 선택됨 - 시간 입력 필요", icon="🏗️")
            cols_sky = st.columns(2)
            with cols_sky[0]:
                if sky_from: st.number_input("출발 스카이 시간(h)", min_value=1, step=1, key="sky_hours_from")
            with cols_sky[1]:
                if sky_to: st.number_input("도착 스카이 시간(h)", min_value=1, step=1, key="sky_hours_final")
            st.write("")

        col_add1, col_add2 = st.columns(2)
        with col_add1: st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2: st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        st.write("")

        st.subheader("🚚 실제 투입 차량 ") # 이 부분은 견적 계산에는 직접 사용되지 않으나, 정보 기록용
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다. (Excel 출력 등에 사용)")
        st.write("")

        base_w = 0
        remove_opt = False
        discount_amount = 0
        final_vehicle_for_housewife_option = st.session_state.get("final_selected_vehicle")
        current_move_type_for_housewife_option = st.session_state.get("base_move_type")

        if current_move_type_for_housewife_option and hasattr(data, "vehicle_prices") and isinstance(data.vehicle_prices, dict):
            vehicle_prices_options_hw = data.vehicle_prices.get(current_move_type_for_housewife_option, {})
            if final_vehicle_for_housewife_option and final_vehicle_for_housewife_option in vehicle_prices_options_hw:
                base_info_hw = vehicle_prices_options_hw.get(final_vehicle_for_housewife_option, {})
                base_w_raw = base_info_hw.get("housewife")
                try:
                    base_w = int(base_w_raw) if base_w_raw is not None else 0
                    if base_w > 0:
                         remove_opt = True
                         add_cost_hw = getattr(data, "ADDITIONAL_PERSON_COST", 0)
                         if isinstance(add_cost_hw, (int, float)):
                             discount_amount = add_cost_hw * base_w
                         else:
                             discount_amount = 0 # 오류 시 할인 없음
                except (ValueError, TypeError):
                     base_w = 0

        if remove_opt:
            st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if "remove_base_housewife" in st.session_state: # UI 일관성을 위해 키가 존재하면 False로 설정
                st.session_state.remove_base_housewife = False

        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
            if st.session_state.get("has_waste_check"):
                waste_cost_per_ton_disp = getattr(data, "WASTE_DISPOSAL_COST_PER_TON", 0)
                waste_cost_val_disp = 0
                if isinstance(waste_cost_per_ton_disp, (int, float)):
                    waste_cost_val_disp = waste_cost_per_ton_disp
                st.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input", format="%.1f")
                if waste_cost_val_disp > 0:
                    st.caption(f"💡 1톤당 {waste_cost_val_disp:,}원 추가 비용 발생")

        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options_list = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_surcharges_exist = hasattr(data, "special_day_prices") and isinstance(data.special_day_prices, dict)
        if not date_surcharges_exist:
            st.warning("data.py에 날짜 할증(special_day_prices) 정보가 없습니다.")

        date_option_keys = [f"date_opt_{i}_widget" for i in range(len(date_options_list))]
        cols_date_options = st.columns(len(date_options_list))
        for i, option_text in enumerate(date_options_list):
            with cols_date_options[i]:
                 surcharge_val = 0
                 if date_surcharges_exist:
                     surcharge_val = data.special_day_prices.get(option_text, 0)
                 help_text_date = f"{surcharge_val:,}원 할증" if surcharge_val > 0 else "할증 없음"
                 st.checkbox(option_text, key=date_option_keys[i], help=help_text_date)
    st.divider()

    # --- Cost Adjustment & Deposit ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        num_cols_for_cost_adj = 3
        if st.session_state.get("has_via_point"):
            num_cols_for_cost_adj = 4

        cols_cost_adjustment = st.columns(num_cols_for_cost_adj)
        with cols_cost_adjustment[0]: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with cols_cost_adjustment[1]: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with cols_cost_adjustment[2]: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
        if st.session_state.get("has_via_point"):
            with cols_cost_adjustment[3]: st.number_input("↪️ 경유지 추가요금", min_value=0, step=10000, key="via_point_surcharge", format="%d", help="경유지 작업으로 인해 발생하는 추가 요금")
    st.divider()

    # --- Final Quote Results ---
    st.header("💵 최종 견적 결과")

    final_selected_vehicle_for_calc = st.session_state.get("final_selected_vehicle")
    calculated_total_cost = 0
    calculated_cost_items = []
    calculated_personnel_info = {} # calculations.py에서 반환될 인력 정보

    if final_selected_vehicle_for_calc:
        try:
            # 보관이사 시 기간 재계산 (state_manager와 유사 로직, UI 변경 즉시 반영 위해)
            if st.session_state.get("is_storage_move"):
                moving_dt_for_duration = st.session_state.get("moving_date")
                arrival_dt_for_duration = st.session_state.get("arrival_date")
                if isinstance(moving_dt_for_duration, date) and isinstance(arrival_dt_for_duration, date) and arrival_dt_for_duration >= moving_dt_for_duration:
                    delta_duration = arrival_dt_for_duration - moving_dt_for_duration
                    st.session_state.storage_duration = max(1, delta_duration.days + 1)
                else: # 날짜가 유효하지 않으면 최소 1일
                    st.session_state.storage_duration = 1

            current_state_for_calc = st.session_state.to_dict()
            if hasattr(calculations, "calculate_total_moving_cost") and callable(calculations.calculate_total_moving_cost):
                calculated_total_cost, calculated_cost_items, calculated_personnel_info = calculations.calculate_total_moving_cost(current_state_for_calc)
                # PDF/이미지/Excel 생성을 위해 세션 상태에 저장
                st.session_state.calculated_cost_items_for_export = calculated_cost_items
                st.session_state.total_cost_for_export = calculated_total_cost
                st.session_state.personnel_info_for_export = calculated_personnel_info
            else:
                st.error("최종 비용 계산 함수(calculate_total_moving_cost)를 찾을 수 없습니다. calculations.py를 확인하세요.")
                # 오류 발생 시 내보내기용 데이터 초기화
                st.session_state.calculated_cost_items_for_export = []
                st.session_state.total_cost_for_export = 0
                st.session_state.personnel_info_for_export = {}


            total_cost_display = calculated_total_cost if isinstance(calculated_total_cost, (int, float)) else 0
            deposit_amount_display = st.session_state.get("deposit_amount", 0)
            try: deposit_amount_val_display = int(deposit_amount_display)
            except (ValueError, TypeError): deposit_amount_val_display = 0
            remaining_balance_display = total_cost_display - deposit_amount_val_display

            st.subheader(f"💰 총 견적 비용: {total_cost_display:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_val_display:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_display:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            cost_item_error_found = next((item_detail for item_detail in calculated_cost_items if isinstance(item_detail, (list, tuple)) and len(item_detail) > 0 and str(item_detail[0]) == "오류"), None)
            if cost_item_error_found:
                st.error(f"비용 계산 중 오류 발생: {cost_item_error_found[2] if len(cost_item_error_found)>2 else '알 수 없는 비용 오류'}")
            else:
                valid_cost_items_for_display = [item for item in calculated_cost_items if isinstance(item, (list, tuple)) and len(item) >= 2]
                if valid_cost_items_for_display:
                    df_data_for_display = []
                    for item_data_disp in valid_cost_items_for_display:
                        name_disp, value_disp = str(item_data_disp[0]), item_data_disp[1]
                        note_disp = str(item_data_disp[2]) if len(item_data_disp) > 2 else ""
                        try: value_disp = int(value_disp) # 금액은 정수로 시도
                        except: pass # 변환 안되면 그대로 둠
                        df_data_for_display.append([name_disp, value_disp, note_disp])

                    df_costs_to_show = pd.DataFrame(df_data_for_display, columns=["항목", "금액", "비고"])
                    st.dataframe(
                        df_costs_to_show.style.format({"금액": "{:,.0f}"}, na_rep='-')
                                    .set_properties(**{'text-align': 'right'}, subset=['금액'])
                                    .set_properties(**{'text-align': 'left'}, subset=['항목', '비고']),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("산출된 비용 내역이 없습니다.")
            st.write("") # 비용 내역과 이사 정보 요약 사이 간격


            # --- 이사 정보 요약 (텍스트 기반, "투입 인력 정보" 테이블 대체) ---
            st.subheader("📋 이사 정보 요약")
            from_addr_summary_val = st.session_state.get('from_location', '정보없음')
            to_addr_summary_val = st.session_state.get('to_location', '정보없음')
            selected_vehicle_summary_val = st.session_state.get('final_selected_vehicle', '미선택') # 최종 확정된 차량 사용
            vehicle_tonnage_summary_text = ""
            if isinstance(selected_vehicle_summary_val, str) and selected_vehicle_summary_val != '미선택':
                match_ton = re.search(r'(\d+(\.\d+)?\s*톤?)', selected_vehicle_summary_val)
                if match_ton:
                    ton_part_text = match_ton.group(1)
                    if "톤" not in ton_part_text: vehicle_tonnage_summary_text = ton_part_text.strip() + "톤"
                    else: vehicle_tonnage_summary_text = ton_part_text.strip()
                else: vehicle_tonnage_summary_text = selected_vehicle_summary_val
            else: vehicle_tonnage_summary_text = "미선택"

            customer_name_summary_val = st.session_state.get('customer_name', '정보없음')
            customer_phone_summary_val = st.session_state.get('customer_phone', '정보없음')

            # personnel_info는 위에서 calculate_total_moving_cost로부터 받은 calculated_personnel_info 사용
            p_info_summary_dict = calculated_personnel_info if isinstance(calculated_personnel_info, dict) else {}
            men_summary_val = p_info_summary_dict.get('final_men', 0)
            women_summary_val = p_info_summary_dict.get('final_women', 0)
            personnel_str_summary_text = f"{men_summary_val}"
            if women_summary_val > 0: personnel_str_summary_text += f"+{women_summary_val}"

            from_method_summary_text = st.session_state.get('from_method', '미지정')
            to_method_summary_text = st.session_state.get('to_method', '미지정')
            has_via_point_summary_bool = st.session_state.get('has_via_point', False)
            via_point_location_summary_text = st.session_state.get('via_point_location', '')

            is_storage_move_summary_bool = st.session_state.get('is_storage_move', False)
            storage_type_summary_text = st.session_state.get('storage_type', '')
            storage_use_electricity_summary_bool = st.session_state.get('storage_use_electricity', False)

            # 비용 항목 추출 함수 (재정의 또는 utils로 이동 고려)
            def get_cost_from_items_local(items_list, label_prefix):
                for item_data in items_list:
                    if isinstance(item_data, (list, tuple)) and len(item_data) >=2:
                        item_label, item_cost_val_local = item_data[0], item_data[1]
                        if isinstance(item_label, str) and item_label.startswith(label_prefix):
                            try: return int(item_cost_val_local or 0)
                            except (ValueError, TypeError): return 0
                return 0

            def get_note_from_items_local(items_list, label_prefix):
                for item_data in items_list:
                    if isinstance(item_data, (list, tuple)) and len(item_data) >=3:
                        item_label_local, _, item_note_val_local = item_data[0], item_data[1], item_data[2]
                        if isinstance(item_label_local, str) and item_label_local.startswith(label_prefix):
                            return str(item_note_val_local or '')
                return ""

            base_fare_summary_val = get_cost_from_items_local(calculated_cost_items, "기본 운임")
            adj_discount_val = get_cost_from_items_local(calculated_cost_items, "할인 조정")
            adj_surcharge_val = get_cost_from_items_local(calculated_cost_items, "할증 조정")
            adjustment_total_summary_val = adj_discount_val + adj_surcharge_val

            date_surcharge_summary_val = get_cost_from_items_local(calculated_cost_items, "날짜 할증")
            long_distance_summary_val = get_cost_from_items_local(calculated_cost_items, "장거리 운송료")
            add_personnel_summary_val = get_cost_from_items_local(calculated_cost_items, "추가 인력")
            housewife_discount_summary_val = get_cost_from_items_local(calculated_cost_items, "기본 여성 인원 제외 할인")
            via_point_surcharge_summary_val = get_cost_from_items_local(calculated_cost_items, "경유지 추가요금")

            total_moving_fee_summary_val = (base_fare_summary_val + adjustment_total_summary_val +
                                           date_surcharge_summary_val + long_distance_summary_val +
                                           add_personnel_summary_val + housewife_discount_summary_val +
                                           via_point_surcharge_summary_val)

            ladder_from_summary_val = get_cost_from_items_local(calculated_cost_items, "출발지 사다리차")
            ladder_to_summary_val = get_cost_from_items_local(calculated_cost_items, "도착지 사다리차")
            ladder_regional_summary_val = get_cost_from_items_local(calculated_cost_items, "지방 사다리 추가요금")

            sky_from_val = get_cost_from_items_local(calculated_cost_items, "출발지 스카이 장비")
            sky_to_val = get_cost_from_items_local(calculated_cost_items, "도착지 스카이 장비")
            sky_total_val = sky_from_val + sky_to_val # calculations.py에서 합산된 "스카이 장비"로 나올 수도 있음
            if sky_total_val == 0: # 합산된 경우
                 sky_total_val = get_cost_from_items_local(calculated_cost_items, "스카이 장비")
            sky_note_text = get_note_from_items_local(calculated_cost_items, "스카이 장비")
            if not sky_note_text: # 개별로 나올 경우 각주 조합
                sky_notes_list = []
                if sky_from_val > 0: sky_notes_list.append(get_note_from_items_local(calculated_cost_items, "출발지 스카이 장비"))
                if sky_to_val > 0: sky_notes_list.append(get_note_from_items_local(calculated_cost_items, "도착지 스카이 장비"))
                sky_note_text = ", ".join(filter(None, sky_notes_list))


            storage_fee_summary_val = get_cost_from_items_local(calculated_cost_items, "보관료")
            storage_note_summary_text = get_note_from_items_local(calculated_cost_items, "보관료")
            waste_cost_summary_val = get_cost_from_items_local(calculated_cost_items, "폐기물 처리")
            waste_note_summary_text = get_note_from_items_local(calculated_cost_items, "폐기물 처리")

            route_parts_list = [from_addr_summary_val if from_addr_summary_val else "출발지미입력"]
            if is_storage_move_summary_bool: route_parts_list.append("보관")
            if has_via_point_summary_bool:
                 via_display_text = "경유지"
                 if via_point_location_summary_text and via_point_location_summary_text != '-':
                     via_display_text = f"경유지({via_point_location_summary_text})"
                 route_parts_list.append(via_display_text)
            route_parts_list.append(to_addr_summary_val if to_addr_summary_val else "도착지미입력")
            route_summary_str = " → ".join(route_parts_list)

            st.text(f"{route_summary_str} {vehicle_tonnage_summary_text}")
            st.text("")
            st.text(f"{customer_name_summary_val}")
            st.text(f"{customer_phone_summary_val}")
            st.text("")
            st.text(f"{selected_vehicle_summary_val} / {personnel_str_summary_text}명")
            st.text("")
            st.text(f"출발지: {from_method_summary_text}")
            st.text(f"도착지: {to_method_summary_text}")
            st.text("")
            st.text(f"계약금 {deposit_amount_val_display:,.0f}원 / 잔금 {remaining_balance_display:,.0f}원")
            st.text("")
            st.text(f"총 {total_cost_display:,.0f}원 중")

            extra_moving_fee_val = total_moving_fee_summary_val - base_fare_summary_val
            if abs(total_moving_fee_summary_val) > 0.01:
                if abs(extra_moving_fee_val) > 0.01 :
                    st.text(f"이사비 {total_moving_fee_summary_val:,.0f} (기본 {base_fare_summary_val:,.0f} + 추가 {extra_moving_fee_val:,.0f})")
                else:
                    st.text(f"이사비 {total_moving_fee_summary_val:,.0f} (기본 {base_fare_summary_val:,.0f})")

            if ladder_from_summary_val > 0: st.text(f"출발지 사다리비 {ladder_from_summary_val:,.0f}원")
            if ladder_to_summary_val > 0: st.text(f"도착지 사다리비 {ladder_to_summary_val:,.0f}원")
            if ladder_regional_summary_val > 0: st.text(f"지방 사다리 추가 {ladder_regional_summary_val:,.0f}원")
            if sky_total_val > 0: st.text(f"스카이비 {sky_total_val:,.0f}원 ({sky_note_text})")
            if storage_fee_summary_val > 0: st.text(f"보관료 {storage_fee_summary_val:,.0f}원 ({storage_note_summary_text})")
            if waste_cost_summary_val > 0: st.text(f"폐기물 {waste_cost_summary_val:,.0f}원 ({waste_note_summary_text})")

            st.text("")
            st.text(f"출발지 주소:")
            st.text(f"{from_addr_summary_val}")
            st.text("")

            if is_storage_move_summary_bool:
                storage_name_parts_disp = storage_type_summary_text.split(" ")[:2]
                storage_display_name_text = " ".join(storage_name_parts_disp) if storage_name_parts_disp else "보관이사"
                if not storage_display_name_text.strip() or storage_display_name_text == "보관": storage_display_name_text ="보관이사"
                st.text(f"{storage_display_name_text}")
                if storage_use_electricity_summary_bool:
                    st.text("보관이사 냉장고전기사용")
                st.text("")

            st.text(f"도착지 주소:")
            st.text(f"{to_addr_summary_val}")
            st.text("")

            bask_parts_summary_list = []
            # utils.get_item_qty가 utils 모듈에 확실히 존재하고, data 모듈도 로드되었다고 가정
            if hasattr(utils, 'get_item_qty') and callable(utils.get_item_qty) and data:
                q_basket_val = utils.get_item_qty(st.session_state, "바구니")
                if q_basket_val > 0: bask_parts_summary_list.append(f"바{q_basket_val}")

                q_med_item_name_val = "중박스"
                if hasattr(data, 'items') and "중자바구니" in data.items: q_med_item_name_val = "중자바구니"
                q_med_basket_or_box_val = utils.get_item_qty(st.session_state, q_med_item_name_val)
                if q_med_basket_or_box_val > 0: bask_parts_summary_list.append(f"{q_med_item_name_val[:2]}{q_med_basket_or_box_val}")

                q_book_basket_val = utils.get_item_qty(st.session_state, "책바구니")
                if q_book_basket_val > 0: bask_parts_summary_list.append(f"책{q_book_basket_val}")

            if bask_parts_summary_list:
                st.text(" ".join(bask_parts_summary_list))
            else:
                st.text("선택된 바구니 없음")
            st.text("")

            special_notes_display_text = st.session_state.get('special_notes', '').strip()
            if special_notes_display_text:
                st.text("요구사항:")
                notes_lines_list = [line.strip() for line in special_notes_display_text.split('.') if line.strip()]
                for line_item in notes_lines_list:
                    st.text(line_item)
            else:
                st.text("요구사항: 없음")
            st.divider() # 이사 정보 요약 끝

        except Exception as e_final_quote:
            st.error(f"최종 견적 표시 중 오류 발생: {e_final_quote}")
            traceback.print_exc()
    else: # 차량 미선택 시
        st.warning("최종 차량이 선택되지 않아 견적을 계산할 수 없습니다. 차량을 선택해주세요.")


    # --- Download and Send Buttons ---
    st.subheader("📲 견적서 발송 및 다운로드")

    # 내보내기용 데이터는 st.session_state에서 가져옴 (위에서 계산 후 저장됨)
    export_pdf_args = {
        "state_data": st.session_state.to_dict(),
        "calculated_cost_items": st.session_state.get("calculated_cost_items_for_export", []),
        "total_cost": st.session_state.get("total_cost_for_export", 0),
        "personnel_info": st.session_state.get("personnel_info_for_export", {})
    }
    # 작업 가능 조건: 차량 선택되었고, 비용항목이 있거나 총비용이 0보다 클 때
    can_proceed_with_actions = bool(final_selected_vehicle_for_calc) and \
                               (export_pdf_args["calculated_cost_items"] or export_pdf_args["total_cost"] > 0)


    # MMS 발송 버튼
    mms_available = hasattr(mms_utils, "send_mms_with_image") and callable(mms_utils.send_mms_with_image) and \
                    hasattr(pdf_generator, "generate_pdf") and callable(pdf_generator.generate_pdf) and \
                    hasattr(pdf_generator, "generate_quote_image_from_pdf") and callable(pdf_generator.generate_quote_image_from_pdf)

    if mms_available:
        mms_button_disabled_flag = not can_proceed_with_actions or not st.session_state.get("customer_phone")
        mms_help_text_val = ""
        if not st.session_state.get("customer_phone"): mms_help_text_val = "고객 전화번호 필요"
        elif not can_proceed_with_actions: mms_help_text_val = "견적 내용 확인 필요"

        if st.button("🖼️ 이미지 견적서 MMS 발송", key="mms_send_button_tab3", disabled=mms_button_disabled_flag, help=mms_help_text_val or None):
            customer_phone_for_mms = st.session_state.get("customer_phone")
            customer_name_for_mms = st.session_state.get("customer_name", "고객")

            with st.spinner("견적서 PDF 생성 중..."):
                pdf_bytes_for_mms = pdf_generator.generate_pdf(**export_pdf_args)

            if pdf_bytes_for_mms:
                with st.spinner("PDF를 이미지로 변환 중... (Poppler 필요)"):
                    image_bytes_for_mms = pdf_generator.generate_quote_image_from_pdf(pdf_bytes_for_mms, poppler_path=None) # 시스템 PATH 의존

                if image_bytes_for_mms:
                    with st.spinner(f"{customer_phone_for_mms}으로 MMS 발송 준비 중..."):
                        mms_file_name_text = f"견적서_{customer_name_for_mms}_{utils.get_current_kst_time_str('%Y%m%d')}.jpg"
                        mms_message_text = f"{customer_name_for_mms}님, 요청하신 이사 견적서입니다. 감사합니다."

                        mms_send_success = mms_utils.send_mms_with_image(
                            recipient_phone=customer_phone_for_mms,
                            image_bytes=image_bytes_for_mms,
                            filename=mms_file_name_text,
                            text_message=mms_message_text
                        )
                        if mms_send_success: # 실제 성공 여부는 게이트웨이 응답에 따라 다름
                            st.success(f"{customer_phone_for_mms}으로 견적서 MMS 발송 요청을 완료했습니다.")
                        else:
                            st.error("MMS 발송에 실패했습니다. `mms_utils.py` 및 게이트웨이 설정을 확인해주세요.")
                else:
                    st.error("견적서 이미지 생성에 실패했습니다. Poppler 유틸리티 설치 및 PATH 설정을 확인하세요.")
            else:
                st.error("견적서 PDF 생성에 실패하여 이미지를 만들 수 없습니다.")
    else:
        st.info("MMS 발송 또는 PDF/이미지 생성 기능 중 일부가 로드되지 않았습니다. (mms_utils.py, pdf_generator.py 확인)")


    # PDF 다운로드 버튼
    pdf_generator_available = hasattr(pdf_generator, "generate_pdf") and callable(pdf_generator.generate_pdf)
    pdf_download_disabled_flag = not can_proceed_with_actions
    pdf_dl_help_text = "" if can_proceed_with_actions else "견적 내용 확인 필요"

    if pdf_generator_available:
        if st.button("📄 PDF 견적서 다운로드", key="pdf_customer_download_tab3", disabled=pdf_download_disabled_flag, help=pdf_dl_help_text or None):
            with st.spinner("PDF 생성 중..."):
                pdf_data_for_download = pdf_generator.generate_pdf(**export_pdf_args)
            if pdf_data_for_download:
                st.download_button(
                    label="클릭하여 PDF 다운로드",
                    data=pdf_data_for_download,
                    file_name=f"견적서_{st.session_state.get('customer_name', '고객')}_{utils.get_current_kst_time_str('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("PDF 생성 실패.")
    else:
        st.info("PDF 생성 기능이 로드되지 않았습니다. (pdf_generator.py 확인)")

    # Excel 다운로드 버튼
    excel_filler_available = hasattr(excel_filler, "fill_final_excel_template") and callable(excel_filler.fill_final_excel_template)
    excel_download_disabled_flag = not can_proceed_with_actions
    excel_dl_help_text = "" if can_proceed_with_actions else "견적 내용 확인 필요"

    if excel_filler_available:
        if st.button("📊 Excel 견적서 다운로드 (템플릿 기반)", key="excel_final_download_tab3", disabled=excel_download_disabled_flag, help=excel_dl_help_text or None):
            with st.spinner("Excel 파일 생성 중..."):
                excel_bytes_download = excel_filler.fill_final_excel_template(
                    st.session_state.to_dict(), # 현재 전체 상태
                    export_pdf_args["calculated_cost_items"], # 계산된 비용항목
                    export_pdf_args["total_cost"],           # 계산된 총비용
                    export_pdf_args["personnel_info"]        # 계산된 인력정보
                )
            if excel_bytes_download:
                st.download_button(
                    label="클릭하여 Excel 다운로드",
                    data=excel_bytes_download,
                    file_name=f"최종견적서_{st.session_state.get('customer_name', '고객')}_{utils.get_current_kst_time_str('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Excel 파일 생성 실패.")
    else:
        st.info("Excel 생성 기능이 로드되지 않았습니다. (excel_filler.py 확인)")

    # 이메일 발송 버튼
    email_utils_available = hasattr(email_utils, "send_quote_email") and callable(email_utils.send_quote_email)
    email_button_disabled_flag = not can_proceed_with_actions or not st.session_state.get("customer_email")
    email_help_text_val = ""
    if not st.session_state.get("customer_email"): email_help_text_val = "고객 이메일 필요"
    elif not can_proceed_with_actions: email_help_text_val = "견적 내용 확인 필요"

    if email_utils_available and pdf_generator_available: # PDF 생성 기능도 있어야 함
        if st.button("📧 견적서 이메일 발송", key="email_send_button_tab3", disabled=email_button_disabled_flag, help=email_help_text_val or None):
            recipient_email_addr = st.session_state.get("customer_email")
            customer_name_for_email = st.session_state.get("customer_name", "고객")

            with st.spinner("이메일 발송용 PDF 생성 중..."):
                pdf_bytes_for_email_send = pdf_generator.generate_pdf(**export_pdf_args)

            if pdf_bytes_for_email_send:
                email_subject_text = f"[{customer_name_for_email}님] 이삿날 이사 견적서입니다."
                email_body_text = f"{customer_name_for_email}님,\n\n요청하신 이사 견적서를 첨부 파일로 보내드립니다.\n\n감사합니다.\n이삿날 드림"
                email_pdf_filename = f"견적서_{customer_name_for_email}_{utils.get_current_kst_time_str('%Y%m%d')}.pdf"

                with st.spinner(f"{recipient_email_addr}(으)로 이메일 발송 중..."):
                    email_send_successful = email_utils.send_quote_email(
                        recipient_email_addr,
                        email_subject_text,
                        email_body_text,
                        pdf_bytes_for_email_send,
                        email_pdf_filename
                    )
                if email_send_successful:
                    st.success(f"{recipient_email_addr}(으)로 견적서 이메일 발송 성공!")
                else:
                    st.error("이메일 발송에 실패했습니다. 이메일 설정을 확인하세요.")
            else:
                st.error("첨부할 PDF 파일 생성에 실패하여 이메일을 발송할 수 없습니다.")
    elif not email_utils_available:
        st.info("이메일 발송 기능이 로드되지 않았습니다. (email_utils.py 확인)")
    elif not pdf_generator_available:
        st.info("PDF 생성 기능이 로드되지 않아 이메일 발송을 할 수 없습니다. (pdf_generator.py 확인)")