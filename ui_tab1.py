# ui_tab1.py
# ui_tab1.py (경유지 옵션, 도착 예정일, 보관 전기사용 옵션 추가, 이미지 업로드 기능 추가, 파일명 및 검색 로직 수정, UPLOAD_DIR 경로 수정 및 예외 처리)
import streamlit as st
from datetime import datetime, date, timedelta
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
    import callbacks
except ImportError as ie:
    st.error(f"UI Tab 1: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 1: 모듈 로딩 중 오류 - {e}")
    st.stop()

# --- 업로드 디렉토리 설정 (상대 경로 및 생성 로직 수정) ---
# 현재 ui_tab1.py 파일이 있는 디렉토리를 기준으로 uploads/images 폴더 경로 설정
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "images")

    if not os.path.exists(UPLOAD_DIR):
        try:
            os.makedirs(UPLOAD_DIR)
            print(f"INFO: Created UPLOAD_DIR at {UPLOAD_DIR}")
        except PermissionError:
            st.error(f"권한 오류: 업로드 디렉토리({UPLOAD_DIR}) 생성 권한이 없습니다. 해당 경로에 쓰기 권한을 확인하거나 다른 경로를 사용해주세요.")
            # 애플리케이션 실행에 치명적일 경우 st.stop() 고려
        except Exception as e_mkdir:
            st.error(f"오류: 업로드 디렉토리({UPLOAD_DIR}) 생성 중 예기치 않은 문제 발생: {e_mkdir}")
except Exception as e_path:
    st.error(f"오류: UPLOAD_DIR 경로 설정 중 문제 발생: {e_path}")
    UPLOAD_DIR = None # 경로 설정 실패 시 None으로 설정하여 이후 로직에서 확인 가능하도록


def render_tab1():
    """Renders the UI for Tab 1: Customer Info and Google Drive."""

    if UPLOAD_DIR is None: # UPLOAD_DIR 설정에 실패했으면 일부 기능을 비활성화하거나 오류 메시지 지속
        st.error("이미지 업로드 기능을 위한 디렉토리 설정에 실패하여 관련 기능 사용이 제한됩니다.")
        # 필요하다면 여기서 return 하여 탭 렌더링 중단

    # === Google Drive Section ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적(JSON) 파일을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        # --- Load Section ---
        with col_load:
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("검색 (전화번호 전체 또는 끝 4자리)", key="gdrive_search_term_tab1", help="전체 전화번호 또는 전화번호 끝 4자리를 입력하세요.")
            if st.button("🔍 견적 검색", key="gdrive_search_button_tab1"):
                st.session_state.gdrive_search_results = []
                st.session_state.gdrive_file_options_map = {}
                st.session_state.gdrive_selected_file_id = None
                st.session_state.gdrive_selected_filename = None
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 JSON 검색 중..."):
                        all_gdrive_results = gdrive.find_files_by_name_contains(search_term_strip, mime_types="application/json")

                    processed_results = []
                    if all_gdrive_results:
                        if len(search_term_strip) == 4 and search_term_strip.isdigit():
                            for r in all_gdrive_results:
                                file_name_stem = os.path.splitext(r['name'])[0]
                                if file_name_stem.endswith(search_term_strip):
                                    processed_results.append(r)
                        else:
                            processed_results = all_gdrive_results

                    if processed_results:
                        st.session_state.gdrive_search_results = processed_results
                        st.session_state.gdrive_file_options_map = {r['name']: r['id'] for r in processed_results}
                        st.session_state.gdrive_selected_filename = processed_results[0].get('name')
                        st.session_state.gdrive_selected_file_id = processed_results[0].get('id')
                        st.success(f"✅ {len(processed_results)}개 검색 완료.")
                        st.rerun() # 검색 결과 반영을 위해 rerun
                    else: st.warning("⚠️ 해당 파일 없음.")
                else: st.warning("⚠️ 검색어를 입력하세요.")

            if st.session_state.get('gdrive_search_results'):
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                current_selection_index = 0
                if st.session_state.gdrive_selected_filename in file_options_display:
                    try: current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                    except ValueError: current_selection_index = 0

                on_change_callback_gdrive = getattr(callbacks, 'update_selected_gdrive_id', None)
                st.selectbox(
                    "불러올 JSON 파일 선택:",
                    file_options_display,
                    key="gdrive_selected_filename_widget_tab1", # 키를 탭1용으로 명확히 구분
                    index=current_selection_index,
                    on_change=on_change_callback_gdrive
                )
                if st.session_state.gdrive_selected_filename and not st.session_state.gdrive_selected_file_id and on_change_callback_gdrive:
                    on_change_callback_gdrive() # 초기 선택 시 ID 업데이트

            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn_tab1"): # 키를 탭1용으로 명확히 구분
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    with st.spinner(f"🔄 '{st.session_state.gdrive_selected_filename}' 로딩 중..."):
                        loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', None)
                        if not update_basket_callback_ref:
                            st.error("Basket callback 없음!")
                            update_basket_callback_ref = lambda: None # Placeholder
                        # 로드된 데이터에 이미지 경로 리스트가 없으면 빈 리스트로 초기화
                        if 'uploaded_image_paths' not in loaded_content:
                            loaded_content['uploaded_image_paths'] = []
                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)
                        if load_success:
                            st.success("✅ 견적 데이터 로딩 완료.")
                            st.rerun() # 상태 변경 후 UI 즉시 업데이트
                        else: st.error("❌ 저장된 데이터 형식 오류로 로딩 실패.")
                    else: st.error(f"❌ '{st.session_state.gdrive_selected_filename}' 파일 로딩 또는 JSON 파싱 실패.")
                else: st.warning("⚠️ 불러올 파일을 선택해주세요.")

        # --- Save Section ---
        with col_save:
            st.markdown("**현재 견적 저장**")
            with st.form(key="save_quote_form_tab1"): # 키를 탭1용으로 명확히 구분
                customer_phone_for_filename = st.session_state.get('customer_phone', '').strip()
                if not customer_phone_for_filename:
                    example_json_fname = "전화번호입력후생성.json"
                else:
                    example_json_fname = f"{customer_phone_for_filename}.json"

                st.caption(f"JSON 파일명 예시: `{example_json_fname}`")
                st.caption("ℹ️ JSON 파일은 고객 전화번호로 저장되며, 같은 번호로 저장 시 덮어쓰기됩니다.")
                submitted = st.form_submit_button("💾 Google Drive에 저장")

                if submitted:
                    customer_phone = st.session_state.get('customer_phone', '').strip()
                    if not customer_phone or not customer_phone.isdigit(): # 간단한 숫자 검증 추가
                        st.error("⚠️ 저장 실패: 유효한 고객 전화번호를 입력해주세요.")
                    else:
                        json_filename = f"{customer_phone}.json" # 고객 전화번호를 파일명으로 사용
                        state_data_to_save = prepare_state_for_save()
                        # 저장 전 이미지 경로가 리스트인지 다시 한번 확인 및 보정
                        if 'uploaded_image_paths' not in state_data_to_save:
                             state_data_to_save['uploaded_image_paths'] = st.session_state.get('uploaded_image_paths', [])
                        elif not isinstance(state_data_to_save.get('uploaded_image_paths'), list):
                             state_data_to_save['uploaded_image_paths'] = st.session_state.get('uploaded_image_paths', [])


                        json_save_success = False
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 데이터 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save)
                            if save_json_result and save_json_result.get('id'):
                                st.success(f"✅ 견적 데이터 '{json_filename}' 저장 완료.")
                                json_save_success = True
                            else: st.error(f"❌ 견적 데이터 '{json_filename}' 저장 실패.")
                        except Exception as save_err:
                            st.error(f"❌ '{json_filename}' 저장 중 예외 발생: {save_err}")
                            traceback.print_exc()
    st.divider()

    # === Customer Info Section ===
    st.header("📝 고객 기본 정보")
    move_type_options_tab1 = globals().get('MOVE_TYPE_OPTIONS') # state_manager에서 가져온 MOVE_TYPE_OPTIONS 사용
    sync_move_type_callback_ref = getattr(callbacks, 'sync_move_type', None)

    if move_type_options_tab1:
        try: current_index_tab1 = move_type_options_tab1.index(st.session_state.base_move_type)
        except ValueError: current_index_tab1 = 0
        st.radio(
            "🏢 **기본 이사 유형**",
            options=move_type_options_tab1,
            index=current_index_tab1,
            horizontal=True,
            key="base_move_type_widget_tab1", # 키를 탭1용으로 명확히 구분
            on_change=sync_move_type_callback_ref,
            args=("base_move_type_widget_tab1",) # 콜백에 전달할 인자
        )
    else: st.warning("이사 유형 옵션을 로드할 수 없습니다.")

    col_opts1, col_opts2, col_opts3 = st.columns(3)
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")
    with col_opts3: st.checkbox("↪️ 경유지 이사 여부", key="has_via_point")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name")
        st.text_input("📍 출발지 주소", key="from_location")
        if st.session_state.get('apply_long_distance'):
            ld_options = data.long_distance_options if hasattr(data,'long_distance_options') and data.long_distance_options else []
            st.selectbox("🛣️ 장거리 구간 선택", ld_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1")
        method_options = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') and data.METHOD_OPTIONS else []
        st.selectbox("🛠️ 출발지 작업 방법", method_options, key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date): # 날짜 타입 아니면 기본값으로 설정
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date")

    with col2:
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678")
        st.text_input("📧 이메일", key="customer_email", placeholder="email@example.com")
        st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소")
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2")
        method_options_to = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') and data.METHOD_OPTIONS else []
        st.selectbox("🛠️ 도착지 작업 방법", method_options_to, key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택")

    # === Image Upload Section ===
    if UPLOAD_DIR: # UPLOAD_DIR이 정상적으로 설정된 경우에만 이미지 업로드 섹션 표시
        st.subheader("🖼️ 관련 이미지 업로드")
        uploaded_files = st.file_uploader(
            "이미지 파일을 선택해주세요 (여러 파일 가능)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="image_uploader_tab1" # 키를 탭1용으로 명확히 구분
        )

        if uploaded_files:
            if 'uploaded_image_paths' not in st.session_state or not isinstance(st.session_state.uploaded_image_paths, list):
                st.session_state.uploaded_image_paths = [] # 리스트가 아니면 초기화

            for uploaded_file in uploaded_files:
                # 파일명 생성 로직 (고객 전화번호 + 타임스탬프 + 원본 파일명 일부)
                customer_phone_for_img = st.session_state.get('customer_phone', 'unknown_phone').strip()
                if not customer_phone_for_img: customer_phone_for_img = 'no_phone'

                # 파일명에서 안전하지 않은 문자 제거
                original_filename_sanitized = "".join(c if c.isalnum() or c in ['.', '_'] else '_' for c in uploaded_file.name)
                customer_phone_sanitized = "".join(c if c.isalnum() else '_' for c in customer_phone_for_img)

                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f") # 고유성 강화를 위해 마이크로초까지 포함
                unique_filename = f"{customer_phone_sanitized}_{timestamp_str}_{original_filename_sanitized}"
                save_path = os.path.join(UPLOAD_DIR, unique_filename)

                try:
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    if save_path not in st.session_state.uploaded_image_paths:
                        st.session_state.uploaded_image_paths.append(save_path)
                    st.success(f"'{uploaded_file.name}' 저장 완료: {os.path.basename(save_path)}")
                except Exception as e:
                    st.error(f"'{uploaded_file.name}' 저장 실패: {e}")
                    traceback.print_exc()

        if st.session_state.get('uploaded_image_paths'):
            st.markdown("**업로드된 이미지:**")
            # Ensure uploaded_image_paths is a list and filter out non-existent paths before display
            # 또한, 문자열이 아닌 요소가 포함되어 있을 경우를 대비하여 필터링
            valid_image_paths = [p for p in st.session_state.uploaded_image_paths if isinstance(p, str) and os.path.exists(p)]

            # 세션 상태의 리스트를 유효한 경로로만 업데이트 (잘못된 데이터 수정)
            if len(valid_image_paths) != len(st.session_state.uploaded_image_paths):
                 st.session_state.uploaded_image_paths = valid_image_paths

            if valid_image_paths:
                cols = st.columns(3) # 이미지를 3열로 표시
                for i, img_path in enumerate(valid_image_paths):
                    try:
                        cols[i % 3].image(img_path, caption=os.path.basename(img_path), use_column_width=True)
                    except Exception as img_disp_err:
                        cols[i % 3].warning(f"{os.path.basename(img_path)} 표시 불가: {img_disp_err}")
            elif st.session_state.uploaded_image_paths: # 리스트는 있지만 유효한 경로가 없는 경우
                st.caption("이전에 업로드된 이미지 중 현재 유효한 파일이 없습니다. (경로: " + ", ".join(st.session_state.uploaded_image_paths) +")")
    else:
        st.warning("이미지 업로드 디렉토리 설정 오류로 이미지 업로드 기능이 비활성화되었습니다.")


    kst_time_str = utils.get_current_kst_time_str() if utils and hasattr(utils, 'get_current_kst_time_str') else ''
    st.caption(f"⏱️ 견적 생성일: {kst_time_str}")
    st.divider()

    if st.session_state.get('has_via_point'):
        with st.container(border=True):
            st.subheader("↪️ 경유지 정보")
            st.text_input("📍 경유지 주소", key="via_point_location", placeholder="경유지 상세 주소 입력")
            method_options_via = data.METHOD_OPTIONS if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else []
            st.selectbox("🛠️ 경유지 작업 방법", options=method_options_via, key="via_point_method", help="경유지에서의 작업 방법을 선택합니다.")
        st.divider()

    if st.session_state.get('is_storage_move'):
        with st.container(border=True):
            st.subheader("📦 보관이사 추가 정보")
            storage_options = data.STORAGE_TYPE_OPTIONS if hasattr(data, 'STORAGE_TYPE_OPTIONS') and data.STORAGE_TYPE_OPTIONS else []
            st.radio("보관 유형 선택:", options=storage_options, key="storage_type", horizontal=True)
            st.checkbox("🔌 보관 중 전기사용 (냉장고 등, 일 3,000원 추가)", key="storage_use_electricity")
            if 'arrival_date' not in st.session_state or \
               not isinstance(st.session_state.arrival_date, date) or \
               st.session_state.arrival_date < st.session_state.moving_date:
                st.session_state.arrival_date = st.session_state.moving_date
            st.date_input(
                "🚚 도착 예정일 (보관 후)",
                key="arrival_date",
                min_value=st.session_state.moving_date
            )
            moving_dt = st.session_state.moving_date
            arrival_dt = st.session_state.arrival_date
            calculated_duration = 1
            if isinstance(moving_dt, date) and isinstance(arrival_dt, date) and arrival_dt >= moving_dt:
                delta = arrival_dt - moving_dt
                calculated_duration = max(1, delta.days + 1)
            st.session_state.storage_duration = calculated_duration
            st.markdown(f"**계산된 보관 기간:** **`{calculated_duration}`** 일")
            st.caption("보관 기간은 출발일과 도착 예정일을 포함하여 자동 계산됩니다.")
        st.divider()

    with st.container(border=True):
        st.header("🗒️ 고객 요구사항")
        st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes", placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등")
# --- End of render_tab1 function ---