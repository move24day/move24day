# ui_tab3.py (수정된 전체 코드 - file_uploader 세션 오류 해결 포함)

import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import traceback

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator
    import excel_filler
    import excel_summary_generator
    from state_manager import MOVE_TYPE_OPTIONS
    from callbacks import sync_move_type, update_basket_quantities
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션")

    with st.expander("결적서 이미지 업로드 및 미리보기", expanded=True):
        uploaded_file = st.file_uploader("이미지 파일을 업로드하세요", type=['png', 'jpg', 'jpeg'], key="quote_image_uploader")

        if uploaded_file:
            st.session_state["uploaded_file_for_preview"] = uploaded_file
            st.image(uploaded_file, caption="업로드된 결적서 이미지 미리보기", use_column_width=True)
        elif "uploaded_file_for_preview" in st.session_state:
            st.image(st.session_state["uploaded_file_for_preview"], caption="이전 업로드 이미지", use_column_width=True)

    st.write("---")
    st.subheader("계산된 결적서 PDF 및 Excel 다운로드")

    if st.button("📄 결적서 PDF 생성"):
        try:
            pdf_bytes = pdf_generator.generate_pdf(st.session_state)
            if pdf_bytes:
                st.download_button(
                    label="📅 PDF 다운로드",
                    data=pdf_bytes,
                    file_name="결적서.pdf",
                    mime="application/pdf"
                )
                st.success("PDF 생성 완료")
            else:
                st.warning("PDF 생성 실패")
        except Exception as e:
            st.error(f"PDF 생성 중 오류 발생: {e}")
            traceback.print_exc()

    if st.button("📊 Excel 결적서 생성"):
        try:
            final_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state)
            st.session_state["final_adjusted_cost"] = final_cost

            excel_bytes = excel_summary_generator.generate_summary_excel(
                st.session_state,
                cost_items,
                personnel_info,
                vehicle_info={},
                waste_info={
                    "total_waste_tons": st.session_state.get("waste_tons_input", 0),
                    "total_waste_cost": st.session_state.get("waste_tons_input", 0) * data.WASTE_DISPOSAL_COST_PER_TON
                }
            )
            if excel_bytes:
                st.download_button(
                    label="📅 Excel 다운로드",
                    data=excel_bytes,
                    file_name="결적서_요약.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("Excel 생성 완료")
            else:
                st.warning("Excel 생성 실패")
        except Exception as e:
            st.error(f"Excel 생성 중 오류 발생: {e}")
            traceback.print_exc()

    st.write("---")
    st.caption("※ 이 탭에서는 생성된 결적서를 PDF 또는 Excel로 다운로드하거나, 이미지를 업로드해서 문자 전송 등을 준비할 수 있습니다.")
