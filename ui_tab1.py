# ui_tab1.py (Uploader outside form, WITH key, NO state reset, NO explicit rerun in submit)
import streamlit as st
from datetime import datetime, date
import pytz
import json
import os
import time
import traceback

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

    # === Google Drive Section ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적(JSON) 및 사진 파일을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        # --- Load Section ---
        with col_load:
            # (Load Section Code - unchanged, based on last working version)
            st.markdown("**견적 불러오기**"); search_term = st.text_input("JSON 검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
                st.session_state.loaded_images = {}; st.session_state.gdrive_image_files = []
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 JSON 검색 중..."): results = gdrive.find_files_by_name_contains(search_term_strip, mime_types="application/json")
                    if results: st.session_state.gdrive_search_results = results; st.session_state.gdrive_file_options_map = {r['name']: r['id'] for r in results}; first_result_id = results[0].get('id'); st.session_state.gdrive_selected_file_id = first_result_id; st.session_state.gdrive_selected_filename = next((n for n,i in st.session_state.gdrive_file_options_map.items() if i==st.session_state.gdrive_selected_file_id), None); st.success(f"✅ {len(results)}개 검색 완료.")
                    else: st.session_state.gdrive_search_results = []; st.session_state.gdrive_file_options_map = {}; st.session_state.gdrive_selected_file_id = None; st.session_state.gdrive_selected_filename = None; st.warning("⚠️ 해당 파일 없음.")
                else: st.warning("⚠️ 검색어를 입력하세요.")
            if st.session_state.get('gdrive_search_results'):
                 file_options_display = list(st.session_state.gdrive_file_options_map.keys()); current_selection_index = 0
                 if st.session_state.gdrive_selected_filename in file_options_display:
                     try: current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                     except ValueError: current_selection_index = 0
                 on_change_callback_gdrive = getattr(callbacks, 'update_selected_gdrive_id', None)
                 st.selectbox("불러올 JSON 파일 선택:", file_options_display, key="gdrive_selected_filename_widget", index=current_selection_index, on_change=on_change_callback_gdrive)
                 if st.session_state.gdrive_selected_filename and not st.session_state.gdrive_selected_file_id and on_change_callback_gdrive: on_change_callback_gdrive()
            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    st.session_state.loaded_images = {}
                    with st.spinner("..."): loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', None);
                        if not update_basket_callback_ref: st.error("Basket callback 없음!"); update_basket_callback_ref = lambda: None
                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)
                        if load_success:
                            st.success("✅ 로딩 완료."); image_filenames_to_load = st.session_state.get("gdrive_image_files", [])
                            if image_filenames_to_load:
                                num_images=len(image_filenames_to_load); img_load_bar=st.progress(0, text=f"🖼️ 이미지 로딩 (0/{num_images})"); loaded_count=0
                                for i, img_filename in enumerate(image_filenames_to_load):
                                     img_file_id = None;
                                     with st.spinner(f"이미지 '{img_filename}' 검색"): img_file_id = gdrive.find_file_id_by_exact_name(img_filename)
                                     if img_file_id:
                                         img_bytes = None;
                                         with st.spinner(f"이미지 '{img_filename}' 다운로드"): img_bytes = gdrive.download_file_bytes(img_file_id)
                                         if img_bytes: st.session_state.loaded_images[img_filename] = img_bytes; loaded_count += 1; progress_val = (i + 1) / num_images; img_load_bar.progress(progress_val, text=f"🖼️ 이미지 로딩 ({loaded_count}/{num_images})")
                                         else: st.warning(f"⚠️ 이미지 '{img_filename}' 다운로드 실패.")
                                     else: st.warning(f"⚠️ 이미지 파일 '{img_filename}' 못 찾음.")
                                     time.sleep(0.1)
                                img_load_bar.empty()
                                if loaded_count > 0: st.success(f"✅ 이미지 {loaded_count}개 로딩 완료.")
                                if loaded_count != num_images: st.warning(f"⚠️ {num_images - loaded_count}개 이미지 로딩 실패/못 찾음.")
                    else: st.error("❌ JSON 파일 로딩 실패.")
                # Removed explicit rerun from here

        # --- Save Section ---
        with col_save:
            st.markdown("**현재 견적 저장**")

            # --- File Uploader OUTSIDE the form, WITH key ---
            st.file_uploader(
                "사진 첨부:",
                accept_multiple_files=True,
                type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
                key="quote_image_uploader"  # <-- Key is Present
            )
            # --- End File Uploader ---

            with st.form(key="save_quote_form"):
                # (Filename examples, captions - unchanged)
                try: kst_ex=pytz.timezone("Asia/Seoul"); now_ex_str=datetime.now(kst_ex).strftime('%y%m%d')
                except Exception: now_ex_str = datetime.now().strftime('%y%m%d')
                phone_ex = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4, default="XXXX")
                quote_base_name = f"{now_ex_str}-{phone_ex}"; example_json_fname = f"{quote_base_name}.json"; st.caption(f"JSON: `{example_json_fname}`"); st.caption(f"사진: `{quote_base_name}_사진1.png` 등")
                st.caption("JSON 파일은 덮어쓰기, 사진은 항상 새로 업로드됩니다.")
                # --- Submit button ---
                submitted = st.form_submit_button("💾 Google Drive에 저장")

                if submitted:
                    # --- Access files via session state KEY ---
                    current_uploaded_files = st.session_state.get("quote_image_uploader", []) or []
                    files_to_upload = current_uploaded_files

                    customer_phone = st.session_state.get('customer_phone', ''); phone_part = utils.extract_phone_number_part(customer_phone, length=4)

                    if phone_part == "번호없음" or not customer_phone.strip():
                         st.error("⚠️ 저장 실패: 고객 전화번호 필요.")
                    else:
                        save_successful = False
                        # (Generate filenames - unchanged)
                        try: kst_save = pytz.timezone("Asia/Seoul"); now_save = datetime.now(kst_save)
                        except Exception: now_save = datetime.now()
                        date_str = now_save.strftime('%y%m%d'); base_save_name = f"{date_str}-{phone_part}"; json_filename = f"{base_save_name}.json"

                        # --- Process and Upload Images Immediately ---
                        # (Image Upload Logic - unchanged)
                        saved_image_names = []
                        num_images_to_upload = len(files_to_upload); img_upload_bar = None
                        if num_images_to_upload > 0: img_upload_bar = st.progress(0, text=f"🖼️ 이미지 업로드 중... (0/{num_images_to_upload})")
                        upload_errors = False
                        for i, uploaded_file_obj in enumerate(files_to_upload):
                            if uploaded_file_obj is None: continue
                            original_filename = uploaded_file_obj.name; _, extension = os.path.splitext(original_filename)
                            desired_drive_image_filename = f"{base_save_name}_사진{i+1}{extension}"
                            with st.spinner(f"이미지 '{desired_drive_image_filename}' 처리 및 업로드 중..."):
                                try:
                                    image_bytes = uploaded_file_obj.getvalue()
                                    save_img_result = gdrive.save_image_file(desired_drive_image_filename, image_bytes)
                                    if save_img_result and save_img_result.get('id'):
                                         actual_saved_name = save_img_result.get('name', desired_drive_image_filename); saved_image_names.append(actual_saved_name)
                                         if img_upload_bar: progress_val = (i + 1) / num_images_to_upload; img_upload_bar.progress(progress_val, text=f"🖼️ 이미지 업로드 중... ({i+1}/{num_images_to_upload})")
                                    else: st.error(f"❌ 이미지 '{original_filename}' 업로드 실패."); upload_errors = True
                                except Exception as read_err: st.error(f"❌ 이미지 '{original_filename}' 처리 오류: {read_err}"); upload_errors = True; traceback.print_exc();
                        if img_upload_bar: img_upload_bar.empty()
                        if not upload_errors and num_images_to_upload > 0: st.success(f"✅ 이미지 {num_images_to_upload}개 업로드 완료.")
                        elif upload_errors: st.warning("⚠️ 일부 이미지 업로드 실패.")
                        # --- End Image Processing ---

                        st.session_state.gdrive_image_files = saved_image_names # Update state
                        state_data_to_save = prepare_state_for_save()

                        # --- Save JSON ---
                        json_save_success = False
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 데이터 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save)
                            if save_json_result and save_json_result.get('id'): st.success(f"✅ '{json_filename}' 저장 완료."); json_save_success = True
                            else: st.error(f"❌ '{json_filename}' 저장 실패.")
                        except Exception as save_err: st.error(f"❌ '{json_filename}' 저장 중 예외: {save_err}"); traceback.print_exc()
                        # --- End JSON Save ---

                        # --- REMOVED State Reset Attempt and Explicit Rerun ---
            # --- End Form ---

    st.divider()

    # --- Customer Info Section ---
    # (Code unchanged, omitted for brevity)
    st.header("📝 고객 기본 정보"); # ... Rest of customer info inputs ...

    # --- Display Loaded Images ---
    # (Code unchanged, omitted for brevity)
    if st.session_state.get("loaded_images"): st.subheader("🖼️ 불러온 사진"); # ... Rest of image display ...

    # --- Storage Move Info / Special Notes ---
    # (Code unchanged, omitted for brevity)
    if st.session_state.get('is_storage_move'): st.subheader("📦 보관이사 추가 정보"); # ... Rest of storage/notes ...

# --- End of render_tab1 function ---