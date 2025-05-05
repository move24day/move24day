# ui_tab1.py (Using st.form, removed key from file_uploader, max 5 images)
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
        STATE_KEYS_TO_SAVE,
        prepare_state_for_save,
        load_state_from_data
    )
    # Ensure callbacks needed are imported
    from callbacks import sync_move_type, update_selected_gdrive_id, update_basket_quantities
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
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("JSON 검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
                st.session_state.loaded_images = {} # Clear previously loaded images on new search
                st.session_state.gdrive_image_files = [] # Clear associated image file list
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 JSON 검색 중..."): results = gdrive.find_files_by_name_contains(search_term_strip, mime_types="application/json")
                    if results:
                        st.session_state.gdrive_search_results = results; st.session_state.gdrive_file_options_map = {res['name']: res['id'] for res in results}
                        first_result_id = results[0].get('id'); st.session_state.gdrive_selected_file_id = first_result_id
                        st.session_state.gdrive_selected_filename = next((name for name, fid in st.session_state.gdrive_file_options_map.items() if fid == first_result_id), None)
                        st.success(f"✅ {len(results)}개 JSON 파일 검색 완료.")
                    else:
                        st.session_state.gdrive_search_results = []; st.session_state.gdrive_file_options_map = {}
                        st.session_state.gdrive_selected_file_id = None; st.session_state.gdrive_selected_filename = None
                        st.warning("⚠️ 해당 검색어의 JSON 견적 파일이 없습니다.")
                else: st.warning("⚠️ 검색어를 입력하세요.")
            if st.session_state.get('gdrive_search_results'):
                 file_options_display = list(st.session_state.gdrive_file_options_map.keys()); current_selection_index = 0
                 if st.session_state.gdrive_selected_filename in file_options_display:
                     try: current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                     except ValueError: current_selection_index = 0
                 # Use a unique key for the selectbox widget
                 st.selectbox( "불러올 JSON 파일 선택:", options=file_options_display, key="gdrive_selected_filename_widget", index=current_selection_index, on_change=update_selected_gdrive_id )
                 # Initial sync if needed
                 if st.session_state.gdrive_selected_filename and not st.session_state.gdrive_selected_file_id: update_selected_gdrive_id()
            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    st.write("--- DEBUG: Loading Start ---") # Debug Start
                    with st.spinner(f"🔄 견적 데이터 로딩 중..."): loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        # Pass the callback reference correctly
                        load_success = load_state_from_data(loaded_content, callbacks.update_basket_quantities)
                        if load_success:
                            st.success("✅ 견적 데이터 로딩 완료.")
                            image_filenames_to_load = st.session_state.get("gdrive_image_files", [])
                            st.write(f"--- DEBUG: Image filenames found in JSON: {image_filenames_to_load} ---") # Debug filenames
                            if image_filenames_to_load:
                                st.session_state.loaded_images = {}
                                num_images = len(image_filenames_to_load)
                                img_load_bar = st.progress(0, text=f"🖼️ 이미지 로딩 중... (0/{num_images})"); loaded_count = 0
                                for i, img_filename in enumerate(image_filenames_to_load):
                                     st.write(f"--- DEBUG: Processing image file: {img_filename} ---") # Debug current image
                                     img_file_id = None # Initialize img_file_id
                                     with st.spinner(f"이미지 '{img_filename}' 검색 중..."): img_file_id = gdrive.find_file_id_by_exact_name(img_filename) # Find by name (no mime type)
                                     st.write(f"--- DEBUG: Found Image File ID: {img_file_id} for {img_filename} ---") # Debug found ID
                                     if img_file_id:
                                         img_bytes = None # Initialize img_bytes
                                         with st.spinner(f"이미지 '{img_filename}' 다운로드 중..."): img_bytes = gdrive.download_file_bytes(img_file_id) # Attempt download
                                         if img_bytes:
                                             st.session_state.loaded_images[img_filename] = img_bytes; loaded_count += 1
                                             st.write(f"--- DEBUG: Successfully downloaded and stored: {img_filename} ---") # Debug success
                                             progress_val = (i + 1) / num_images; img_load_bar.progress(progress_val, text=f"🖼️ 이미지 로딩 중... ({loaded_count}/{num_images})")
                                         else: st.warning(f"⚠️ 이미지 '{img_filename}' (ID:{img_file_id}) 다운로드 실패."); st.write(f"--- DEBUG: Download FAILED for: {img_filename} (ID: {img_file_id}) ---") # Debug failure
                                     else: st.warning(f"⚠️ 저장된 이미지 파일 '{img_filename}'을 Google Drive에서 찾을 수 없습니다."); st.write(f"--- DEBUG: Image file not found on Drive: {img_filename} ---") # Debug not found
                                     time.sleep(0.1) # Keep delay
                                img_load_bar.empty()
                                if loaded_count > 0: st.success(f"✅ 이미지 {loaded_count}개 로딩 완료.")
                                if loaded_count != num_images: st.warning(f"⚠️ {num_images - loaded_count}개 이미지 로딩 실패 또는 찾을 수 없음.")
                                st.write(f"--- DEBUG: Final loaded_images keys: {list(st.session_state.loaded_images.keys())} ---") # Debug final keys
                            else: st.write("--- DEBUG: No image filenames found in JSON to load. ---") # Debug no images listed
                        # Error handled in load_state_from_data
                    else: st.write("--- DEBUG: Failed to load JSON content. ---") # Debug JSON load fail
                    st.write("--- DEBUG: Loading End ---") # Debug End


# --- Save Section (Using st.form, removed key from file_uploader) ---
        with col_save:
            st.markdown("**현재 견적 저장**")
            with st.form(key="save_quote_form"):
                # ... (파일 이름 예시 등 기존 코드) ...
                try: kst_ex = pytz.timezone("Asia/Seoul"); now_ex_str = datetime.now(kst_ex).strftime('%y%m%d')
                except: now_ex_str = datetime.now().strftime('%y%m%d')
                phone_ex = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4, default="XXXX")
                quote_base_name = f"{now_ex_str}-{phone_ex}"; example_json_fname = f"{quote_base_name}.json"
                st.caption(f"JSON 파일명 형식: `{example_json_fname}`"); st.caption(f"사진 파일명 형식: `{quote_base_name}_사진1.png` 등")

                uploaded_image_files_in_form = st.file_uploader( "사진 첨부 (최대 5장):", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'] )

                if uploaded_image_files_in_form and len(uploaded_image_files_in_form) > 5: st.warning("⚠️ 사진은 최대 5장까지만 첨부 및 저장됩니다. 5장을 초과한 파일은 저장되지 않습니다.", icon="⚠️")
                st.caption("JSON(견적 데이터) 파일이 덮어쓰기됩니다. 사진은 매번 새로 업로드됩니다.")
                submitted = st.form_submit_button("💾 Google Drive에 저장")

                if submitted:
                    current_uploaded_files = uploaded_image_files_in_form or []
                    if len(current_uploaded_files) > 5: st.warning("5장을 초과한 이미지는 제외하고 저장합니다.", icon="⚠️")
                    files_to_upload = current_uploaded_files[:5]
                    customer_phone = st.session_state.get('customer_phone', ''); phone_part = utils.extract_phone_number_part(customer_phone, length=4)

                    if phone_part == "번호없음" or not customer_phone.strip():
                         st.error("⚠️ 저장 실패: 고객 전화번호(뒤 4자리 포함)를 먼저 입력해주세요.")
                    else:
                        try: kst_save = pytz.timezone("Asia/Seoul"); now_save = datetime.now(kst_save)
                        except: now_save = datetime.now()
                        date_str = now_save.strftime('%y%m%d'); base_save_name = f"{date_str}-{phone_part}"; json_filename = f"{base_save_name}.json"

                        # --- 이미지 업로드 및 파일명 저장 수정 ---
                        saved_image_names = [] # 실제 저장된 파일명을 담을 리스트
                        num_images_to_upload = len(files_to_upload); img_upload_bar = None
                        if num_images_to_upload > 0: img_upload_bar = st.progress(0, text=f"🖼️ 이미지 업로드 중... (0/{num_images_to_upload})")
                        upload_errors = False

                        for i, uploaded_file in enumerate(files_to_upload):
                            original_filename = uploaded_file.name
                            _, extension = os.path.splitext(original_filename)
                            # 1. 원하는 파일명 생성 (기존 방식)
                            desired_drive_image_filename = f"{base_save_name}_사진{i+1}{extension}"

                            with st.spinner(f"이미지 '{desired_drive_image_filename}' 업로드 시도 중..."):
                                image_bytes = uploaded_file.getvalue()
                                # 2. 수정된 save_image_file 호출 (고유 이름 처리 내장됨)
                                save_img_result = gdrive.save_image_file(desired_drive_image_filename, image_bytes)

                            # 3. 결과 확인 및 실제 저장된 이름 사용
                            if save_img_result and save_img_result.get('id'):
                                 # --- !!! 중요: 반환된 실제 파일 이름 사용 !!! ---
                                 actual_saved_name = save_img_result.get('name', desired_drive_image_filename) # Drive가 반환한 이름 사용
                                 saved_image_names.append(actual_saved_name) # 실제 저장된 이름 추가
                                 print(f"DEBUG [Save]: Image {i+1} saved. Desired: '{desired_drive_image_filename}', Actual: '{actual_saved_name}'")
                                 if img_upload_bar:
                                     progress_val = (i + 1) / num_images_to_upload
                                     img_upload_bar.progress(progress_val, text=f"🖼️ 이미지 업로드 중... ({i+1}/{num_images_to_upload})")
                            else:
                                 st.error(f"❌ 이미지 '{original_filename}' 업로드 실패.")
                                 upload_errors = True
                            # time.sleep(0.1) # Drive API 호출 빈도 조절 필요시 사용

                        if img_upload_bar: img_upload_bar.empty()
                        if not upload_errors and num_images_to_upload > 0: st.success(f"✅ 이미지 {num_images_to_upload}개 업로드 완료.")
                        elif upload_errors: st.warning("⚠️ 일부 이미지 업로드에 실패했습니다.")
                        # --- 수정 완료 ---

                        # JSON 저장을 위해 상태 업데이트 (실제 저장된 이름 사용)
                        st.session_state.gdrive_image_files = saved_image_names
                        state_data_to_save = prepare_state_for_save() # gdrive_image_files 포함

                        # JSON 파일 저장
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 견적 데이터 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save)
                            if save_json_result and save_json_result.get('id'):
                                st.success(f"✅ '{json_filename}' 저장/업데이트 완료.")
                            else:
                                st.error(f"❌ '{json_filename}' 저장 중 오류 발생.")
                        except TypeError as json_err: st.error(f"❌ 저장 실패: 데이터를 JSON으로 변환 중 오류 발생 - {json_err}")
                        except Exception as save_err: st.error(f"❌ '{json_filename}' 파일 저장 중 예외 발생: {save_err}")
            # --- End Form ---
    st.divider()

    # --- Customer Info Section ---
    st.header("📝 고객 기본 정보")
    # Ensure MOVE_TYPE_OPTIONS is available
    move_type_options_tab1 = globals().get('MOVE_TYPE_OPTIONS')
    if move_type_options_tab1:
        try: current_index_tab1 = move_type_options_tab1.index(st.session_state.base_move_type)
        except ValueError: current_index_tab1 = 0
        st.radio( "🏢 **기본 이사 유형**", options=move_type_options_tab1, index=current_index_tab1, horizontal=True, key="base_move_type_widget_tab1", on_change=sync_move_type, args=("base_move_type_widget_tab1",) )
    else: st.warning("이사 유형 옵션을 로드할 수 없습니다.")
    col_opts1, col_opts2 = st.columns(2);
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name"); st.text_input("📍 출발지 주소", key="from_location")
        if st.session_state.get('apply_long_distance'): st.selectbox("🛣️ 장거리 구간 선택", data.long_distance_options if hasattr(data,'long_distance_options') else [], key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1"); st.selectbox("🛠️ 출발지 작업 방법", data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else [], key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
    with col2:
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678"); st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소")
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2"); st.selectbox("🛠️ 도착지 작업 방법", data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else [], key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date):
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date"); st.caption(f"⏱️ 견적 생성일: {utils.get_current_kst_time_str() if hasattr(utils, 'get_current_kst_time_str') else ''}")
    st.divider()

    # --- Display Loaded Images ---
    if st.session_state.get("loaded_images"):
        st.subheader("🖼️ 불러온 사진"); loaded_images_dict = st.session_state.loaded_images
        num_cols = min(len(loaded_images_dict), 4)
        if num_cols > 0:
            cols = st.columns(num_cols); i = 0
            for filename, img_bytes in loaded_images_dict.items():
                with cols[i % num_cols]: st.image(img_bytes, caption=filename, use_container_width=True)
                i += 1
        st.divider()

    # --- Storage Move Info / Special Notes ---
    if st.session_state.get('is_storage_move'):
        st.subheader("📦 보관이사 추가 정보"); st.radio("보관 유형 선택:", options=data.STORAGE_TYPE_OPTIONS if hasattr(data, 'STORAGE_TYPE_OPTIONS') else [], key="storage_type", horizontal=True)
        st.number_input("보관 기간 (일)", min_value=1, step=1, key="storage_duration"); st.divider()
    st.header("🗒️ 고객 요구사항")
    st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes", placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등")

# --- End of render_tab1 function ---