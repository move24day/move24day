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

if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
    state_manager.initialize_session_state(callbacks.update_basket_quantities)
else:
    st.error("오류: callbacks 모듈 또는 update_basket_quantities 함수를 찾을 수 없습니다.")
    st.stop()


tab1, tab2, tab3 = st.tabs(["👤 고객 정보", "📋 물품 선택", "💰 견적 및 비용"])

try:
    move_type_options_main = getattr(state_manager, 'MOVE_TYPE_OPTIONS', None)
    default_move_type_app = None
    if move_type_options_main:
        default_move_type_app = move_type_options_main[0]
    elif hasattr(data, 'item_definitions') and data.item_definitions:
        default_move_type_app = list(data.item_definitions.keys())[0]
        st.warning("MOVE_TYPE_OPTIONS를 찾을 수 없어 data.item_definitions의 첫 번째 키를 사용합니다.")
    
    current_move_type_main = st.session_state.get('base_move_type', default_move_type_app)

    if not current_move_type_main:
        st.error("이사 유형을 결정할 수 없습니다. data.py 또는 state_manager.py를 확인하세요.")
        st.session_state.total_volume = 0.0
        st.session_state.total_weight = 0.0
        st.session_state.recommended_vehicle_auto = None
        st.session_state.remaining_space = 0.0
    else:
        st.session_state.total_volume, st.session_state.total_weight = calculations.calculate_total_volume_weight(
            st.session_state.to_dict(), current_move_type_main
        )
        # recommend_vehicle 호출 시 current_move_type_main 전달
        rec_vehicle, rem_space = calculations.recommend_vehicle(
            st.session_state.total_volume, 
            st.session_state.total_weight,
            current_move_type_main # << 수정된 부분: 이사 유형 전달
        )
        st.session_state.recommended_vehicle_auto = rec_vehicle
        st.session_state.remaining_space = rem_space 

    if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        callbacks.update_basket_quantities()
    else:
        st.warning("callbacks.update_basket_quantities 함수를 찾을 수 없어 차량 및 바구니 자동 업데이트가 원활하지 않을 수 있습니다.")

except Exception as calc_error:
     st.error(f"물량 계산 또는 콜백 실행 중 오류 발생: {calc_error}")
     traceback.print_exc()
     st.session_state.total_volume = 0.0
     st.session_state.total_weight = 0.0
     st.session_state.recommended_vehicle_auto = None
     st.session_state.remaining_space = 0.0
     if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        callbacks.update_basket_quantities()


with tab1:
    ui_tab1.render_tab1()

with tab2:
    ui_tab2.render_tab2()

with tab3:
    ui_tab3.render_tab3()
