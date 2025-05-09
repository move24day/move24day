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
    # Use the correct GDrive helper name consistently
    import google_drive_helper as gdrive
    import pdf_generator # Still needed for generate_excel used by summary in ui_tab3
    import excel_filler # Still needed for final excel in ui_tab3
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
    import callbacks # callbacks 모듈 임포트 확인
    import ui_tab1
    import ui_tab2
    import ui_tab3
except ImportError as ie:
    st.error(f"메인 앱: 필수 UI/상태 모듈 로딩 실패 - {ie}.")
    st.stop()
except Exception as e:
    st.error(f"메인 앱: UI/상태 모듈 로딩 중 예외 발생 - {e}")
    traceback.print_exc() # Print detailed traceback for debugging
    st.stop()


# --- Main Application ---

# Display Title
st.markdown("<h1 style='text-align: center; color: #1E90FF;'>🚚 이삿날 스마트 견적 🚚</h1>", unsafe_allow_html=True)
st.write("")

# Initialize session state (pass the callback reference)
# Ensure callbacks module is imported correctly and function exists
if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
    state_manager.initialize_session_state(callbacks.update_basket_quantities)
else:
    st.error("오류: callbacks 모듈 또는 update_basket_quantities 함수를 찾을 수 없습니다.")
    st.stop()


# --- Define Tabs ---
tab1, tab2, tab3 = st.tabs(["👤 고객 정보", "📋 물품 선택", "💰 견적 및 비용"])


# --- Recalculate Volume/Weight/Recommendation Before Rendering Tabs ---
# This ensures Tab 2 and Tab 3 have the latest info based on state
try:
    move_type_options_main = getattr(state_manager, 'MOVE_TYPE_OPTIONS', None)
    if not move_type_options_main:
        st.warning("MOVE_TYPE_OPTIONS를 찾을 수 없습니다. data.py/state_manager.py 확인 필요. 기본값으로 진행합니다.")
        current_move_type_main = list(data.item_definitions.keys())[0] if hasattr(data, 'item_definitions') and data.item_definitions else None
    else:
        current_move_type_main = st.session_state.get('base_move_type', move_type_options_main[0])

    if current_move_type_main:
        st.session_state.total_volume, st.session_state.total_weight = calculations.calculate_total_volume_weight(
            st.session_state.to_dict(), current_move_type_main
        )
        rec_vehicle, rem_space = calculations.recommend_vehicle(
            st.session_state.total_volume, st.session_state.total_weight
        )
        st.session_state.recommended_vehicle_auto = rec_vehicle
        st.session_state.remaining_space = rem_space 
    else:
         st.error("현재 이사 유형을 결정할 수 없습니다. data.py 파일을 확인하세요.")
         st.session_state.total_volume = 0.0
         st.session_state.total_weight = 0.0
         st.session_state.recommended_vehicle_auto = None
         st.session_state.remaining_space = 0.0

    # <<수정된 부분: 추천 차량 계산 후 콜백 함수 호출>>
    # 이 호출을 통해 recommended_vehicle_auto 변경 시 final_selected_vehicle 및 바구니 수량이 업데이트됩니다.
    if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        callbacks.update_basket_quantities()
    else:
        # 이 경고는 initialize_session_state에서도 이미 확인하므로 중복될 수 있으나, 여기서도 중요하므로 유지 가능
        st.warning("callbacks.update_basket_quantities 함수를 찾을 수 없어 차량 및 바구니 자동 업데이트가 원활하지 않을 수 있습니다.")

except Exception as calc_error:
     st.error(f"물량 계산 또는 콜백 실행 중 오류 발생: {calc_error}")
     traceback.print_exc()
     # Set defaults on error
     st.session_state.total_volume = 0.0
     st.session_state.total_weight = 0.0
     st.session_state.recommended_vehicle_auto = None
     st.session_state.remaining_space = 0.0
     st.session_state.final_selected_vehicle = None # 오류 발생 시 final_selected_vehicle도 초기화 고려


# --- Render Tabs by Calling UI Functions ---
with tab1:
    ui_tab1.render_tab1()

with tab2:
    ui_tab2.render_tab2()

with tab3:
    ui_tab3.render_tab3()

# Optional: Footer or other elements outside tabs can go here
