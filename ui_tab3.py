# ui_tab3.py
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
    from state_manager import MOVE_TYPE_OPTIONS
    import mms_utils # mms_utils 임포트
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    if hasattr(e, "name"):
        if e.name == "email_utils":
            st.warning("email_utils.py 파일이 없거나 로드할 수 없습니다. 이메일 발송 기능이 비활성화됩니다.")
        elif e.name == "mms_utils":
            st.warning("mms_utils.py 파일이 없거나 로드할 수 없습니다. MMS 발송 기능이 비활성화됩니다.")
        elif e.name == "pdf_generator":
            st.error("pdf_generator.py 파일이 없거나 로드할 수 없습니다. PDF/이미지 생성 기능이 비활성화됩니다.")
            st.stop()


    if "MOVE_TYPE_OPTIONS" not in globals():
        MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"] 
    # pdf_generator가 없으면 중단할 수 있도록 처리
    if not all(module_name in globals() for module_name in ["data", "utils", "calculations", "callbacks", "state_manager"]):
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
    
    update_basket_quantities_callback = getattr(callbacks, "update_basket_quantities", None)
    sync_move_type_callback = getattr(callbacks, "sync_move_type", None)

    if not callable(update_basket_quantities_callback) or not callable(sync_move_type_callback):
        st.error("UI Tab 3: 콜백 함수(update_basket_quantities 또는 sync_move_type)를 찾을 수 없습니다. callbacks.py를 확인하세요.")

    # --- Move Type Selection (Tab 3) ---
    # (기존 코드 유지)
    st.subheader("🏢 이사 유형 ")
    current_move_type = st.session_state.get("base_move_type")
    move_type_options_local = MOVE_TYPE_OPTIONS 

    current_index_tab3 = 0
    if move_type_options_local:
        try:
            current_index_tab3 = move_type_options_local.index(current_move_type)
        except (ValueError, TypeError):
            current_index_tab3 = 0
            if current_move_type not in move_type_options_local and move_type_options_local:
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
        args=("base_move_type_widget_tab3",)
    )
    st.divider()

    # --- Vehicle Selection ---
    # (기존 코드 유지)
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
            recommended_vehicle_auto_from_state = st.session_state.get("recommended_vehicle_auto")
            final_vehicle_from_state = st.session_state.get("final_selected_vehicle")
            current_total_volume = st.session_state.get("total_volume", 0.0)
            current_total_weight = st.session_state.get("total_weight", 0.0)

            if use_auto_widget:
                if final_vehicle_from_state and final_vehicle_from_state in available_trucks_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_from_state}**")
                    spec = data.vehicle_specs.get(final_vehicle_from_state) if hasattr(data, "vehicle_specs") else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get("capacity", "N/A")}m³, {spec.get("weight_capacity", "N/A"):,}kg")
                        st.caption(f"현재 이사짐 예상: {current_total_volume:.2f}m³, {current_total_weight:.2f}kg")
                else: 
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_from_state and "초과" in recommended_vehicle_auto_from_state:
                        error_msg += f"물량 초과({recommended_vehicle_auto_from_state}). 수동 선택 필요."
                    elif recommended_vehicle_auto_from_state: 
                        error_msg += f"추천된 차량({recommended_vehicle_auto_from_state})은 현재 이사 유형에 없거나 사용할 수 없습니다. 수동 선택 필요."
                    elif current_total_volume > 0 or current_total_weight > 0:
                        error_msg += "적합한 차량을 찾을 수 없거나 계산/정보 부족. 수동 선택 필요."
                    else:
                        error_msg += "물품 미선택. 탭2에서 물품을 선택해주세요."
                    st.error(error_msg)

                    if not available_trucks_widget: 
                        st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else:
                        current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                        current_index_widget = 0
                        if current_manual_selection_widget in available_trucks_widget:
                            try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                            except ValueError: current_index_widget = 0
                        elif available_trucks_widget: 
                            st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                        
                        st.selectbox(
                            "수동으로 차량 선택:",
                            available_trucks_widget, index=current_index_widget,
                            key="manual_vehicle_select_value",
                            on_change=update_basket_quantities_callback 
                        )
            else: # Manual selection mode
                if not available_trucks_widget: 
                    st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    current_index_widget = 0
                    if current_manual_selection_widget in available_trucks_widget:
                        try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError: current_index_widget = 0
                    elif available_trucks_widget: 
                         st.session_state.manual_vehicle_select_value = available_trucks_widget[0]

                    st.selectbox(
                        "차량 직접 선택:",
                        available_trucks_widget, index=current_index_widget,
                        key="manual_vehicle_select_value",
                        on_change=update_basket_quantities_callback 
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
    # (기존 코드 유지)
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
    # (기존 코드 유지)
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

    if final_selected_vehicle_calc:
        try:
            if st.session_state.get("is_storage_move"):
                moving_dt_recalc = st.session_state.get("moving_date")
                arrival_dt_recalc = st.session_state.get("arrival_date")
                if isinstance(moving_dt_recalc, date) and isinstance(arrival_dt_recalc, date) and arrival_dt_recalc >= moving_dt_recalc:
                    delta_recalc = arrival_dt_recalc - moving_dt_recalc
                    st.session_state.storage_duration = max(1, delta_recalc.days + 1)
                else:
                    st.session_state.storage_duration = 1 

            current_state_dict = st.session_state.to_dict()
            if hasattr(calculations, "calculate_total_moving_cost") and callable(calculations.calculate_total_moving_cost):
                total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)
                # PDF/이미지 생성을 위해 세션 상태에 저장
                st.session_state.calculated_cost_items_for_pdf = cost_items
                st.session_state.total_cost_for_pdf = total_cost
                st.session_state.personnel_info_for_pdf = personnel_info
            else:
                st.error("최종 비용 계산 함수를 찾을 수 없습니다. calculations.py를 확인하세요.")
                total_cost, cost_items, personnel_info = 0, [], {}
                st.session_state.calculated_cost_items_for_pdf = []
                st.session_state.total_cost_for_pdf = 0
                st.session_state.personnel_info_for_pdf = {}


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
            error_item_found = next((item_detail for item_detail in cost_items if isinstance(item_detail, str)), None)
            if error_item_found:
                st.error(f"비용 계산 중 오류 발생: {error_item_found}")
            else:
                cost_df = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"] if cost_items and len(cost_items[0]) == 3 else ["항목", "금액"])
                if not cost_df.empty:
                    if "금액" in cost_df.columns:
                         cost_df["금액"] = cost_df["금액"].apply(lambda x: f"{int(x):,} 원" if isinstance(x, (int, float)) else x)
                    st.table(cost_df.set_index("항목"))
                else:
                    st.info("산출된 비용 내역이 없습니다.")

            st.subheader("👥 투입 인력 정보")
            if personnel_info and isinstance(personnel_info, dict) and any(personnel_info.values()):
                # personnel_info의 키를 "표시명"으로 바꾸고, 값은 "인원수"로 하는 DataFrame 생성
                display_personnel_info = {
                    "기본 남성 인력": personnel_info.get('base_men', 0),
                    "기본 여성 인력": personnel_info.get('base_women', 0),
                    "수동 추가 남성": personnel_info.get('manual_added_men', 0),
                    "수동 추가 여성": personnel_info.get('manual_added_women', 0),
                    "최종 투입 남성": personnel_info.get('final_men', 0),
                    "최종 투입 여성": personnel_info.get('final_women', 0),
                }
                personnel_df_data = [(k,v) for k,v in display_personnel_info.items() if v > 0] # 인원수가 0보다 큰 경우만 표시
                if personnel_df_data:
                    personnel_df = pd.DataFrame(personnel_df_data, columns=["직책", "인원수"])
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

    # --- Download and Send Buttons ---
    st.subheader("📲 견적서 발송 및 다운로드")
    
    # PDF 생성에 필요한 데이터 (위에서 계산된 값을 사용)
    pdf_args = {
        "state_data": st.session_state.to_dict(),
        "calculated_cost_items": st.session_state.get("calculated_cost_items_for_pdf", []),
        "total_cost": st.session_state.get("total_cost_for_pdf", 0),
        "personnel_info": st.session_state.get("personnel_info_for_pdf", {})
    }

    # --- MMS 발송 버튼 ---
    if hasattr(mms_utils, "send_mms_with_image") and callable(mms_utils.send_mms_with_image) and \
       hasattr(pdf_generator, "generate_pdf") and callable(pdf_generator.generate_pdf) and \
       hasattr(pdf_generator, "generate_quote_image_from_pdf") and callable(pdf_generator.generate_quote_image_from_pdf):

        if st.button("🖼️ 이미지 견적서 MMS 발송", key="mms_send_button"):
            customer_phone = st.session_state.get("customer_phone")
            customer_name = st.session_state.get("customer_name", "고객")

            if not customer_phone:
                st.warning("고객 휴대폰 번호가 입력되지 않았습니다 (고객 정보 탭에서 입력).")
            elif not pdf_args["calculated_cost_items"] and pdf_args["total_cost"] == 0 : # 비용계산이 안된 경우
                st.warning("견적 내용이 없습니다. 품목 선택 및 차량 선택 후 비용 계산이 완료되어야 합니다.")
            else:
                with st.spinner("견적서 PDF 생성 중..."):
                    pdf_bytes = pdf_generator.generate_pdf(**pdf_args)

                if pdf_bytes:
                    with st.spinner("PDF를 이미지로 변환 중... (Poppler 필요)"):
                        # Poppler 경로를 환경에 맞게 설정해야 할 수 있습니다.
                        # 예: poppler_path = r"C:\path\to\poppler-xx.xx.x\bin" (Windows)
                        # 현재는 None으로 두어 시스템 PATH에서 찾도록 합니다.
                        image_bytes = pdf_generator.generate_quote_image_from_pdf(pdf_bytes, poppler_path=None) 
                    
                    if image_bytes:
                        with st.spinner(f"{customer_phone}으로 MMS 발송 준비 중..."):
                            mms_filename = f"견적서_{customer_name}_{utils.get_current_kst_time_str('%Y%m%d')}.jpg"
                            mms_text_message = f"{customer_name}님, 요청하신 이사 견적서입니다. 감사합니다."
                            
                            mms_sent = mms_utils.send_mms_with_image(
                                recipient_phone=customer_phone,
                                image_bytes=image_bytes,
                                filename=mms_filename,
                                text_message=mms_text_message
                            )
                            if mms_sent: # 실제 발송 성공 여부는 mms_utils 구현에 따름
                                st.success(f"{customer_phone}으로 견적서 MMS 발송 요청을 완료했습니다. (실제 발송은 게이트웨이 설정 및 응답에 따라 달라집니다)")
                            else:
                                st.error("MMS 발송에 실패했습니다. `mms_utils.py`의 실제 구현 및 MMS 게이트웨이 설정을 확인해주세요.")
                    else:
                        st.error("견적서 이미지 생성에 실패했습니다. Poppler 유틸리티가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.")
                else:
                    st.error("견적서 PDF 생성에 실패하여 이미지를 만들 수 없습니다.")
    else:
        st.info("MMS 발송 또는 PDF/이미지 생성 기능 중 일부가 로드되지 않았습니다. `mms_utils.py` 또는 `pdf_generator.py`를 확인하세요.")


    # --- 기존 다운로드 버튼들 ---
    # PDF 다운로드
    if hasattr(pdf_generator, "generate_pdf") and callable(pdf_generator.generate_pdf):
        if st.button("📄 PDF 견적서 다운로드", key="pdf_customer_download"):
            if not pdf_args["calculated_cost_items"] and pdf_args["total_cost"] == 0 :
                 st.warning("견적 내용이 없어 PDF를 생성할 수 없습니다.")
            else:
                with st.spinner("PDF 생성 중..."):
                    pdf_data_cust = pdf_generator.generate_pdf(**pdf_args)
                if pdf_data_cust:
                    st.download_button(
                        label="클릭하여 PDF 다운로드",
                        data=pdf_data_cust,
                        file_name=f"견적서_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("PDF 생성 실패.")
    else:
        st.info("PDF 생성 기능이 로드되지 않았습니다. `pdf_generator.py`를 확인하세요.")

    # Excel 다운로드 (기존 excel_filler.fill_final_excel_template 사용)
    if hasattr(excel_filler, "fill_final_excel_template") and callable(excel_filler.fill_final_excel_template):
        if st.button("📊 Excel 견적서 다운로드 (템플릿 기반)", key="excel_final_download"):
            if not pdf_args["calculated_cost_items"] and pdf_args["total_cost"] == 0 :
                 st.warning("견적 내용이 없어 Excel 파일을 생성할 수 없습니다.")
            else:
                with st.spinner("Excel 파일 생성 중..."):
                    excel_bytes = excel_filler.fill_final_excel_template(
                        st.session_state.to_dict(), 
                        pdf_args["calculated_cost_items"], # 이미 계산된 cost_items 사용
                        pdf_args["total_cost"],           # 이미 계산된 total_cost 사용
                        pdf_args["personnel_info"]        # 이미 계산된 personnel_info 사용
                    )
                if excel_bytes:
                    st.download_button(
                        label="클릭하여 Excel 다운로드",
                        data=excel_bytes,
                        file_name=f"최종견적서_{st.session_state.get("customer_name", "고객")}_{utils.get_current_kst_time_str("%Y%m%d")}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("Excel 파일 생성 실패.")
    else:
        st.info("Excel 생성 기능(fill_final_excel_template)이 로드되지 않았습니다. `excel_filler.py`를 확인하세요.")
    
    # 이메일 발송 (기존 로직 유지, pdf_generator.generate_pdf 사용)
    if hasattr(email_utils, "send_quote_email") and callable(email_utils.send_quote_email) and \
       hasattr(pdf_generator, "generate_pdf") and callable(pdf_generator.generate_pdf):
        if st.button("📧 견적서 이메일 발송", key="email_send_button"):
            recipient_email = st.session_state.get("customer_email")
            customer_name = st.session_state.get("customer_name", "고객")

            if not recipient_email:
                st.warning("고객 이메일 주소가 입력되지 않았습니다 (고객 정보 탭에서 입력).")
            elif not pdf_args["calculated_cost_items"] and pdf_args["total_cost"] == 0 :
                 st.warning("견적 내용이 없어 이메일을 발송할 수 없습니다.")
            else:
                with st.spinner("이메일 발송용 PDF 생성 중..."):
                    pdf_email_bytes = pdf_generator.generate_pdf(**pdf_args)
                
                if pdf_email_bytes:
                    subject = f"[{customer_name}님] 이삿날 이사 견적서입니다."
                    body = f"{customer_name}님,\n\n요청하신 이사 견적서를 첨부 파일로 보내드립니다.\n\n감사합니다.\n이삿날 드림"
                    pdf_filename = f"견적서_{customer_name}_{utils.get_current_kst_time_str('%Y%m%d')}.pdf"
                    
                    with st.spinner(f"{recipient_email}(으)로 이메일 발송 중..."):
                        email_sent = email_utils.send_quote_email(recipient_email, subject, body, pdf_email_bytes, pdf_filename)
                    
                    if email_sent:
                        st.success(f"{recipient_email}(으)로 견적서 이메일 발송 성공!")
                    else:
                        st.error("이메일 발송에 실패했습니다. 이메일 설정을 확인하세요.")
                else:
                    st.error("첨부할 PDF 파일 생성에 실패하여 이메일을 발송할 수 없습니다.")
    else:
        st.info("이메일 발송 또는 PDF 생성 기능 중 일부가 로드되지 않았습니다. `email_utils.py` 또는 `pdf_generator.py`를 확인하세요.")

