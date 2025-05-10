# ui_tab3.py
# ui_tab3.py (실제 투입 차량 정보 입력란 완전 삭제)
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
            st.write("") # Add spacing after sky hours if they are shown

        col_add1, col_add2 = st.columns(2)
        with col_add1: st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2: st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        
        # "실제 투입 차량" 섹션 완전 삭제
        
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
        
        if remove_opt: 
            st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if "remove_base_housewife" in st.session_state: 
                st.session_state.remove_base_housewife = False
        
        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: 
            st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
            if st.session_state.get("has_waste_check"):
                waste_cost_per_ton_disp,waste_cost_val_disp = getattr(data, "WASTE_DISPOSAL_COST_PER_TON", 0),0
                if isinstance(waste_cost_per_ton_disp, (int, float)): waste_cost_val_disp = waste_cost_per_ton_disp
                st.number_input(
                    "폐기물 양 (톤)", 
                    min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input",
                    help=f"톤당 처리 비용: {waste_cost_val_disp:,.0f}원"
                )
        st.write("")

        st.markdown("##### **🗓️ 이사일 특수조건 할증 (선택 시 자동 합산)**")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_cols = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            surcharge_val = data.special_day_prices.get(option, 0) if hasattr(data, "special_day_prices") else 0
            date_cols[i].checkbox(
                f"{option.split(' ')[0]} (+{surcharge_val:,.0f})", # 공백 뒤 아이콘 제외하고 표시
                key=f"date_opt_{i}_widget",
                help=f"{option} 선택 시 {surcharge_val:,.0f}원 할증"
            )
        st.write("") # Add spacing after date options

        st.number_input("지방 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", help="지방으로 이동 시 사다리차 사용에 대한 추가 요금입니다.")
        if st.session_state.get("has_via_point"):
            st.number_input("경유지 추가 요금", min_value=0, step=10000, key="via_point_surcharge", help="경유지 작업에 대한 추가 요금입니다.")

    st.divider()

    # --- Cost Calculation Display ---
    with st.container(border=True):
        st.subheader("📊 최종 견적 비용")
        calculated_total_cost, cost_breakdown_items, personnel_summary = calculations.calculate_total_moving_cost(st.session_state.to_dict())

        if not st.session_state.get("final_selected_vehicle"):
            st.error("⚠️ 차량이 선택되지 않아 정확한 비용 계산이 불가능합니다. 차량을 선택해주세요.")
        else:
            cost_df_data = []
            for item_desc, item_cost, item_note in cost_breakdown_items:
                cost_df_data.append({
                    "항목": item_desc,
                    "금액": f"{item_cost:,.0f} 원",
                    "비고": item_note
                })
            
            cost_df = pd.DataFrame(cost_df_data)
            st.dataframe(cost_df, hide_index=True, use_container_width=True)

            st.markdown(f"#### **총 예상 비용 (VAT 별도): <span style='color:blue; float:right;'>{calculated_total_cost:,.0f} 원</span>**", unsafe_allow_html=True)

            cols_final_cost = st.columns(2)
            with cols_final_cost[0]:
                st.number_input("계약금 (선금)", min_value=0, step=10000, key="deposit_amount", help="계약 시 지불하는 금액입니다.")
            with cols_final_cost[1]:
                st.number_input("금액 조정 (+/-)", step=1000, key="adjustment_amount", help="최종 견적에서 추가 할증 또는 할인 금액을 입력합니다. (예: -50000)")

            final_display_cost = calculated_total_cost + st.session_state.get("adjustment_amount", 0)
            balance_due = final_display_cost - st.session_state.get("deposit_amount", 0)
            
            st.markdown(f"---")
            st.markdown(f"### **최종 합계 (VAT 별도): <span style='color:red; float:right;'>{final_display_cost:,.0f} 원</span>**", unsafe_allow_html=True)
            st.markdown(f"##### **잔금 (VAT 별도): <span style='float:right;'>{balance_due:,.0f} 원</span>**", unsafe_allow_html=True)


    st.divider()

    # --- Download and Send Section ---
    if st.session_state.get("final_selected_vehicle"):
        with st.container(border=True):
            st.subheader("📤 견적서 다운로드 및 발송")
            
            # --- PDF and Excel Generation ---
            # Always generate data for download buttons
            pdf_bytes_customer = None
            final_excel_bytes = None
            quote_image_bytes = None

            if 'pdf_generator' in globals() and callable(pdf_generator.generate_pdf):
                pdf_bytes_customer = pdf_generator.generate_pdf(
                    st.session_state.to_dict(),
                    cost_breakdown_items,
                    final_display_cost, # 최종 조정된 금액 전달
                    personnel_summary
                )
            else: st.warning("PDF 생성 모듈(pdf_generator)이 없어 PDF 생성이 비활성화되었습니다.")

            if pdf_bytes_customer and 'pdf_generator' in globals() and callable(pdf_generator.generate_quote_image_from_pdf):
                quote_image_bytes = pdf_generator.generate_quote_image_from_pdf(pdf_bytes_customer, image_format='JPEG')
            elif pdf_bytes_customer: st.warning("PDF 이미지 변환 모듈이 없어 MMS용 이미지 생성이 비활성화되었습니다.")


            if 'excel_filler' in globals() and callable(excel_filler.fill_final_excel_template):
                 final_excel_bytes = excel_filler.fill_final_excel_template(
                    st.session_state.to_dict(),
                    cost_breakdown_items,
                    final_display_cost, # 최종 조정된 금액 전달
                    personnel_summary
                )
            else: st.warning("Excel 생성 모듈(excel_filler)이 없어 Excel 생성이 비활성화되었습니다.")


            customer_phone_for_filename = utils.extract_phone_number_part(st.session_state.get("customer_phone", ""), default="견적")
            kst_filename_part = utils.get_current_kst_time_str("%Y%m%d")

            # --- Download Buttons ---
            col_pdf, col_excel, col_email_send, col_mms_send = st.columns(4)
            with col_pdf:
                if pdf_bytes_customer:
                    st.download_button(
                        label="📄 PDF 견적서 다운로드",
                        data=pdf_bytes_customer,
                        file_name=f"이삿날견적서_{customer_phone_for_filename}_{kst_filename_part}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else: st.button("📄 PDF 견적서 다운로드", disabled=True, use_container_width=True)

            with col_excel:
                if final_excel_bytes:
                    st.download_button(
                        label="📊 Excel 견적서 다운로드",
                        data=final_excel_bytes,
                        file_name=f"이삿날견적서_상세_{customer_phone_for_filename}_{kst_filename_part}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else: st.button("📊 Excel 견적서 다운로드", disabled=True, use_container_width=True)

            # --- Email Send ---
            with col_email_send:
                email_button_disabled = not pdf_bytes_customer or not st.session_state.get("customer_email") or 'email_utils' not in globals()
                if st.button("📧 이메일로 견적 발송", disabled=email_button_disabled, use_container_width=True):
                    if 'email_utils' in globals() and callable(email_utils.send_quote_email):
                        recipient = st.session_state.get("customer_email")
                        cust_name = st.session_state.get("customer_name", "고객")
                        subject = f"[이삿날] {cust_name}님의 이사 견적서입니다."
                        body = f"{cust_name}님, 요청하신 이사 견적서를 첨부파일로 보내드립니다.\n\n감사합니다.\n이삿날 드림"
                        pdf_name_email = f"이삿날견적서_{customer_phone_for_filename}_{kst_filename_part}.pdf"
                        
                        with st.spinner("이메일 발송 중..."):
                            email_sent = email_utils.send_quote_email(recipient, subject, body, pdf_bytes_customer, pdf_name_email)
                        if email_sent:
                            st.success(f"{recipient}(으)로 견적서 이메일 발송 성공!")
                        # 실패 메시지는 email_utils 내부에서 st.error로 표시
                    else:
                        st.error("이메일 발송 모듈(email_utils)이 준비되지 않았습니다.")
            
            # --- MMS Send ---
            with col_mms_send:
                mms_button_disabled = not quote_image_bytes or not st.session_state.get("customer_phone") or 'mms_utils' not in globals()
                if st.button("📱 MMS로 견적 발송", disabled=mms_button_disabled, use_container_width=True):
                    if 'mms_utils' in globals() and callable(mms_utils.send_mms_with_image):
                        recipient_phone_mms = st.session_state.get("customer_phone")
                        cust_name_mms = st.session_state.get("customer_name", "고객")
                        text_msg_mms = f"{cust_name_mms}님, 요청하신 이사 견적서 이미지입니다. 확인 후 연락주시면 감사하겠습니다. -이삿날-"
                        img_filename_mms = f"견적서_{customer_phone_for_filename}_{kst_filename_part}.jpg"
                        
                        with st.spinner("MMS 발송 준비 중... (실제 발송은 게이트웨이 연동 필요)"):
                            mms_sent = mms_utils.send_mms_with_image(recipient_phone_mms, quote_image_bytes, img_filename_mms, text_msg_mms)
                        
                        if mms_sent: # 실제 연동 시 성공 여부 판단
                            st.success(f"{recipient_phone_mms}(으)로 견적 이미지 MMS 발송 성공!")
                        else:
                            # 실패 메시지는 mms_utils 내부 또는 여기서 상세화 가능
                            st.warning("MMS 발송 기능이 아직 완전히 연동되지 않았거나, 발송에 실패했습니다. (mms_utils.py 확인 필요)")
                    else:
                        st.error("MMS 발송 모듈(mms_utils)이 준비되지 않았습니다.")

    # --- Display Current KST Time ---
    current_kst = utils.get_current_kst_time_str() if 'utils' in globals() and hasattr(utils, 'get_current_kst_time_str') else "시간 로드 실패"
    st.caption(f"현재 시간 (KST): {current_kst}")