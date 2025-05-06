# ui_tab3.py (이미지 관련 코드 참조 제거)
import streamlit as st
import pandas as pd
import traceback
import io # For BytesIO with file downloads

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # For PDF and Summary Excel
    import excel_filler # For Final Excel
    import email_utils # For sending email
    from state_manager import MOVE_TYPE_OPTIONS # Import options if needed
    import callbacks # Import callbacks if needed for widget sync
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 - {e}")
    st.stop()

def render_tab3():
    """Renders the UI for Tab 3: Costs and Output."""

    st.header("💰 견적 비용 계산 및 최종 확인")
    st.caption("선택된 품목과 옵션을 바탕으로 예상 비용을 계산하고 견적서를 생성합니다.")

    # --- Recalculate Costs Section ---
    # Use a placeholder for cost calculation results if not yet calculated
    calculated_total_cost = 0
    calculated_cost_items = []
    personnel_info = {}

    try:
        # Perform cost calculation (this should already happen in app.py before rendering tabs,
        # but we can recalculate here if needed, or just retrieve from state)
        # Ensure calculations.py is robust against missing state keys if any were removed
        calculated_total_cost, calculated_cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())
        st.session_state.calculated_total_cost = calculated_total_cost # Store in state if needed elsewhere
        st.session_state.calculated_cost_items = calculated_cost_items
        st.session_state.personnel_info = personnel_info

    except Exception as e:
        st.error(f"비용 계산 중 오류 발생: {e}")
        traceback.print_exc()
        st.warning("비용 계산에 실패하여 일부 기능이 제한될 수 있습니다.")
        # Reset results on error
        st.session_state.calculated_total_cost = 0
        st.session_state.calculated_cost_items = []
        st.session_state.personnel_info = {}
        calculated_total_cost = 0
        calculated_cost_items = []
        personnel_info = {}

    # --- Display Costs and Options ---
    col_cost_details, col_options = st.columns([2, 1]) # Give more space to cost details

    with col_cost_details:
        st.subheader("📊 비용 상세 내역")
        if calculated_cost_items:
            cost_df = pd.DataFrame(calculated_cost_items, columns=["항목", "금액", "비고"])
            # Format the '금액' column for display
            cost_df['금액'] = cost_df['금액'].apply(lambda x: f"{int(x):,} 원" if pd.notna(x) else "0 원")
            st.dataframe(cost_df, hide_index=True, use_container_width=True)
        else:
            st.info("계산된 비용 내역이 없습니다. 품목 및 옵션을 확인하세요.")

        st.markdown("---")
        st.subheader("💰 최종 예상 비용")
        total_cost_str = f"{calculated_total_cost:,.0f} 원"
        st.metric(label="총 견적 비용 (VAT 별도)", value=total_cost_str)

        # Deposit and Balance Calculation
        deposit_amount = st.session_state.get('deposit_amount', 0)
        remaining_balance = calculated_total_cost - deposit_amount
        deposit_str = f"{deposit_amount:,.0f} 원"
        remaining_str = f"{remaining_balance:,.0f} 원"

        col_dep, col_bal = st.columns(2)
        with col_dep:
            st.metric(label="계약금 (-)", value=deposit_str)
        with col_bal:
            st.metric(label="잔금 (VAT 별도)", value=remaining_str)


    with col_options:
        st.subheader("⚙️ 추가 옵션 및 조정")

        # Sync move type widget if needed
        move_type_options_tab3 = globals().get('MOVE_TYPE_OPTIONS')
        sync_move_type_callback_ref = getattr(callbacks, 'sync_move_type', None)
        if move_type_options_tab3:
             try: current_index_tab3 = move_type_options_tab3.index(st.session_state.base_move_type)
             except ValueError: current_index_tab3 = 0
             st.radio( "기본 이사 유형 확인", options=move_type_options_tab3, index=current_index_tab3,
                       key="base_move_type_widget_tab3", on_change=sync_move_type_callback_ref,
                       args=("base_move_type_widget_tab3",) )
        else: st.warning("이사 유형 옵션 로드 실패")

        # Vehicle Selection
        st.selectbox(
            "차량 선택 방식",
            ("자동 추천 차량 사용", "수동 선택"),
            key="vehicle_select_radio",
            on_change=callbacks.update_basket_quantities # Update baskets on change
        )

        rec_vehicle_tab3 = st.session_state.get('recommended_vehicle_auto')
        vehicle_display = ""
        if st.session_state.vehicle_select_radio == "자동 추천 차량 사용":
            if rec_vehicle_tab3 and "초과" not in rec_vehicle_tab3:
                vehicle_display = f"✅ 자동: **{rec_vehicle_tab3}**"
                st.session_state.manual_vehicle_select_value = None # Clear manual selection
            elif rec_vehicle_tab3 and "초과" in rec_vehicle_tab3:
                vehicle_display = f"❌ 자동: **{rec_vehicle_tab3}**"
                st.session_state.manual_vehicle_select_value = None # Clear manual selection
            else:
                vehicle_display = "ℹ️ 자동 추천 불가 (물량 확인)"
                st.session_state.manual_vehicle_select_value = None # Clear manual selection
            st.markdown(vehicle_display)
        else: # Manual Selection
            current_move_type_tab3 = st.session_state.get('base_move_type')
            available_trucks = list(data.vehicle_prices.get(current_move_type_tab3, {}).keys()) if current_move_type_tab3 else []
            # Ensure manual selection is valid, fallback if not
            manual_value = st.session_state.get('manual_vehicle_select_value')
            if manual_value not in available_trucks and available_trucks:
                 st.session_state.manual_vehicle_select_value = available_trucks[0] # Fallback to first available
            elif not available_trucks:
                 st.session_state.manual_vehicle_select_value = None

            st.selectbox(
                "수동 차량 선택:",
                options=available_trucks,
                key="manual_vehicle_select_value",
                index=available_trucks.index(st.session_state.manual_vehicle_select_value) if st.session_state.manual_vehicle_select_value in available_trucks else 0,
                on_change=callbacks.update_basket_quantities # Update baskets on change
            )
            st.markdown(f"☑️ 수동 선택: **{st.session_state.get('manual_vehicle_select_value', 'N/A')}**")

        # Final selected vehicle display (for confirmation)
        final_vehicle_tab3 = st.session_state.get('final_selected_vehicle')
        if final_vehicle_tab3:
             st.success(f"➡️ 최종 선택 차량: **{final_vehicle_tab3}**")
        else:
             st.warning("⚠️ 최종 차량이 선택되지 않았습니다.")

        st.markdown("---")

        # Additional Personnel & Options
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.number_input("👨 추가 남자 인원", min_value=0, step=1, key="add_men")
        with col_p2:
            st.number_input("👩 추가 여자 인원", min_value=0, step=1, key="add_women")

        st.checkbox("🧹 기본 여성 인원 제외", key="remove_base_housewife", help="체크 시 기본 포함된 여성 인원 비용이 차감됩니다.")

        # Ladder/Sky Options
        from_method = st.session_state.get('from_method')
        to_method = st.session_state.get('to_method')
        if from_method == "스카이 🏗️": st.number_input("⬆️ 출발지 스카이 시간", min_value=1, step=1, key="sky_hours_from")
        if to_method == "스카이 🏗️": st.number_input("⬇️ 도착지 스카이 시간", min_value=1, step=1, key="sky_hours_final")
        st.number_input("🏞️ 지방 사다리차 추가금", min_value=0, step=1000, key="regional_ladder_surcharge", help="수도권 외 지역 사다리차 사용 시 추가 비용")

        # Waste Disposal
        st.checkbox("🗑️ 폐기물 처리 요청", key="has_waste_check")
        if st.session_state.get('has_waste_check'):
            st.number_input("처리할 폐기물 톤(Ton)", min_value=0.5, step=0.5, key="waste_tons_input", format="%.1f")

        # Special Day Surcharges
        st.markdown("**🗓️ 이사 날짜 할증 선택**")
        date_opts = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        cols_dates = st.columns(len(date_opts))
        for i, option in enumerate(date_opts):
            with cols_dates[i]:
                st.checkbox(option, key=f"date_opt_{i}_widget")

        st.markdown("---")
        # Adjustments
        st.number_input("💰 비용 조정 (+/-)", step=1000, key="adjustment_amount", help="최종 비용 가감 조정 (음수 입력 가능)")
        st.number_input("💰 계약금", min_value=0, step=10000, key="deposit_amount")

        # Actual dispatched vehicle input (for final excel)
        st.markdown("**🚚 실제 투입 차량 (최종 엑셀용)**")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1: st.number_input("1톤", min_value=0, key="dispatched_1t")
        with col_t2: st.number_input("2.5톤", min_value=0, key="dispatched_2_5t")
        with col_t3: st.number_input("3.5톤", min_value=0, key="dispatched_3_5t")
        with col_t4: st.number_input("5톤", min_value=0, key="dispatched_5t")


    st.markdown("---")
    # --- Output Generation Section ---
    st.header("📄 견적서 생성 및 발송")

    # Prepare data for output functions
    state_dict = st.session_state.to_dict()
    final_cost_for_output = st.session_state.get('calculated_total_cost', 0)
    cost_items_for_output = st.session_state.get('calculated_cost_items', [])
    personnel_info_for_output = st.session_state.get('personnel_info', {})

    # Filename generation for downloads
    customer_name_file = state_dict.get('customer_name', '고객')
    moving_date_file = state_dict.get('moving_date')
    date_str_file = moving_date_file.strftime('%Y%m%d') if isinstance(moving_date_file, date) else "날짜미정"
    base_filename_file = f"이삿날견적_{date_str_file}_{customer_name_file}"

    col_pdf, col_excel_sum, col_excel_final, col_email = st.columns(4)

    # PDF Generation
    with col_pdf:
        st.markdown("**PDF 견적서**")
        try:
            # Generate PDF in memory (이미지 데이터 불필요)
            pdf_bytes = pdf_generator.generate_pdf(
                state_dict,
                cost_items_for_output,
                final_cost_for_output,
                personnel_info_for_output
                # 이미지 관련 인자 제거됨
            )
            if pdf_bytes:
                st.download_button(
                    label="📄 PDF 다운로드",
                    data=pdf_bytes,
                    file_name=f"{base_filename_file}.pdf",
                    mime="application/pdf"
                )
                st.session_state['pdf_data_customer'] = pdf_bytes # Store for email
            else:
                st.error("PDF 생성 실패")
        except Exception as pdf_e:
            st.error(f"PDF 생성 오류: {pdf_e}")
            traceback.print_exc()

    # Summary Excel Generation (from pdf_generator)
    with col_excel_sum:
        st.markdown("**요약 Excel (내부 확인용)**")
        try:
            # Generate summary excel (이미지 데이터 불필요)
            excel_summary_bytes = pdf_generator.generate_excel(
                 state_dict,
                 cost_items_for_output,
                 final_cost_for_output,
                 personnel_info_for_output
                 # 이미지 관련 인자 제거됨
            )
            if excel_summary_bytes:
                st.download_button(
                    label="📊 요약 Excel 다운로드",
                    data=excel_summary_bytes,
                    file_name=f"{base_filename_file}_요약.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("요약 Excel 생성 실패")
        except Exception as exs_e:
            st.error(f"요약 Excel 오류: {exs_e}")
            traceback.print_exc()

    # Final Excel Generation (from excel_filler)
    with col_excel_final:
        st.markdown("**최종 Excel (전달용)**")
        try:
            # Generate final excel (이미지 데이터 불필요)
            final_excel_bytes = excel_filler.fill_final_excel_template(
                 state_dict,
                 cost_items_for_output,
                 final_cost_for_output,
                 personnel_info_for_output
                 # 이미지 관련 인자 제거됨
            )
            if final_excel_bytes:
                 st.download_button(
                      label="📋 최종 Excel 다운로드",
                      data=final_excel_bytes,
                      file_name=f"{base_filename_file}_최종견적.xlsx",
                      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                 )
                 st.session_state['final_excel_data'] = final_excel_bytes # Optional: Store if needed
            else:
                 st.error("최종 Excel 생성 실패")
        except Exception as exf_e:
            st.error(f"최종 Excel 오류: {exf_e}")
            traceback.print_exc()


    # Email Section
    with col_email:
        st.markdown("**이메일 발송**")
        recipient = st.session_state.get('customer_email')
        pdf_ready_for_email = st.session_state.get('pdf_data_customer')

        if not recipient:
            st.warning("고객 이메일 주소가 없습니다.")
        elif not pdf_ready_for_email:
            st.warning("PDF 견적서가 생성되지 않았습니다.")
        else:
            email_subject = f"[이삿날] {customer_name_file} 고객님 이사 견적서입니다."
            email_body = f"""안녕하세요, {customer_name_file} 고객님. 이삿날입니다.

요청하신 이사 견적서를 첨부해 드립니다.
이사 예정일: {date_str_file}

견적 내용을 확인하신 후 궁금한 점이 있으시면 언제든지 연락 주세요.

감사합니다.

이삿날 드림
{data.COMPANY_PHONE_1 if hasattr(data, 'COMPANY_PHONE_1') else ''}
{data.COMPANY_EMAIL if hasattr(data, 'COMPANY_EMAIL') else ''}
"""
            if st.button("📧 이메일 발송", key="send_email_btn"):
                with st.spinner("이메일 발송 중..."):
                    success = email_utils.send_quote_email(
                        recipient_email=recipient,
                        subject=email_subject,
                        body=email_body,
                        pdf_bytes=pdf_ready_for_email, # PDF 바이트 전달
                        pdf_filename=f"{base_filename_file}.pdf" # 파일명 전달
                        # 이미지 첨부 관련 인자 없음
                    )
                if success:
                    st.success(f"{recipient} 주소로 이메일 발송 완료!")
                else:
                    st.error("이메일 발송 실패. 관리자에게 문의하세요.")

# --- End of render_tab3 function ---