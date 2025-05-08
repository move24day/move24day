# ui_tab1.py
# ui_tab1.py (경유지 옵션, 도착 예정일, 보관 전기사용 옵션 추가)
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


def render_tab1():
    """Renders the UI for Tab 1: Customer Info and Google Drive."""

    # === Google Drive Section ===
    with st.container(border=True):
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적(JSON) 파일을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        # --- Load Section ---
        with col_load:
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("JSON 검색어 (날짜 YYMMDD 또는 번호 XXXX)", key="gdrive_search_term", help="파일 이름 일부 입력 후 검색")
            if st.button("🔍 견적 검색"):
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
                        st.session_state.gdrive_selected_filename = results[0].get('name')
                        st.session_state.gdrive_selected_file_id = results[0].get('id')
                        st.success(f"✅ {len(results)}개 검색 완료.")
                        st.rerun()
                    else: st.warning("⚠️ 해당 파일 없음.")
                else: st.warning("⚠️ 검색어를 입력하세요.")

            if st.session_state.get('gdrive_search_results'):
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                current_selection_index = 0
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
                    with st.spinner(f"🔄 '{st.session_state.gdrive_selected_filename}' 로딩 중..."):
                        loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', None);
                        if not update_basket_callback_ref: st.error("Basket callback 없음!"); update_basket_callback_ref = lambda: None
                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)
                        if load_success:
                            st.success("✅ 견적 데이터 로딩 완료.")
                            st.rerun()
                        else: st.error("❌ 저장된 데이터 형식 오류로 로딩 실패.")
                    else: st.error(f"❌ '{st.session_state.gdrive_selected_filename}' 파일 로딩 또는 JSON 파싱 실패.")
                else: st.warning("⚠️ 불러올 파일을 선택해주세요.")


        # --- Save Section ---
        with col_save:
            st.markdown("**현재 견적 저장**")
            with st.form(key="save_quote_form"):
                try: kst_ex = pytz.timezone("Asia/Seoul"); now_ex_str = datetime.now(kst_ex).strftime('%y%m%d')
                except Exception: now_ex_str = datetime.now().strftime('%y%m%d')
                phone_ex = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), length=4, default="XXXX")
                quote_base_name = f"{now_ex_str}-{phone_ex}"
                example_json_fname = f"{quote_base_name}.json"
                st.caption(f"JSON 파일명 예시: `{example_json_fname}`")
                st.caption("ℹ️ JSON 파일은 같은 이름으로 저장 시 덮어쓰기됩니다.")
                submitted = st.form_submit_button("💾 Google Drive에 저장")

                if submitted:
                    customer_phone = st.session_state.get('customer_phone', '')
                    phone_part = utils.extract_phone_number_part(customer_phone, length=4)

                    if phone_part == "번호없음" or not customer_phone.strip():
                        st.error("⚠️ 저장 실패: 고객 전화번호가 필요합니다.")
                    else:
                        try: kst_save = pytz.timezone("Asia/Seoul"); now_save = datetime.now(kst_save)
                        except Exception: now_save = datetime.now()
                        date_str = now_save.strftime('%y%m%d'); base_save_name = f"{date_str}-{phone_part}"; json_filename = f"{base_save_name}.json"
                        state_data_to_save = prepare_state_for_save()
                        json_save_success = False
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 데이터 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save)
                            if save_json_result and save_json_result.get('id'):
                                st.success(f"✅ 견적 데이터 '{json_filename}' 저장 완료.")
                                json_save_success = True
                            else: st.error(f"❌ 견적 데이터 '{json_filename}' 저장 실패.")
                        except Exception as save_err:
                            st.error(f"❌ '{json_filename}' 저장 중 예외 발생: {save_err}"); traceback.print_exc()
    st.divider()

    # === Customer Info Section ===
    st.header("📝 고객 기본 정보")
    move_type_options_tab1 = globals().get('MOVE_TYPE_OPTIONS'); sync_move_type_callback_ref = getattr(callbacks, 'sync_move_type', None)
    if move_type_options_tab1:
        try: current_index_tab1 = move_type_options_tab1.index(st.session_state.base_move_type)
        except ValueError: current_index_tab1 = 0
        st.radio( "🏢 **기본 이사 유형**", options=move_type_options_tab1, index=current_index_tab1, horizontal=True, key="base_move_type_widget_tab1", on_change=sync_move_type_callback_ref, args=("base_move_type_widget_tab1",))
    else: st.warning("이사 유형 옵션을 로드할 수 없습니다.")

    col_opts1, col_opts2, col_opts3 = st.columns(3) # 경유지 옵션을 위해 3개 컬럼
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")
    with col_opts3: st.checkbox("↪️ 경유지 이사 여부", key="has_via_point") # 경유지 옵션

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name"); st.text_input("📍 출발지 주소", key="from_location");
        if st.session_state.get('apply_long_distance'): ld_options = data.long_distance_options if hasattr(data,'long_distance_options') else []; st.selectbox("🛣️ 장거리 구간 선택", ld_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1"); method_options = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []; st.selectbox("🛠️ 출발지 작업 방법", method_options, key="from_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
        # 이사 예정일 (출발일)
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date):
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date")


    with col2:
        st.text_input("📞 전화번호", key="customer_phone", placeholder="01012345678"); st.text_input("📧 이메일", key="customer_email", placeholder="email@example.com"); st.text_input("📍 도착지 주소", key="to_location", placeholder="이사 도착지 상세 주소"); st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2"); method_options_to = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []; st.selectbox("🛠️ 도착지 작업 방법", method_options_to, key="to_method", help="사다리차, 승강기, 계단, 스카이 중 선택")
        # 도착 예정일 입력은 아래 보관이사 섹션에서 조건부로 표시


    kst_time_str = utils.get_current_kst_time_str() if utils and hasattr(utils, 'get_current_kst_time_str') else ''
    st.caption(f"⏱️ 견적 생성일: {kst_time_str}")
    st.divider()

    # === Via Point Info (경유지 정보) ===
    if st.session_state.get('has_via_point'):
        with st.container(border=True):
            st.subheader("↪️ 경유지 정보")
            st.text_input("📍 경유지 주소", key="via_point_location", placeholder="경유지 상세 주소 입력")
            method_options_via = data.METHOD_OPTIONS if hasattr(data, 'METHOD_OPTIONS') else []
            st.selectbox("🛠️ 경유지 작업 방법", options=method_options_via, key="via_point_method", help="경유지에서의 작업 방법을 선택합니다.")
        st.divider()


    # === Storage Move Info & Special Notes ===
    if st.session_state.get('is_storage_move'):
        with st.container(border=True):
            st.subheader("📦 보관이사 추가 정보")
            storage_options = data.STORAGE_TYPE_OPTIONS if hasattr(data, 'STORAGE_TYPE_OPTIONS') else []
            st.radio("보관 유형 선택:", options=storage_options, key="storage_type", horizontal=True)

            # 전기 사용 옵션 추가
            st.checkbox("🔌 보관 중 전기사용 (냉장고 등, 일 3,000원 추가)", key="storage_use_electricity")

            # 도착 예정일 입력
            # arrival_date가 없거나 moving_date보다 이전이면 moving_date로 초기화
            if 'arrival_date' not in st.session_state or \
               not isinstance(st.session_state.arrival_date, date) or \
               st.session_state.arrival_date < st.session_state.moving_date:
                st.session_state.arrival_date = st.session_state.moving_date

            st.date_input(
                "🚚 도착 예정일 (보관 후)",
                key="arrival_date",
                min_value=st.session_state.moving_date # 출발일 이전 선택 불가
            )

            # --- Calculate and Update Duration ---
            moving_dt = st.session_state.moving_date
            arrival_dt = st.session_state.arrival_date
            calculated_duration = 1 # 기본값 1일
            if isinstance(moving_dt, date) and isinstance(arrival_dt, date) and arrival_dt >= moving_dt:
                delta = arrival_dt - moving_dt
                calculated_duration = max(1, delta.days + 1) # 출발일, 도착일 포함하여 최소 1일

            # 계산된 기간을 세션 상태에 저장 (calculations.py에서 사용)
            st.session_state.storage_duration = calculated_duration

            # 계산된 보관 기간 표시 (읽기 전용)
            st.markdown(f"**계산된 보관 기간:** **`{calculated_duration}`** 일")
            st.caption("보관 기간은 출발일과 도착 예정일을 포함하여 자동 계산됩니다.")

        st.divider()

    with st.container(border=True):
        st.header("🗒️ 고객 요구사항"); st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes", placeholder="예: 에어컨 이전 설치 필요, 특정 가구 분해/조립 요청 등")
# --- End of render_tab1 function ---