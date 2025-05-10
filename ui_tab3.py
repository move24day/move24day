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

    critical_modules = ["data", "utils", "calculations", "callbacks", "state_manager"]
    missing_critical = [name for name in critical_modules if name not in globals()]
    if missing_critical:
        st.error(f"UI Tab 3: 필수 핵심 모듈 ({', '.join(missing_critical)}) 로딩 실패. 앱 실행을 중단합니다.")
        st.stop()
    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
        st.warning("MOVE_TYPE_OPTIONS 로드 실패. 기본값을 사용합니다.")

except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 예상치 못한 오류 발생 - {e}")
    traceback.print_exc()
    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""
    # st.write("DEBUG: render_tab3 함수 시작") # 디버깅 메시지

    st.header("💰 계산 및 옵션 ")

    update_basket_quantities_callback = getattr(callbacks, "update_basket_quantities", None)
    sync_move_type_callback = getattr(callbacks, "sync_move_type", None)

    if not callable(update_basket_quantities_callback) or not callable(sync_move_type_callback):
        st.error("UI Tab 3: 콜백 함수(update_basket_quantities 또는 sync_move_type)를 찾을 수 없습니다. callbacks.py를 확인하세요.")

    st.subheader("🏢 이사 유형 ")
    current_move_type_from_state = st.session_state.get("base_move_type")
    move_type_options_local = MOVE_TYPE_OPTIONS

    current_index_tab3 = 0
    if move_type_options_local:
        try:
            current_index_tab3 = move_type_options_local.index(current_move_type_from_state)
        except (ValueError, TypeError):
            current_index_tab3 = 0
            if move_type_options_local:
                 st.session_state.base_move_type = move_type_options_local[0]
                 if "base_move_type_widget_tab1" in st.session_state:
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

    with st.container(border=True):
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget:
            st.radio(
                "차량 선택 방식:",
                ["자동 추천 차량 사용", "수동으로 차량 선택"],
                key="vehicle_select_radio",
                help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.",
                on_change=update_basket_quantities_callback
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
            final_vehicle_from_state_display = st.session_state.get("final_selected_vehicle")
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
                    if recommended_vehicle_from_state and "초과" in recommended_vehicle_from_state: error_msg_auto += f"물량 초과({recommended_vehicle_from_state}). 수동 선택 필요."
                    elif recommended_vehicle_from_state: error_msg_auto += f"추천된 차량({recommended_vehicle_from_state}) 사용 불가. 수동 선택 필요."
                    elif current_total_volume_display > 0 or current_total_weight_display > 0: error_msg_auto += "적합 차량 없음. 수동 선택 필요."
                    else: error_msg_auto += "물품 미선택. 탭2에서 물품 선택 필요."
                    st.error(error_msg_auto)
                    if not available_trucks_for_vehicle_select: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else:
                        current_manual_selection_for_auto_fail = st.session_state.get("manual_vehicle_select_value", available_trucks_for_vehicle_select[0] if available_trucks_for_vehicle_select else None)
                        idx_for_auto_fail = 0
                        if current_manual_selection_for_auto_fail in available_trucks_for_vehicle_select:
                            try: idx_for_auto_fail = available_trucks_for_vehicle_select.index(current_manual_selection_for_auto_fail)
                            except ValueError: idx_for_auto_fail = 0
                        st.selectbox("수동으로 차량 선택:", available_trucks_for_vehicle_select, index=idx_for_auto_fail, key="manual_vehicle_select_value", on_change=update_basket_quantities_callback)
            else:
                if not available_trucks_for_vehicle_select: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection = st.session_state.get("manual_vehicle_select_value", available_trucks_for_vehicle_select[0] if available_trucks_for_vehicle_select else None)
                    current_index_manual = 0
                    if current_manual_selection in available_trucks_for_vehicle_select:
                        try: current_index_manual = available_trucks_for_vehicle_select.index(current_manual_selection)
                        except ValueError: current_index_manual = 0
                    st.selectbox("차량 직접 선택:", available_trucks_for_vehicle_select, index=current_index_manual, key="manual_vehicle_select_value", on_change=update_basket_quantities_callback)
                    if final_vehicle_from_state_display and final_vehicle_from_state_display in available_trucks_for_vehicle_select:
                        st.info(f"ℹ️ 수동 선택됨: **{final_vehicle_from_state_display}**")
                        spec_manual_disp = data.vehicle_specs.get(final_vehicle_from_state_display) if hasattr(data, "vehicle_specs") else None
                        if spec_manual_disp:
                            st.caption(f"선택차량 최대 용량: {spec_manual_disp.get('capacity', 'N/A')}m³, {spec_manual_disp.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {current_total_volume_display:.2f}m³, {current_total_weight_display:.2f}kg")
    st.divider()

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
        st.subheader("🚚 실제 투입 차량 ")
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다. (Excel 출력 등에 사용)")
        st.write("")
        base_w,remove_opt,discount_amount = 0,False,0
        final_vehicle_for_hw = st.session_state.get("final_selected_vehicle")
        current_move_type_for_hw = st.session_state.get("base_move_type")
        if current_move_type_for_hw and hasattr(data, "vehicle_prices") and isinstance(data.vehicle_prices, dict):
            vehicle_prices_options_hw = data.vehicle_prices.get(current_move_type_for_hw, {})
            if final_vehicle_for_hw and final_vehicle_for_hw in vehicle_prices_options_hw:
                base_info_hw = vehicle_prices_options_hw.get(final_vehicle_for_hw, {})
                base_w_raw = base_info_hw.get("housewife")
                try:
                    base_w = int(base_w_raw) if base_w_raw is not None else 0
                    if base_w > 0: remove_opt, add_cost_hw = True, getattr(data, "ADDITIONAL_PERSON_COST", 0); discount_amount = add_cost_hw * base_w if isinstance(add_cost_hw, (int, float)) else 0
                except: base_w = 0
        if remove_opt: st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if "remove_base_housewife" in st.session_state: st.session_state.remove_base_housewife = False
        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
            if st.session_state.get("has_waste_check"):
                waste_cost_per_ton_disp,waste_cost_val_disp = getattr(data, "WASTE_DISPOSAL_COST_PER_TON", 0),0
                if isinstance(waste_cost_per_ton_disp, (int, float)): waste_cost_val_disp = waste_cost_per_ton_disp
                st.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5