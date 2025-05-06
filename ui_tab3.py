# ui_tab3.py (Key changed for file_uploader)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date # date 추가
import traceback # Keep for error handling

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # Needed for generate_excel (used in summary) and generate_pdf
    import excel_filler # Needed for the final excel generation
    # Import MOVE_TYPE_OPTIONS from state_manager
    from state_manager import MOVE_TYPE_OPTIONS
    # Import callbacks needed in this tab
    from callbacks import sync_move_type, update_basket_quantities
    # Import excel_summary_generator if it exists and is used
    import excel_summary_generator # Assuming this exists based on previous context
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션")

    # --- Expander for Image Preview (Assuming this is its purpose) ---
    # --- !!! KEY CHANGED HERE !!! ---
    with st.expander("결적서 이미지 업로드 및 미리보기", expanded=True):
        uploaded_file = st.file_uploader(
            "이미지 파일을 업로드하세요",
            type=['png', 'jpg', 'jpeg'],
            key="preview_image_uploader"  # <-- UNIQUE KEY
        )

        if uploaded_file:
            # Store the uploaded file object in session state for preview persistence
            st.session_state["uploaded_file_for_preview"] = uploaded_file
            # Display the newly uploaded file
            st.image(uploaded_file, caption="업로드된 결적서 이미지 미리보기", use_column_width=True)
        elif "uploaded_file_for_preview" in st.session_state and st.session_state["uploaded_file_for_preview"] is not None:
             # If no new file is uploaded, but a previous one exists in state, show it
             try:
                st.image(st.session_state["uploaded_file_for_preview"], caption="이전 업로드 이미지", use_column_width=True)
             except Exception as img_err:
                 st.warning(f"이전 이미지 표시에 실패했습니다: {img_err}")
                 # Optionally clear the invalid state
                 # del st.session_state["uploaded_file_for_preview"]
    # --- !!! KEY CHANGE APPLIED !!! ---

    st.write("---") # Divider moved outside expander

    # --- Move Type Selection (Tab 3) ---
    # (This section seems removed in the provided ui_tab3 code, keep it removed or add back if needed)
    # st.subheader("🏢 이사 유형 확인/변경")
    # ... (Radio button code for move type sync) ...
    # st.divider()

    # --- Vehicle Selection ---
    # (This section seems removed in the provided ui_tab3 code, keep it removed or add back if needed)
    # with st.container(border=True):
    #    st.subheader("🚚 차량 선택")
    #    ... (Vehicle selection radio/selectbox code) ...
    # st.divider()

    # --- Work Conditions & Options ---
    # (This section seems removed in the provided ui_tab3 code, keep it removed or add back if needed)
    # with st.container(border=True):
    #    st.subheader("🛠️ 작업 조건 및 추가 옵션")
    #    ... (Sky hours, additional personnel, dispatched vehicles, remove housewife checkbox, date options) ...

    # --- Cost Adjustment & Deposit ---
    # (This section seems removed in the provided ui_tab3 code, keep it removed or add back if needed)
    # with st.container(border=True):
    #    st.subheader("💰 비용 조정 및 계약금")
    #    ... (Deposit, Adjustment, Regional Surcharge inputs) ...
    # st.divider()

    # --- Final Quote Results ---
    # (This section seems removed in the provided ui_tab3 code, keep it removed or add back if needed)
    # st.header("💵 최종 견적 결과")
    # ... (Cost calculation call, display total/deposit/remaining, cost details dataframe) ...
    # ... (Summary generation and display logic using format_money_manwon_unit etc.) ...
    # st.divider()

    # --- Download Section ---
    # This section is present in the provided ui_tab3 code, keep it.
    st.subheader("📄 계산된 결적서 PDF 및 Excel 다운로드") # Header changed slightly from original

    # Check if calculations can be run (needs a selected vehicle)
    final_selected_vehicle_dl = st.session_state.get('final_selected_vehicle') # Check if vehicle is selected

    if final_selected_vehicle_dl:
        # Run calculations only if needed and vehicle is selected
        try:
            # It might be better to run calculation once and store results if multiple buttons need it
            # Or run it inside each button's logic if state might change between button presses
            final_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())
            st.session_state["final_adjusted_cost"] = final_cost # Store for potential reuse
            has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False
            can_gen_pdf = not has_cost_error
            can_gen_final_excel = True # Assume final excel can always be generated if vehicle selected
            can_gen_summary_excel = not has_cost_error # Summary excel might depend on valid cost items

        except Exception as calc_err:
            st.error(f"비용 계산 중 오류 발생: {calc_err}")
            traceback.print_exc()
            can_gen_pdf = False
            can_gen_final_excel = False
            can_gen_summary_excel = False
            cost_items = [] # Ensure cost_items is defined for later checks
            personnel_info = {}

        cols_dl = st.columns(3) # Use 3 columns for downloads

        with cols_dl[0]:
            st.markdown("**① Final 견적서 (Excel)**")
            if can_gen_final_excel:
                 # Button to generate Final Excel
                 if st.button("📄 생성: Final 견적서"):
                     # Rerun calculation if state could have changed, otherwise use stored results
                     latest_total_cost_fe, latest_cost_items_fe, latest_personnel_info_fe = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                     filled_excel_data = excel_filler.fill_final_excel_template(st.session_state.to_dict(), latest_cost_items_fe, latest_total_cost_fe, latest_personnel_info_fe)
                     if filled_excel_data:
                         st.session_state['final_excel_data'] = filled_excel_data
                         st.success("✅ Final Excel 생성 완료!")
                     else:
                         if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']
                         st.error("❌ Final Excel 생성 실패.")

                 # Download button for Final Excel (appears after generation)
                 if st.session_state.get('final_excel_data'):
                     ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d') if pytz else datetime.now().strftime('%y%m%d')
                     fname = f"{ph_part}_{now_str}_Final견적서.xlsx"
                     st.download_button("📥 다운로드 (Final Excel)", st.session_state['final_excel_data'], fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_final_excel')
                 else:
                     st.caption("생성 버튼 클릭")
            else:
                st.caption("Excel 생성 불가") # Simplified message

        with cols_dl[1]:
            st.markdown("**② 고객용 견적서 (PDF)**")
            if can_gen_pdf:
                # Button to generate PDF
                if st.button("📄 생성: PDF 견적서"):
                    # Use already calculated results if possible, or recalculate
                    latest_total_cost_pdf = st.session_state.get("final_adjusted_cost", 0)
                    # pdf_generator might need the specific format from calculations
                    latest_total_cost_pdf_recalc, latest_cost_items_pdf, latest_personnel_info_pdf = calculations.calculate_total_moving_cost(st.session_state.to_dict())

                    pdf_bytes = pdf_generator.generate_pdf(st.session_state.to_dict(), latest_cost_items_pdf, latest_total_cost_pdf_recalc, latest_personnel_info_pdf)
                    st.session_state['pdf_data_customer'] = pdf_bytes
                    if pdf_bytes:
                        st.success("✅ PDF 생성 완료!")
                    else:
                        if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']
                        st.error("❌ PDF 생성 실패.")

                # Download button for PDF
                if st.session_state.get('pdf_data_customer'):
                    ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M') if pytz else datetime.now().strftime('%y%m%d_%H%M')
                    fname = f"{ph_part}_{now_str}_이삿날견적서.pdf"
                    st.download_button("📥 다운로드 (PDF)", st.session_state['pdf_data_customer'], fname, 'application/pdf', key='dl_pdf')
                else:
                     st.caption("생성 버튼 클릭")
            else:
                st.caption("PDF 생성 불가 (비용 오류?)") # Simplified message

        with cols_dl[2]:
             st.markdown("**③ 요약 Excel**")
             if can_gen_summary_excel:
                 # Button to generate Summary Excel
                 if st.button("📊 생성: 요약 Excel"):
                     # Use already calculated results
                     summary_total_cost = st.session_state.get("final_adjusted_cost", 0)
                     # Need to ensure cost_items and personnel_info are available from calculation check above
                     excel_bytes = excel_summary_generator.generate_summary_excel(
                         st.session_state.to_dict(), # Pass dict directly
                         cost_items, # Use results from check above
                         personnel_info, # Use results from check above
                         vehicle_info={}, # Pass empty or relevant vehicle info if needed
                         waste_info={ # Pass relevant waste info
                             "total_waste_tons": st.session_state.get("waste_tons_input", 0),
                             "total_waste_cost": st.session_state.get("waste_tons_input", 0) * data.WASTE_DISPOSAL_COST_PER_TON if hasattr(data,'WASTE_DISPOSAL_COST_PER_TON') else 0
                         }
                     )
                     if excel_bytes:
                         st.session_state['summary_excel_data'] = excel_bytes
                         st.success("✅ 요약 Excel 생성 완료!")
                     else:
                         if 'summary_excel_data' in st.session_state: del st.session_state['summary_excel_data']
                         st.error("❌ 요약 Excel 생성 실패.")

                 # Download button for Summary Excel
                 if st.session_state.get('summary_excel_data'):
                     ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d') if pytz else datetime.now().strftime('%y%m%d')
                     fname = f"{ph_part}_{now_str}_견적서_요약.xlsx"
                     st.download_button(
                         "📥 다운로드 (요약 Excel)",
                         st.session_state['summary_excel_data'],
                         fname,
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         key='dl_summary_excel'
                     )
                 else:
                     st.caption("생성 버튼 클릭")
             else:
                 st.caption("Excel 생성 불가 (비용 오류?)") # Simplified message

    else: # Vehicle not selected
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산 및 다운로드는 차량 선택 후 가능합니다.")

    st.write("---")
    st.caption("※ 이 탭에서는 생성된 견적서를 PDF 또는 Excel로 다운로드하거나, 이미지를 업로드해서 문자 전송 등을 준비할 수 있습니다.")


# --- End of render_tab3 function ---