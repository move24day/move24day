# ui_tab1.py
import streamlit as st
from datetime import datetime, date
import pytz
import json # For saving state

# Import necessary custom modules
try:
    import data
    import utils
    import gdrive_utils
    from state_manager import (
        MOVE_TYPE_OPTIONS,
        STATE_KEYS_TO_SAVE,
        prepare_state_for_save,
        load_state_from_data
    )
    from callbacks import sync_move_type, update_selected_gdrive_id, update_basket_quantities
except ImportError as e:
    st.error(f"UI Tab 1: 필수 모듈 로딩 실패 - {e}")
    st.stop()


def render_tab1():
    """Renders the UI for Tab 1: Customer Info and Google Drive."""

    # === Google Drive Section ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        # --- Load Section ---
        with col_load:
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")

            if st.button("🔍 견적 검색"):
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 검색 중..."):
                        results = gdrive_utils.search_files(search_term_strip)
                    if results:
                        st.session_state.gdrive_search_results = results
                        st.session_state.gdrive_file_options_map = {res['name']: res['id'] for res in results}
                        # Set default selection to the first result if available
                        first_result_id = results[0].get('id')
                        st.session_state.gdrive_selected_file_id = first_result_id
                        st.session_state.gdrive_selected_filename = next((name for name, fid in st.session_state.gdrive_file_options_map.items() if fid == first_result_id), None)
                        st.success(f"✅ {len(results)}개 파일 검색 완료.")
                    else:
                        # Clear results if search yields nothing
                        st.session_state.gdrive_search_results = []
                        st.session_state.gdrive_file_options_map = {}
                        st.session_state.gdrive_selected_file_id = None
                        st.session_state.gdrive_selected_filename = None
                        st.warning("⚠️ 검색 결과가 없습니다.")
                else:
                    st.warning("⚠️ 검색어를 입력하세요.")

            # Display selectbox if search results exist
            if st.session_state.get('gdrive_search_results'):
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                current_selection_index = 0
                # Find index of currently selected filename (if it exists in options)
                if st.session_state.gdrive_selected_filename in file_options_display:
                    try:
                        current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                    except ValueError:
                        current_selection_index = 0 # Default to 0 if name somehow not found

                st.selectbox(
                    "불러올 파일 선택:",
                    options=file_options_display,
                    key="gdrive_selected_filename_widget", # Unique key for the widget
                    index=current_selection_index,
                    on_change=update_selected_gdrive_id # Use callback to update ID state
                )
                # Ensure ID state is synced initially if filename state exists but ID doesn't
                if st.session_state.gdrive_selected_filename and not st.session_state.gdrive_selected_file_id:
                     update_selected_gdrive_id()


            # Load Button
            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                file_id = st.session_state.gdrive_selected_file_id
                if file_id:
                    with st.spinner(f"🔄 견적 파일 로딩 중..."):
                        loaded_content = gdrive_utils.load_file(file_id) # load_file returns dict or None
                    if loaded_content:
                        # Pass the update_basket_quantities callback reference
                        load_success = load_state_from_data(loaded_content, update_basket_quantities)
                        if load_success:
                            st.success("✅ 견적 정보를 성공적으로 불러왔습니다.")
                            st.rerun() # Rerun to apply loaded state to the whole UI
                        # Error handling inside load_state_from_data
                    # else: Error handling inside gdrive_utils.load_file

        # --- Save Section ---
        with col_save:
            st.markdown("**현재 견적 저장**")
            try: kst_ex = pytz.timezone("Asia/Seoul"); now_ex_str = datetime.now(kst_ex).strftime('%y%m%d')
            except: now_ex_str = datetime.now().strftime('%y%m%d')
            phone_ex = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4, default="XXXX")
            example_fname = f"{now_ex_str}-{phone_ex}.json"
            st.caption(f"파일명 형식: `{example_fname}`")

            if st.button("💾 Google Drive에 저장", key="save_gdrive_btn"):
                try: kst_save = pytz.timezone("Asia/Seoul"); now_save = datetime.now(kst_save)
                except: now_save = datetime.now()
                date_str = now_save.strftime('%y%m%d')
                phone_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4)

                if phone_part == "번호없음" or not st.session_state.get('customer_phone', '').strip():
                    st.error("⚠️ 저장 실패: 고객 전화번호(뒤 4자리 포함)를 먼저 입력해주세요.")
                else:
                    save_filename = f"{date_str}-{phone_part}.json"
                    state_data_to_save = prepare_state_for_save() # Get state dict

                    try:
                        # Convert dict to JSON string
                        json_string_to_save = json.dumps(state_data_to_save, ensure_ascii=False, indent=2)
                        with st.spinner(f"🔄 '{save_filename}' 파일 저장 중..."):
                            # Pass the JSON string to the save function
                            save_result = gdrive_utils.save_file(save_filename, json_string_to_save)

                        if save_result and save_result.get('id'):
                             st.success(f"✅ '{save_filename}' 파일 저장/업데이트 완료 (ID: {save_result.get('id', 'N/A')}, Status: {save_result.get('status', 'N/A')}).")
                        else:
                             st.error(f"❌ '{save_filename}' 파일 저장 중 오류 발생.")
                    except TypeError as json_err:
                         st.error(f"❌ 저장 실패: 데이터를 JSON으로 변환 중 오류 발생 - {json_err}")
                    except Exception as save_err:
                         st.error(f"❌ '{save_filename}' 파일 저장 중 예외 발생: {save_err}")

            st.caption("동일 파일명 존재 시 덮어씁니다(업데이트).")

    st.divider()

    # --- Customer Info Section ---
    st.header("📝 고객 기본 정보")

    # Move Type Selection (Tab 1)
    try: current_index_tab1 = MOVE_TYPE_OPTIONS.index(st.session_state.base_move_type)
    except ValueError: current_index_tab1 = 0 # Default if state is somehow invalid
    st.radio(
        "🏢 **기본 이사 유형**",
        options=MOVE_TYPE_OPTIONS, index=current_index_tab1, horizontal=True,
        key="base_move_type_widget_tab1", # Use the specific widget key
        on_change=sync_move_type, # Use the callback
        args=("base_move_type_widget_tab1",) # Pass the key to the callback
    )

    # Additional Options Checkboxes
    col_opts1, col_opts2 = st.columns(2)
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")
    st.write("") # Spacer

    # Input Fields Columns
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name")
        st.text_input("📍 출발지 주소", key="from_location")
        if st.session_state.get('apply_long_distance'):
            st.selectbox("🛣️ 장거리 구간 선택", data.long_distance_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1")
        st.selectbox("🛠️ 출발지 작업 방법", data.METHOD_OPTIONS, key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택")

    with col2:
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678")
        st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소")
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2")
        st.selectbox("🛠️ 도착지 작업 방법", data.METHOD_OPTIONS, key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
        # Ensure moving_date is a date object before passing to date_input
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date):
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def # Reset to default
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date")
        st.caption(f"⏱️ 견적 생성일: {utils.get_current_kst_time_str()}")

    st.divider()

    # Storage Move Info (Conditional)
    if st.session_state.get('is_storage_move'):
        st.subheader("📦 보관이사 추가 정보")
        st.radio("보관 유형 선택:", options=data.STORAGE_TYPE_OPTIONS, key="storage_type", horizontal=True)
        st.number_input("보관 기간 (일)", min_value=1, step=1, key="storage_duration")
        st.divider() # Add divider after storage section if it appears

    # Special Notes
    st.header("🗒️ 고객 요구사항")
    st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes", placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등")