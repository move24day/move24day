# ui_tab3.py
# ui_tab3.py (이사 정보 요약 형식 최종 조정)
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
    import pdf_generator
    import excel_filler
    import email_utils # 사용자 제공 email_utils 임포트
    # Ensure callbacks is imported to access its functions
    import callbacks 
    from state_manager import MOVE_TYPE_OPTIONS # state_manager에서 가져오도록 수정
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    if hasattr(e, "name") and e.name == "email_utils":
        st.warning("email_utils.py 파일이 없거나 로드할 수 없습니다. 이메일 발송 기능이 비활성화됩니다.")
    # Ensure MOVE_TYPE_OPTIONS has a fallback if state_manager fails to provide it
    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] 
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 예상치 못한 오류 발생 - {e}")
    traceback.print_exc()
    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] 
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션 ")
    
    # Ensure callbacks.update_basket_quantities and callbacks.sync_move_type are available
    update_basket_quantities_callback = getattr(callbacks, "update_basket_quantities", None)
    sync_move_type_callback = getattr(callbacks, "sync_move_type", None)

    if not callable(update_basket_quantities_callback) or not callable(sync_move_type_callback):
        st.error("UI Tab 3: 콜백 함수(update_basket_quantities 또는 sync_move_type)를 찾을 수 없습니다. callbacks.py를 확인하세요.")
        # return # Stop rendering if critical callbacks are missing

    # --- Move Type Selection (Tab 3) ---
    st.subheader("🏢 이사 유형 ")
    current_move_type = st.session_state.get("base_move_type")
    # Use MOVE_TYPE_OPTIONS directly as it should be defined globally or imported
    move_type_options_local = MOVE_TYPE_OPTIONS 

    current_index_tab3 = 0
    if move_type_options_local:
        try:
            current_index_tab3 = move_type_options_local.index(current_move_type)
        except (ValueError, TypeError):
            current_index_tab3 = 0
            if current_move_type not in move_type_options_local and move_type_options_local:
                 st.session_state.base_move_type = move_type_options_local[0]
                 # print("Warning: Resetting base_move_type in Tab 3 due to invalid state.")
                 if "base_move_type_widget_tab1" in st.session_state:
                      st.session_state.base_move_type_widget_tab1 = move_type_options_local[0]
    else:
        st.error("이사 유형 옵션(MOVE_TYPE_OPTIONS)을 불러올 수 없습니다.")
        return

    st.radio(
        "기본 이사 유형:",
        options=move_type_options_local, index=current_index_tab3, horizontal=True,
        key="base_move_type_widget_tab3", 
        on_change=sync_move_type_callback, # Use the fetched callback
        args=("base_move_type_widget_tab3",)
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
                on_change=update_basket_quantities_callback # Use the fetched callback
            )

        with col_v2_widget:
            current_move_type_widget = st.session_state.get("base_move_type")
            vehicle_prices_options_widget = {}
            available_trucks_widget = []

            if current_move_type_widget and hasattr(data, "vehicle_prices") and isinstance(data.vehicle_prices, dict):
                vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})

            if vehicle_prices_options_widget and hasattr(data, "vehicle_specs") and isinstance(data.vehicle_specs, dict):
                available_trucks_widget = sorted(
                    [truck for truck in vehicle_prices_options_widget.keys() if truck in data.vehicle_specs],
                    key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0)
                )

            use_auto_widget = st.session_state.get("vehicle_select_radio") == "자동 추천 차량 사용"
            # These are the direct states updated by callbacks
            recommended_vehicle_auto_from_state = st.session_state.get("recommended_vehicle_auto")
            final_vehicle_from_state = st.session_state.get("final_selected_vehicle")
            current_total_volume = st.session_state.get("total_volume", 0.0)
            current_total_weight = st.session_state.get("total_weight", 0.0)

            if use_auto_widget:
                # Check if final_selected_vehicle (which should be the recommended one if valid) is set and available
                if final_vehicle_from_state and final_vehicle_from_state in available_trucks_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_from_state}**")
                    spec = data.vehicle_specs.get(final_vehicle_from_state) if hasattr(data, "vehicle_specs") else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get("capacity", "N/A")}m³, {spec.get("weight_capacity", "N/A"):,}kg")
                        st.caption(f"현재 이사짐 예상: {current_total_volume:.2f}m³, {current_total_weight:.2f}kg")
                else: # Auto-selection failed or recommended vehicle is not available/valid
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_from_state and "초과" in recommended_vehicle_auto_from_state:
                        error_msg += f"물량 초과({recommended_vehicle_auto_from_state}). 수동 선택 필요."
                    elif recommended_vehicle_auto_from_state: # A specific vehicle was recommended by calculations
                        # This case means recommended_vehicle_auto_from_state was set, but it didn't become final_vehicle_from_state
                        # (e.g. not in available_trucks_widget)
                        error_msg += f"추천된 차량({recommended_vehicle_auto_from_state})은 현재 이사 유형에 없거나 사용할 수 없습니다. 수동 선택 필요."
                    elif current_total_volume > 0 or current_total_weight > 0:
                        # Items are selected, but no recommendation could be made (e.g. calculations.recommend_vehicle returned None)
                        error_msg += "적합한 차량을 찾을 수 없거나 계산/정보 부족. 수동 선택 필요."
                    else:
                        # No items selected, hence no volume/weight, and no recommendation
                        error_msg += "물품 미선택. 탭2에서 물품을 선택해주세요."
                    st.error(error_msg)

                    # Offer manual selection if auto fails
                    if not available_trucks_widget: 
                        st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else:
                        current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                        current_index_widget = 0
                        if current_manual_selection_widget in available_trucks_widget:
                            try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                            except ValueError: current_index_widget = 0
                        elif available_trucks_widget: # Default to first if no valid current selection
                            st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                        
                        st.selectbox(
                            "수동으로 차량 선택:",
                            available_trucks_widget, index=current_index_widget,
                            key="manual_vehicle_select_value",
                            on_change=update_basket_quantities_callback # Use the fetched callback
                        )
                        # Display manually selected vehicle info if one is made through this fallback
                        manual_selected_display_fallback = st.session_state.get("final_selected_vehicle")
                        if st.session_state.get("vehicle_select_radio") == "자동 추천 차량 사용" and manual_selected_display_fallback and manual_selected_display_fallback in available_trucks_widget:
                            # This condition is tricky, means auto failed, and user might pick one here
                            # The display of this info might be better handled by the main manual selection block if radio changes
                            pass 

            else: # Manual selection mode
                if not available_trucks_widget: 
                    st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    current_index_widget = 0
                    if current_manual_selection_widget in available_trucks_widget:
                        try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError: current_index_widget = 0
                    elif available_trucks_widget: # Default to first if no valid current selection
                         st.session_state.manual_vehicle_select_value = available_trucks_widget[0]

                    st.selectbox(
                        "차량 직접 선택:",
                        available_trucks_widget, index=current_index_widget,
                        key="manual_vehicle_select_value",
                        on_change=update_basket_quantities_callback # Use the fetched callback
                    )
                    manual_selected_display = st.session_state.get("final_selected_vehicle")
                    if manual_selected_display and manual_selected_display in available_trucks_widget:
                        st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                        spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, "vehicle_specs") else None
                        if spec_manual:
                            st.caption(f"선택차량 최대 용량: {spec_manual.get("capacity", "N/A")}m³, {spec_manual.get("weight_capacity", "N/A"):,}kg")
                            st.caption(f"현재 이사짐 예상: {current_total_volume:.2f}m³, {current_total_weight:.2f}kg")
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

        st.subheader("🚚 실제 투입 차량 ")
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.")
        st.write("")

        base_w = 0
        remove_opt = False
        discount_amount = 0
        final_vehicle_for_options = st.session_state.get("final_selected_vehicle")
        current_move_type_options = st.session_state.get("base_move_type")

        if current_move_type_options and hasattr(data, "vehicle_prices") and isinstance(data.vehicle_prices, dict):
            vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})
            if final_vehicle_for_options and final_vehicle_for_options in vehicle_prices_options_display:
                base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {})
                base_w_raw = base_info.get("housewife")
                try:
                    base_w = int(base_w_raw) if base_w_raw is not None else 0
                    if base_w > 0:
                         remove_opt = True
                         add_cost = getattr(data, "ADDITIONAL_PERSON_COST", 0)
                         if isinstance(add_cost, (int, float)):
                             discount_amount = add_cost * base_w
                         else:
                             st.warning("data.ADDITIONAL_PERSON_COST가 숫자가 아닙니다. 할인 금액이 0으로 처리됩니다.")
                             discount_amount = 0
                except (ValueError, TypeError):
                     base_w = 0
                     # print(f"Warning: Non-numeric \'housewife\' value encountered: {base_w_raw}")

        if remove_opt:
            st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if "remove_base_housewife" in st.session_state:
                st.session_state.remove_base_housewife = False

        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
            if st.session_state.get("has_waste_check"):
                waste_cost_per_ton = getattr(data, "WASTE_DISPOSAL_COST_PER_TON", 0)
                waste_cost_display = 0
                if isinstance(waste_cost_per_ton, (int, float)):
                    waste_cost_display = waste_cost_per_ton
                else:
                    st.warning("data.WASTE_DISPOSAL_COST_PER_TON 정의 오류.")
                st.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input", format="%.1f")
                if waste_cost_display > 0:
                    st.caption(f"💡 1톤당 {waste_cost_display:,}원 추가 비용 발생")

        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_surcharges_defined = hasattr(data, "special_day_prices") and isinstance(data.special_day_prices, dict)
        if not date_surcharges_defined:
            st.warning("data.py에 날짜 할증(special_day_prices) 정보가 없습니다.")

        date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            with cols_date[i]:
                 surcharge_amount = 0
                 if date_surcharges_defined:
                     surcharge_amount = data.special_day_prices.get(option, 0)
                 help_text = f"{surcharge_amount:,}원 할증" if surcharge_amount > 0 else ""
                 st.checkbox(option, key=date_keys[i], help=help_text)
    st.divider()

    # --- Cost Adjustment & Deposit ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        num_cols_cost_adj = 3
        if st.session_state.get("has_via_point"):
            num_cols_cost_adj = 4

        cols_adj = st.columns(num_cols_cost_adj)
        with cols_adj[0]: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with cols_adj[1]: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with cols_adj[2]: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
        if st.session_state.get("has_via_point"):
            with cols_adj[3]: st.number_input("↪️ 경유지 추가요금", min_value=0, step=10000, key="via_point_surcharge", format="%d", help="경유지 작업으로 인해 발생하는 추가 요금")
    st.divider()

    # --- Final Quote Results ---
    st.header("💵 최종 견적 결과")

    final_selected_vehicle_calc = st.session_state.get("final_selected_vehicle")
    total_cost = 0
    cost_items = []
    personnel_info = {}
    # has_cost_error = False # This variable was unused

    if final_selected_vehicle_calc:
        try:
            if st.session_state.get("is_storage_move"):
                moving_dt_recalc = st.session_state.get("moving_date")
                arrival_dt_recalc = st.session_state.get("arrival_date")
                if isinstance(moving_dt_recalc, date) and isinstance(arrival_dt_recalc, date) and arrival_dt_recalc >= moving_dt_recalc:
                    delta_recalc = arrival_dt_recalc - moving_dt_recalc
                    st.session_state.storage_duration = max(1, delta_recalc.days + 1)
                else:
                    st.session_state.storage_duration = 1 # Default if dates are invalid

            current_state_dict = st.session_state.to_dict()
            # Ensure calculations module and its function are available
            if hasattr(calculations, "calculate_total_moving_cost") and callable(calculations.calculate_total_moving_cost):
                total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)
            else:
                st.error("최종 비용 계산 함수를 찾을 수 없습니다. calculations.py를 확인하세요.")
                total_cost, cost_items, personnel_info = 0, [], {}

            total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
            deposit_amount_val = st.session_state.get("deposit_amount", 0)
            try: deposit_amount_num = int(deposit_amount_val)
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            # Check for error items (e.g., strings indicating issues)
            error_item_found = next((item_detail for item_detail in cost_items if isinstance(item_detail, str)), None)
            if error_item_found:
                st.error(f"비용 계산 중 오류 발생: {error_item_found}")
            else:
                cost_df = pd.DataFrame(cost_items)
                if not cost_df.empty:
                    cost_df.columns = ["항목", "비용"]
                    cost_df["비용"] = cost_df["비용"].apply(lambda x: f"{int(x):,} 원" if isinstance(x, (int, float)) else x)
                    st.table(cost_df.set_index("항목"))
                else:
                    st.info("산출된 비용 내역이 없습니다.")

            st.subheader("👥 투입 인력 정보")
            if personnel_info and isinstance(personnel_info, dict) and any(personnel_info.values()):
                personnel_df = pd.DataFrame(list(personnel_info.items()), columns=["직책", "인원수"])
                personnel_df = personnel_df[personnel_df["인원수"] > 0] # Show only if count > 0
                if not personnel_df.empty:
                    st.table(personnel_df.set_index("직책"))
                else:
                    st.info("산출된 투입 인력 정보가 없습니다.") 
            else:
                st.info("산출된 투입 인력 정보가 없습니다.")

        except Exception as e_cost:
            st.error(f"최종 견적 표시 중 오류 발생: {e_cost}")
            traceback.print_exc()
    else:
        st.warning("최종 차량이 선택되지 않아 견적을 계산할 수 없습니다. 차량을 선택해주세요.")

    # --- Download Buttons ---
    st.subheader("📄 견적서 다운로드")
    # ... (rest of the download logic remains the same)
    # Ensure pdf_generator and excel_filler are used correctly
    # For example, for PDF:
    if st.button("고객용 PDF 견적서 다운로드", key="pdf_customer_download"):
        if hasattr(pdf_generator, "create_pdf_for_customer") and callable(pdf_generator.create_pdf_for_customer):
            pdf_data_cust = pdf_generator.create_pdf_for_customer(st.session_state.to_dict(), data, calculations, utils)
            if pdf_data_cust:
                st.download_button(
                    label="다운로드 준비 완료 (고객용 PDF)",
                    data=pdf_data_cust,
                    file_name=f"견적서_고객용_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("고객용 PDF 생성 실패.")
        else:
            st.error("PDF 생성 함수(create_pdf_for_customer)를 찾을 수 없습니다.")

    # Similar checks for other download buttons...
    if st.button("내부용 PDF 견적서 다운로드", key="pdf_internal_download"):
        if hasattr(pdf_generator, "create_pdf_for_internal") and callable(pdf_generator.create_pdf_for_internal):
            pdf_data_int = pdf_generator.create_pdf_for_internal(st.session_state.to_dict(), data, calculations, utils)
            if pdf_data_int:
                st.download_button(
                    label="다운로드 준비 완료 (내부용 PDF)",
                    data=pdf_data_int,
                    file_name=f"견적서_내부용_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("내부용 PDF 생성 실패.")
        else:
            st.error("PDF 생성 함수(create_pdf_for_internal)를 찾을 수 없습니다.")

    if st.button("Excel 견적서 다운로드", key="excel_download"):
        if hasattr(excel_filler, "fill_excel_template") and callable(excel_filler.fill_excel_template):
            excel_bytes = excel_filler.fill_excel_template(st.session_state.to_dict(), data, calculations, utils)
            if excel_bytes:
                st.download_button(
                    label="다운로드 준비 완료 (Excel)",
                    data=excel_bytes,
                    file_name=f"견적서_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Excel 파일 생성 실패.")
        else:
            st.error("Excel 생성 함수(fill_excel_template)를 찾을 수 없습니다.")

    # Email sending logic (ensure email_utils is available and function exists)
    if hasattr(email_utils, "send_email_with_attachments") and callable(email_utils.send_email_with_attachments):
        if st.button("견적서 이메일 발송", key="email_send_button"):
            # Generate PDFs first
            pdf_customer_bytes = pdf_generator.create_pdf_for_customer(st.session_state.to_dict(), data, calculations, utils) if hasattr(pdf_generator, "create_pdf_for_customer") else None
            pdf_internal_bytes = pdf_generator.create_pdf_for_internal(st.session_state.to_dict(), data, calculations, utils) if hasattr(pdf_generator, "create_pdf_for_internal") else None
            
            attachments = []
            if pdf_customer_bytes:
                attachments.append({
                    "filename": f"견적서_고객용_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.pdf",
                    "content": pdf_customer_bytes,
                    "mimetype": "application/pdf"
                })
            if pdf_internal_bytes:
                 attachments.append({
                    "filename": f"견적서_내부용_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.pdf",
                    "content": pdf_internal_bytes,
                    "mimetype": "application/pdf"
                })

            if attachments:
                recipient_email = st.session_state.get("customer_email")
                if recipient_email:
                    subject = f"[{st.session_state.get("customer_name", "고객") }님] 이사 견적서입니다."
                    body = f"{st.session_state.get("customer_name", "고객")}님, 요청하신 이사 견적서를 첨부 파일로 보내드립니다.\n\n감사합니다."
                    try:
                        email_utils.send_email_with_attachments(recipient_email, subject, body, attachments)
                        st.success(f"{recipient_email}로 견적서 이메일 발송 성공!")
                    except Exception as email_exc:
                        st.error(f"이메일 발송 실패: {email_exc}")
                else:
                    st.warning("고객 이메일 주소가 입력되지 않았습니다.")
            else:
                st.error("첨부할 PDF 파일 생성에 실패하여 이메일을 발송할 수 없습니다.")
    else:
        st.info("이메일 발송 기능이 로드되지 않았습니다. email_utils.py를 확인하세요.")

