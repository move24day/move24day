# ui_tab1.py (파일 업로더를 폼 내부로 이동하여 상태 관리 안정화)
import streamlit as st
from datetime import datetime, date
import pytz
import json
import os
import time
import traceback
# StreamlitAPIException import는 더 이상 필요 없을 수 있으나, 만약을 위해 유지 가능
from streamlit.errors import StreamlitAPIException

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
            # (Load Section Code - 기존과 동일, 변경 없음)
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("JSON 검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
                # Reset state related to previous loads
                st.session_state.loaded_images = {}
                st.session_state.gdrive_image_files = []
                st.session_state.gdrive_search_results = []
                st.session_state.gdrive_file_options_map = {}
                st.session_state.gdrive_selected_file_id = None
                st.session_state.gdrive_selected_filename = None

                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 JSON 검색 중..."):
                        results = gdrive.find_files_by_name_contains(search_term_strip, mime_types="application/json")
                    if results:
                        st.session_state.gdrive_search_results = results
                        st.session_state.gdrive_file_options_map = {r['name']: r['id'] for r in results}
                        # Select the first result by default
                        st.session_state.gdrive_selected_filename = results[0].get('name')
                        st.session_state.gdrive_selected_file_id = results[0].get('id')
                        st.success(f"✅ {len(results)}개 검색 완료.")
                        st.rerun() # Ensure selectbox updates with new default
                    else:
                        st.warning("⚠️ 해당 파일 없음.")
                else:
                    st.warning("⚠️ 검색어를 입력하세요.")

            # File selection dropdown
            if st.session_state.get('gdrive_search_results'):
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                current_selection_index = 0
                if st.session_state.gdrive_selected_filename in file_options_display:
                    try:
                        current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                    except ValueError:
                        current_selection_index = 0 # Default to first if somehow name is invalid

                on_change_callback_gdrive = getattr(callbacks, 'update_selected_gdrive_id', None)
                st.selectbox(
                    "불러올 JSON 파일 선택:",
                    file_options_display,
                    key="gdrive_selected_filename_widget",
                    index=current_selection_index,
                    on_change=on_change_callback_gdrive # Callback updates ID based on name
                )
                # Ensure ID is synced if callback exists and wasn't triggered immediately (e.g., direct state change)
                if st.session_state.gdrive_selected_filename and not st.session_state.gdrive_selected_file_id and on_change_callback_gdrive:
                     on_change_callback_gdrive()

            # Load button
            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn"):
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    st.session_state.loaded_images = {} # Clear previous images before loading new ones
                    with st.spinner(f"🔄 '{st.session_state.gdrive_selected_filename}' 로딩 중..."):
                        loaded_content = gdrive.load_json_file(json_file_id) # Use helper function
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', None)
                        if not update_basket_callback_ref:
                            st.error("Basket callback 없음!")
                            update_basket_callback_ref = lambda: None # No-op fallback

                        # Load state from the dictionary
                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)

                        if load_success:
                            st.success("✅ 견적 데이터 로딩 완료.")
                            # --- Image Loading Logic (after successful state load) ---
                            image_filenames_to_load = st.session_state.get("gdrive_image_files", []) # Get image filenames from loaded state
                            if image_filenames_to_load:
                                num_images = len(image_filenames_to_load)
                                img_load_bar = st.progress(0, text=f"🖼️ 이미지 로딩 시작 (0/{num_images})")
                                loaded_count = 0
                                for i, img_filename in enumerate(image_filenames_to_load):
                                    img_file_id = None
                                    progress_text = f"🖼️ 이미지 '{img_filename}' ({i+1}/{num_images}) 로딩 중..."
                                    img_load_bar.progress((i + 0.1) / num_images, text=progress_text) # Show progress early

                                    # Find image file ID on Drive
                                    with st.spinner(f"이미지 '{img_filename}' 검색 중..."):
                                        img_file_id = gdrive.find_file_id_by_exact_name(img_filename) # Search by exact name

                                    if img_file_id:
                                        # Download image bytes
                                        img_bytes = None
                                        with st.spinner(f"이미지 '{img_filename}' 다운로드 중..."):
                                             img_bytes = gdrive.download_file_bytes(img_file_id)

                                        if img_bytes:
                                            st.session_state.loaded_images[img_filename] = img_bytes
                                            loaded_count += 1
                                        else:
                                            st.warning(f"⚠️ 이미지 '{img_filename}' 다운로드 실패.")
                                    else:
                                        st.warning(f"⚠️ 이미지 파일 '{img_filename}'을(를) Drive에서 찾을 수 없습니다.")

                                    # Update progress bar fully for this image
                                    img_load_bar.progress((i + 1) / num_images, text=f"🖼️ 이미지 로딩 ({loaded_count}/{num_images})")
                                    time.sleep(0.1) # Small delay

                                img_load_bar.empty() # Remove progress bar on completion
                                if loaded_count > 0:
                                    st.success(f"✅ 이미지 {loaded_count}개 로딩 완료.")
                                if loaded_count != num_images:
                                    st.warning(f"⚠️ {num_images - loaded_count}개의 이미지를 로딩하지 못했습니다.")
                                # --- End Image Loading ---
                            else:
                                st.info("ℹ️ 이 견적에는 저장된 이미지가 없습니다.")

                            # Trigger a rerun to ensure all UI elements reflect the loaded state
                            st.rerun()

                        else:
                            st.error("❌ 저장된 데이터 형식 오류로 로딩 실패.")
                    else:
                        st.error(f"❌ '{st.session_state.gdrive_selected_filename}' 파일 로딩 또는 JSON 파싱 실패.")
                else:
                     st.warning("⚠️ 불러올 파일을 선택해주세요.")


        # --- Save Section ---
        with col_save:
            st.markdown("**현재 견적 저장**")

            # --- Form 시작 ---
            # 파일 업로더 및 저장 버튼을 form 내부에 배치
            with st.form(key="save_quote_form"):

                # --- 파일 업로더 (폼 내부) ---
                # key는 그대로 사용해도 되지만, 명확성을 위해 변경 가능 (예: quote_image_uploader_in_form)
                # try-except 블록은 form 내부로 이동하면서 필요성이 낮아졌으므로 제거 (필요시 복구)
                uploaded_files_in_form = st.file_uploader(
                    "사진 첨부 (저장 시 함께 업로드):",
                    accept_multiple_files=True,
                    type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
                    key="quote_image_uploader" # 위젯 키
                )
                # --- 파일 업로더 이동 완료 ---

                # Filename examples and captions
                try:
                    kst_ex = pytz.timezone("Asia/Seoul")
                    now_ex_str = datetime.now(kst_ex).strftime('%y%m%d')
                except Exception:
                    now_ex_str = datetime.now().strftime('%y%m%d')
                phone_ex = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4, default="XXXX")
                quote_base_name = f"{now_ex_str}-{phone_ex}"
                example_json_fname = f"{quote_base_name}.json"
                st.caption(f"JSON 파일명 예시: `{example_json_fname}`")
                st.caption(f"사진 파일명 예시: `{quote_base_name}_사진1.png` 등")
                st.caption("ℹ️ JSON 파일은 같은 이름으로 저장 시 덮어쓰기되고, 사진은 항상 새로 업로드됩니다.")

                # Form submission button
                submitted = st.form_submit_button("💾 Google Drive에 저장")

                if submitted:
                    # --- 저장 로직 (폼 제출 시 실행) ---
                    # 폼 내부의 파일 업로더 상태를 사용
                    files_to_upload = uploaded_files_in_form or [] # 위젯 키 사용

                    customer_phone = st.session_state.get('customer_phone', '')
                    phone_part = utils.extract_phone_number_part(customer_phone, length=4)

                    # 전화번호 확인
                    if phone_part == "번호없음" or not customer_phone.strip():
                        st.error("⚠️ 저장 실패: 고객 전화번호가 필요합니다.")
                    else:
                        # Generate filenames
                        try:
                            kst_save = pytz.timezone("Asia/Seoul")
                            now_save = datetime.now(kst_save)
                        except Exception:
                            now_save = datetime.now()
                        date_str = now_save.strftime('%y%m%d')
                        base_save_name = f"{date_str}-{phone_part}"
                        json_filename = f"{base_save_name}.json"

                        # --- 이미지 처리 및 업로드 ---
                        saved_image_names = []
                        num_images_to_upload = len(files_to_upload)
                        img_upload_bar = None
                        if num_images_to_upload > 0:
                            img_upload_bar = st.progress(0, text=f"🖼️ 이미지 업로드 시작 (0/{num_images_to_upload})")
                        upload_errors = False

                        for i, uploaded_file_obj in enumerate(files_to_upload):
                            if uploaded_file_obj is None: continue # 혹시 모를 NoneType 방지

                            original_filename = uploaded_file_obj.name
                            _, extension = os.path.splitext(original_filename)
                            # Google Drive에 저장될 최종 이미지 파일명 생성
                            desired_drive_image_filename = f"{base_save_name}_사진{i+1}{extension}"

                            progress_text = f"🖼️ '{original_filename}' ({i+1}/{num_images_to_upload}) 업로드 중..."
                            if img_upload_bar: img_upload_bar.progress((i + 0.1) / num_images_to_upload, text=progress_text)

                            # 이미지 파일 읽기 및 저장
                            with st.spinner(f"이미지 '{original_filename}' 처리 및 업로드 중..."):
                                try:
                                    # 파일을 bytes 형태로 읽음
                                    image_bytes = uploaded_file_obj.getvalue()
                                    # Google Drive에 저장 (고유 이름 처리 포함)
                                    save_img_result = gdrive.save_image_file(desired_drive_image_filename, image_bytes)

                                    if save_img_result and save_img_result.get('id'):
                                        # 실제 저장된 파일명 사용 (고유 이름 처리로 인해 변경될 수 있음)
                                        actual_saved_name = save_img_result.get('name', desired_drive_image_filename)
                                        saved_image_names.append(actual_saved_name)
                                    else:
                                        st.error(f"❌ 이미지 '{original_filename}' 업로드 실패.")
                                        upload_errors = True
                                except Exception as read_err:
                                    st.error(f"❌ 이미지 '{original_filename}' 처리 오류: {read_err}")
                                    upload_errors = True
                                    traceback.print_exc()

                            # 프로그레스 바 업데이트
                            if img_upload_bar: img_upload_bar.progress((i + 1) / num_images_to_upload, text=f"🖼️ 이미지 업로드 ({i+1}/{num_images_to_upload})")

                        # 프로그레스 바 제거 및 결과 메시지
                        if img_upload_bar: img_upload_bar.empty()
                        if not upload_errors and num_images_to_upload > 0:
                            st.success(f"✅ 이미지 {num_images_to_upload}개 업로드 완료.")
                        elif upload_errors:
                            st.warning("⚠️ 일부 이미지 업로드에 실패했습니다.")
                        # --- 이미지 처리 완료 ---

                        # 저장된 이미지 파일명 리스트를 세션 상태에 업데이트
                        st.session_state.gdrive_image_files = saved_image_names

                        # 현재 세션 상태를 저장용 데이터로 준비
                        state_data_to_save = prepare_state_for_save()

                        # --- JSON 파일 저장 ---
                        json_save_success = False
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 데이터 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save) # JSON 저장 함수 호출

                            if save_json_result and save_json_result.get('id'):
                                st.success(f"✅ 견적 데이터 '{json_filename}' 저장 완료.")
                                json_save_success = True
                                # 저장 성공 후 파일 업로더 상태 초기화 (선택적)
                                # st.session_state.quote_image_uploader = [] # 주석 처리됨 - 필요시 활성화
                            else:
                                st.error(f"❌ 견적 데이터 '{json_filename}' 저장 실패.")
                        except Exception as save_err:
                            st.error(f"❌ '{json_filename}' 저장 중 예외 발생: {save_err}")
                            traceback.print_exc()
                        # --- JSON 저장 완료 ---

                        # 저장 완료 후 페이지 새로고침이나 상태 초기화는 필요에 따라 추가 가능
                        # 예: st.rerun() # 저장이 UI에 즉시 반영되어야 하는 경우

            # --- End Form ---

    st.divider() # --- 구분선 ---

    # === Customer Info Section ===
    # (고객 정보 섹션 - 기존과 동일, 변경 없음)
    st.header("📝 고객 기본 정보")
    move_type_options_tab1 = globals().get('MOVE_TYPE_OPTIONS')
    sync_move_type_callback_ref = getattr(callbacks, 'sync_move_type', None)

    if move_type_options_tab1:
        try:
            current_index_tab1 = move_type_options_tab1.index(st.session_state.base_move_type)
        except ValueError:
            current_index_tab1 = 0
        st.radio( "🏢 **기본 이사 유형**",
                  options=move_type_options_tab1,
                  index=current_index_tab1,
                  horizontal=True,
                  key="base_move_type_widget_tab1",
                  on_change=sync_move_type_callback_ref,
                  args=("base_move_type_widget_tab1",) # 콜백 인자 전달
                  )
    else:
        st.warning("이사 유형 옵션을 로드할 수 없습니다.")

    col_opts1, col_opts2 = st.columns(2);
    with col_opts1:
        st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2:
        st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name")
        st.text_input("📍 출발지 주소", key="from_location")
        if st.session_state.get('apply_long_distance'):
             ld_options = data.long_distance_options if hasattr(data,'long_distance_options') else []
             st.selectbox("🛣️ 장거리 구간 선택", ld_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1")
        method_options = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []
        st.selectbox("🛠️ 출발지 작업 방법", method_options, key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
    with col2:
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678")
        st.text_input("📧 이메일", key="customer_email", placeholder="email@example.com") # Email input
        st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소")
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2")
        method_options_to = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []
        st.selectbox("🛠️ 도착지 작업 방법", method_options_to, key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택")

    # 이사 예정일 입력 (기본값 처리 포함)
    current_moving_date_val = st.session_state.get('moving_date')
    if not isinstance(current_moving_date_val, date):
         try:
             kst_def = pytz.timezone("Asia/Seoul")
             default_date_def = datetime.now(kst_def).date()
         except Exception:
             default_date_def = datetime.now().date()
         st.session_state.moving_date = default_date_def # Set default if invalid
    st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date")
    kst_time_str = utils.get_current_kst_time_str() if utils and hasattr(utils, 'get_current_kst_time_str') else ''
    st.caption(f"⏱️ 견적 생성일: {kst_time_str}")

    st.divider() # --- 구분선 ---

    # === Display Loaded Images ===
    # (불러온 이미지 표시 - 기존과 동일, 변경 없음)
    if st.session_state.get("loaded_images"):
        st.subheader("🖼️ 불러온 사진")
        loaded_images_dict = st.session_state.loaded_images
        num_loaded = len(loaded_images_dict)
        # Display images in columns (e.g., up to 4 columns)
        num_cols_display = min(num_loaded, 4)
        if num_cols_display > 0:
            cols_display = st.columns(num_cols_display)
            i = 0
            for filename, img_bytes in loaded_images_dict.items():
                with cols_display[i % num_cols_display]:
                    st.image(img_bytes, caption=filename, use_container_width=True)
                i += 1
        st.divider() # --- 구분선 ---

    # === Storage Move Info & Special Notes ===
    # (보관 이사 정보 / 고객 요구사항 - 기존과 동일, 변경 없음)
    if st.session_state.get('is_storage_move'):
        st.subheader("📦 보관이사 추가 정보")
        storage_options = data.STORAGE_TYPE_OPTIONS if hasattr(data, 'STORAGE_TYPE_OPTIONS') else []
        st.radio("보관 유형 선택:", options=storage_options, key="storage_type", horizontal=True)
        st.number_input("보관 기간 (일)", min_value=1, step=1, key="storage_duration")
        st.divider() # --- 구분선 ---

    st.header("🗒️ 고객 요구사항")
    st.text_area(
        "기타 특이사항이나 요청사항을 입력해주세요.",
        height=100,
        key="special_notes",
        placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등"
    )
# --- End of render_tab1 function ---