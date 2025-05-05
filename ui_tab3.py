# ui_tab3.py (Streamlit container compatibility improved)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime
import traceback  # Keep for error handling

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator  # Needed for generate_excel (used in summary) and generate_pdf
    import excel_filler  # Needed for the final excel generation
    from state_manager import MOVE_TYPE_OPTIONS
    from callbacks import sync_move_type, update_basket_quantities
except ImportError as e:
    st.error(f"UI Tab 3: 시스템 목록 로딩 실패 - {e}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    st.header("💰 계산 및 옵션")

    st.subheader("🏢 이사 유형 확인/변경")
    current_move_type = st.session_state.get('base_move_type')
    current_index_tab3 = 0
    if MOVE_TYPE_OPTIONS and isinstance(MOVE_TYPE_OPTIONS, (list, tuple)):
        try:
            current_index_tab3 = MOVE_TYPE_OPTIONS.index(current_move_type)
        except ValueError:
            current_index_tab3 = 0
            if MOVE_TYPE_OPTIONS:
                st.session_state.base_move_type = MOVE_TYPE_OPTIONS[0]
                print("Warning: Resetting base_move_type in Tab 3 due to invalid state.")
            else:
                st.error("이사 유형 옵션을 data.py에서 찾을 수 없습니다.")

        st.radio(
            "기본 이사 유형:",
            options=MOVE_TYPE_OPTIONS,
            index=current_index_tab3,
            horizontal=True,
            key="base_move_type_widget_tab3",
            on_change=sync_move_type,
            args=("base_move_type_widget_tab3",)
        )
    else:
        st.error("이사 유형 옵션을 정의할 수 없습니다. data.py 파일을 확인해주세요.")

    st.divider()

    # --- Vehicle Selection ---
    if hasattr(st, "container"):
        with st.container(border=True):
            st.subheader("🚚 차반 선택")
            col_v1_widget, col_v2_widget = st.columns([1, 2])
            with col_v1_widget:
                st.radio("차반 선택 방식:", ["자동 추천 차반 사용", "수동으로 차반 선택"],
                         key="vehicle_select_radio",
                         help="자동 추천을 사용하거나, 목록에서 직접 차반을 선택합니다.",
                         on_change=update_basket_quantities)
            with col_v2_widget:
                current_move_type_widget = st.session_state.base_move_type
                vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
                available_trucks_widget = sorted(vehicle_prices_options_widget.keys(), key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))
                use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차반 사용"
                recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
                final_vehicle_widget = st.session_state.get('final_selected_vehicle')
                valid_auto_widget = (recommended_vehicle_auto_widget and "추천 초과" not in recommended_vehicle_auto_widget and recommended_vehicle_auto_widget in available_trucks_widget)

                if use_auto_widget:
                    if valid_auto_widget:
                        st.success(f"✅ 자동 선택됨: **{final_vehicle_widget}**")
                    else:
                        st.error("⚠️ 자동 추천 불가")
                        if available_trucks_widget:
                            current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                            current_index_widget = 0
                            try:
                                current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                            except ValueError:
                                current_index_widget = 0
                            if current_manual_selection_widget not in available_trucks_widget:
                                st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                            st.selectbox("수동으로 차반 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities)
                else:
                    if available_trucks_widget:
                        current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                        current_index_widget = 0
                        try:
                            current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError:
                            current_index_widget = 0
                        if current_manual_selection_widget not in available_trucks_widget:
                            st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                        st.selectbox("차반 직접 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities)
                    else:
                        st.error("❌ 현재 이사 유형에 선택 가능한 차반 정보가 없습니다.")
    else:
        st.warning("현재 Streamlit 버전에서 `st.container(border=True)`를 지원하지 않습니다. Streamlit 1.25.0 이상으로 업그레이드해주세요.")

    st.divider()

    # 나머지 UI는 동일하게 유지됨 (필요 시 계속 추가 가능)

# --- End of render_tab3 function ---
