# app.py (Main execution file)

# 1. Import streamlit first
import streamlit as st

# 2. Set page config early
st.set_page_config(page_title="이삿날 포장이사 견적서", layout="wide", page_icon="🚚")

# 3. Import standard libraries
import pandas as pd
from datetime import datetime, date
import pytz
import math
import traceback # For error logging
import io

# 4. Import custom utility and data modules
try:
    import data
    import utils
    import calculations
    import google_drive_helper as gdrive
    import pdf_generator
    import excel_filler
except ImportError as ie:
    st.error(f"메인 앱: 필수 유틸리티 모듈 로딩 실패 - {ie}.")
    st.stop()
except Exception as e:
    st.error(f"메인 앱: 유틸리티 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


# 5. Import the NEWLY CREATED modules
try:
    import state_manager
    import callbacks
    import ui_tab1
    import ui_tab2
    import ui_tab3
except ImportError as ie:
    st.error(f"메인 앱: 필수 UI/상태 모듈 로딩 실패 - {ie}.")
    st.stop()
except Exception as e:
    st.error(f"메인 앱: UI/상태 모듈 로딩 중 예외 발생 - {e}")
    traceback.print_exc()
    st.stop()


# --- Main Application ---

st.markdown("<h1 style='text-align: center; color: #1E90FF;'>🚚 이삿날 스마트 견적 🚚</h1>", unsafe_allow_html=True)
st.write("")

# Initialize session state (pass the callback reference for initial setup if needed)
if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
    state_manager.initialize_session_state(callbacks.update_basket_quantities)
else:
    st.error("오류: callbacks 모듈 또는 update_basket_quantities 함수를 찾을 수 없습니다.")
    st.stop()

# --- Recalculate Volume/Weight/Recommendation and Update Dependent States BEFORE Rendering Tabs ---
try:
    # Determine current_move_type_main
    move_type_options_main = getattr(state_manager, 'MOVE_TYPE_OPTIONS', None)
    default_move_type_app = None
    if move_type_options_main:
        default_move_type_app = move_type_options_main[0]
    elif hasattr(data, 'item_definitions') and data.item_definitions: # Fallback if MOVE_TYPE_OPTIONS is missing
        default_move_type_app = list(data.item_definitions.keys())[0]
        # st.warning("MOVE_TYPE_OPTIONS를 찾을 수 없어 data.item_definitions의 첫 번째 키를 사용합니다.") # 사용자에게 알림 최소화
    
    current_move_type_main = st.session_state.get('base_move_type', default_move_type_app)

    if not current_move_type_main:
        # This case should ideally not be reached if defaults are set properly
        st.error("이사 유형을 결정할 수 없습니다. data.py 또는 state_manager.py를 확인하세요.")
        st.session_state.total_volume = 0.0
        st.session_state.total_weight = 0.0
        st.session_state.recommended_vehicle_auto = None
        st.session_state.remaining_space = 0.0
    else:
        # Calculate total volume and weight
        st.session_state.total_volume, st.session_state.total_weight = calculations.calculate_total_volume_weight(
            st.session_state.to_dict(), current_move_type_main
        )
        # Recommend vehicle based on new totals and current move type
        rec_vehicle, rem_space = calculations.recommend_vehicle(
            st.session_state.total_volume,
            st.session_state.total_weight,
            current_move_type_main # Pass current_move_type
        )
        st.session_state.recommended_vehicle_auto = rec_vehicle
        st.session_state.remaining_space = rem_space

    # CRITICAL: Update final_selected_vehicle and basket quantities immediately
    # after recommended_vehicle_auto is determined.
    if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        # print("DEBUG APP: Calling update_basket_quantities AFTER recommendation in app.py")
        callbacks.update_basket_quantities()
    else:
        # This warning might be redundant if already checked during initialization
        st.warning("콜백 함수 'update_basket_quantities'를 찾을 수 없어 차량/바구니 자동 업데이트에 문제가 있을 수 있습니다.")

except Exception as calc_error:
     st.error(f"물량 계산 또는 콜백 실행 중 오류 발생: {calc_error}")
     traceback.print_exc()
     # Set defaults on error
     st.session_state.total_volume = 0.0
     st.session_state.total_weight = 0.0
     st.session_state.recommended_vehicle_auto = None
     st.session_state.remaining_space = 0.0
     # Ensure dependent states are also reset or updated
     if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        # print("DEBUG APP: Calling update_basket_quantities AFTER EXCEPTION in app.py")
        callbacks.update_basket_quantities() # This will use recommended_vehicle_auto = None


# --- Define and Render Tabs ---
# Now that all critical states (recommended_vehicle_auto, final_selected_vehicle, basket quantities)
# are presumably up-to-date, render the tabs.
tab1, tab2, tab3 = st.tabs(["👤 고객 정보", "📋 물품 선택", "💰 견적 및 비용"])

with tab1:
    ui_tab1.render_tab1()

with tab2:
    # Tab 2 will display the latest recommended_vehicle_auto
    # and the basket quantities as updated by the callback.
    ui_tab2.render_tab2()

with tab3:
    # Tab 3 will use the latest final_selected_vehicle for its display
    # and for cost calculations.
    ui_tab3.render_tab3()

# Optional: Footer or other elements outside tabs can go here