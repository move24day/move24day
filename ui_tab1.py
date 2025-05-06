# ui_tab1.py (Conditional rendering for Save Form)
import streamlit as st
from datetime import datetime, date
import pytz
import json
import os
import time

# Import necessary custom modules
try:
    import data
    import utils
    import google_drive_helper as gdrive # Use alias
    from state_manager import (
        MOVE_TYPE_OPTIONS,
        prepare_state_for_save,
        load_state_from_data
    )
    import callbacks # Ensure callbacks module exists and has necessary functions
except ImportError as ie:
    st.error(f"UI Tab 1: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 1: 모듈 로딩 중 오류 - {e}")
    st.stop()


def render_tab1():
    """Renders the UI for Tab 1: Customer Info and Google Drive."""

    # Initialize the flag if it doesn't exist
    if 'just_loaded_quote' not in st.session_state:
        st.session_state.just_loaded_quote = False

    # === Google Drive Section ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적(JSON) 및 사진 파일을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        # --- Load Section ---
        with col_load:
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("JSON 검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
                # Reset relevant states on new search
                st.session_state.loaded_images = {}
                st.session_state.gdrive_image_files = []
                st.session_state.just_loaded_quote = False # Reset flag on new search

                search_term_strip = search_term.strip()
                if search_term_strip:
                    # ... (Search logic - same as before) ...
                    if results:
                        # ... (Update state with search results - same as before) ...
                        st.success(f"✅ {len(results)}개 JSON 파일 검색 완료.")
                    else:
                        # ... (Handle no results - same as before) ...
                        st.warning("⚠️ 해당 검색어의 JSON 견적 파일이 없습니다.")
                else:
                    st.warning("⚠️ 검색어를 입력하세요.")

            # Selectbox for loaded files (same as before)
            if st.session_state.get('gdrive_search_results'):
                 # ... (Selectbox logic - same as before) ...
                 pass # Placeholder for brevity

            # Load button logic
            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    # --- REMOVED: Direct state assignment to uploader ---
                    # if 'quote_image_uploader' in st.session_state:
                    #     st.session_state.quote_image_uploader = []
                    st.session_state.loaded_images = {} # Reset display area

                    with st.spinner(f"🔄 견적 데이터 로딩 중..."):
                        loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', None)
                        if not update_basket_callback_ref:
                             st.error("Basket update callback not found!")
                             update_basket_callback_ref = lambda: None

                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)

                        if load_success:
                            st.success("✅ 견적 데이터 로딩 완료.")
                            # --- !!! Set the flag AFTER successful load !!! ---
                            st.session_state.just_loaded_quote = True
                            # --- Load images logic (same as before) ---
                            # ... (image loading code) ...
                        # else: handled in load_state_from_data
                    else:
                         st.error("❌ 선택된 JSON 파일 내용을 불러오는 데 실패했습니다.")
                # Trigger immediate rerun after button press to reflect state changes and flag
                st.rerun()


        # --- Save Section (Conditional Rendering) ---
        # Check the flag BEFORE rendering this section
        render_save_form = not st.session_state.get('just_loaded_quote', False)

        if render_save_form:
            with col_save:
                st.markdown("**현재 견적 저장**")
                with st.form(key="save_quote_form"):
                    # ... (Filename examples, etc.) ...

                    uploaded_image_files_in_form = st.file_uploader(
                        "사진 첨부 (최대 5장):",
                        accept_multiple_files=True,
                        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
                        key="quote_image_uploader"  # Keep static key
                    )

                    # ... (File limit warning, caption) ...
                    submitted = st.form_submit_button("💾 Google Drive에 저장")

                    if submitted:
                        # --- Reset the flag when save is attempted ---
                        st.session_state.just_loaded_quote = False
                        # ... (Existing save logic - same as before) ...
                        # ... (Includes clearing uploader on success) ...
        else:
            # Optionally, display a placeholder message in the save column
            with col_save:
                st.markdown("**현재 견적 저장**")
                st.info("견적을 불러왔습니다. 다른 작업을 수행하면 저장 양식이 다시 나타납니다.")
            # --- Reset the flag so the form appears on the NEXT rerun ---
            # This happens automatically because the script reruns after this point
            # without the 'just_loaded_quote' being set to True again.
            # We reset it to False explicitly if the save button is pressed (above).
            # For clarity, we can ensure it's False if we are in this 'else' block
            # although subsequent reruns without loading will naturally clear it.
            st.session_state.just_loaded_quote = False


    st.divider()

    # --- Customer Info Section ---
    # (This section remains unchanged)
    st.header("📝 고객 기본 정보")
    # ... (Rest of the customer info code) ...

    # --- Display Loaded Images ---
    # (This section remains unchanged)
    if st.session_state.get("loaded_images"):
        # ... (Image display code) ...
        pass # Placeholder

    # --- Storage Move Info / Special Notes ---
    # (This section remains unchanged)
    if st.session_state.get('is_storage_move'):
        # ... (Storage info code) ...
        pass # Placeholder
    st.header("🗒️ 고객 요구사항")
    # ... (Special notes text area) ...

# --- End of render_tab1 function ---