# ui_tab3.py (Removed Excel downloads, Added PDF email sending)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date
import traceback

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # Needed for generate_excel (used in summary) and generate_pdf
    # import excel_filler # No longer needed for Final Excel
    # import excel_summary_generator # No longer needed for Summary Excel
    import email_utils # Needed for sending email
    from state_manager import MOVE_TYPE_OPTIONS
    from callbacks import sync_move_type, update_basket_quantities
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    # Ensure specific missing modules are reported if possible
    if 'email_utils' not in str(ie): st.warning("email_utils.py 파일이 필요합니다.")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, Summary, and Email."""

    st.header("💰 계산 및 옵션")

    # --- Move Type Selection (Restored from previous full version) ---
    st.subheader("🏢 이사 유형 확인/변경")
    current_move_type = st.session_state.get('base_move_type')
    current_index_tab3 = 0
    if 'MOVE_TYPE_OPTIONS' in globals() and MOVE_TYPE_OPTIONS and isinstance(MOVE_TYPE_OPTIONS, (list, tuple)):
        try: current_index_tab3 = MOVE_TYPE_OPTIONS.index(current_move_type)
        except ValueError:
            current_index_tab3 = 0
            if MOVE_TYPE_OPTIONS: st.session_state.base_move_type = MOVE_TYPE_OPTIONS[0]
            else: st.error("이사 유형 옵션을 data.py에서 찾을 수 없습니다.")
        st.radio("기본 이사 유형:", options=MOVE_TYPE_OPTIONS, index=current_index_tab3, horizontal=True,
                 key="base_move_type_widget_tab3", on_change=sync_move_type, args=("base_move_type_widget_tab3",))
    else: st.error("이사 유형 옵션을 정의할 수 없습니다. data.py 또는 state_manager.py 파일을 확인하세요.")
    st.divider()

    # --- Vehicle Selection (Restored) ---
    with st.container(border=True):
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget:
            st.radio("차량 선택 방식:", ["자동 추천 차량 사용", "수동으로 차량 선택"], key="vehicle_select_radio",
                     help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.", on_change=update_basket_quantities)
        with col_v2_widget:
            current_move_type_widget = st.session_state.base_move_type
            vehicle_prices_options_widget = {}
            available_trucks_widget = []
            if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
                 vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
            if hasattr(data, 'vehicle_specs') and isinstance(data.vehicle_specs, dict):
                 available_trucks_widget = sorted(vehicle_prices_options_widget.keys(), key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))
            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
            final_vehicle_widget = st.session_state.get('final_selected_vehicle')
            valid_auto_widget = (recommended_vehicle_auto_widget and "초과" not in recommended_vehicle_auto_widget and recommended_vehicle_auto_widget in available_trucks_widget)
            if use_auto_widget:
                if valid_auto_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_widget}**")
                    spec = data.vehicle_specs.get(final_vehicle_widget) if hasattr(data, 'vehicle_specs') else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get('capacity', 'N/A')}m³, {spec.get('weight_capacity', 'N/A'):,}kg")
                        st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
                else:
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_widget and "초과" in recommended_vehicle_auto_widget: error_msg += f"물량 초과({recommended_vehicle_auto_widget}). 수동 선택 필요."
                    elif not recommended_vehicle_auto_widget and (st.session_state.get('total_volume', 0.0) > 0 or st.session_state.get('total_weight', 0.0) > 0): error_msg += "계산/정보 부족. 수동 선택 필요."
                    else: error_msg += "물품 미선택 또는 정보 부족. 수동 선택 필요."
                    st.error(error_msg)
            if not use_auto_widget or (use_auto_widget and not valid_auto_widget):
                 if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                 else:
                     current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                     current_index_widget = 0
                     if current_manual_selection_widget not in available_trucks_widget:
                         current_manual_selection_widget = available_trucks_widget[0] if available_trucks_widget else None
                         st.session_state.manual_vehicle_select_value = current_manual_selection_widget
                     if current_manual_selection_widget:
                         try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                         except ValueError: current_index_widget = 0
                     st.selectbox("수동으로 차량 선택:" if not use_auto_widget else "수동 선택 (자동 추천 불가):",
                         available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities)
                     manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                     if manual_selected_display:
                        st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                        spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, 'vehicle_specs') else None
                        if spec_manual:
                            st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
    st.divider()

    # --- Work Conditions & Options (Restored) ---
    with st.container(border=True):
        st.subheader("🛠️ 작업 조건 및 추가 옵션")
        sky_from = st.session_state.get('from_method') == "스카이 🏗️"; sky_to = st.session_state.get('to_method') == "스카이 🏗️"
        if sky_from or sky_to:
            st.warning("스카이 작업 선택됨 - 시간 입력 필요", icon="🏗️"); cols_sky = st.columns(2)
            with cols_sky[0]:
                if sky_from: st.number_input("출발 스카이 시간(h)", min_value=1, step=1, key="sky_hours_from")
            with cols_sky[1]:
                if sky_to: st.number_input("도착 스카이 시간(h)", min_value=1, step=1, key="sky_hours_final")
            st.write("")
        col_add1, col_add2 = st.columns(2)
        with col_add1: st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2: st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        st.write("")
        st.subheader("🚚 실제 투입 차량 (견적과 별개)")
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다."); st.write("")
        base_w = 0; remove_opt = False; final_vehicle_for_options = st.session_state.get('final_selected_vehicle'); current_move_type_options = st.session_state.base_move_type; vehicle_prices_options_display = {}
        if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict): vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})
        if final_vehicle_for_options and final_vehicle_for_options in vehicle_prices_options_display: base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {}); base_w = base_info.get('housewife', 0)
        if base_w > 0: remove_opt = True
        if remove_opt: discount_amount = data.ADDITIONAL_PERSON_COST * base_w if hasattr(data, 'ADDITIONAL_PERSON_COST') else 0; st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,}원)", key="remove_base_housewife")
        else:
             if 'remove_base_housewife' in st.session_state: st.session_state.remove_base_housewife = False
        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
             if st.session_state.get('has_waste_check'): st.number_input("폐기물 톤수", min_value=0.5, step=0.5, key="waste_tons_input", format="%.1f")
        st.write("")
        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]; date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            with cols_date[i]: st.checkbox(option, key=date_keys[i])
    st.divider()

    # --- Cost Adjustment & Deposit (Restored) ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        with col_adj1: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with col_adj2: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with col_adj3: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
    st.divider()

    # --- Final Quote Results (Restored) ---
    st.header("💵 최종 견적 결과")
    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle')
    total_cost = 0
    cost_items = []
    personnel_info = {}
    has_cost_error = False
    can_gen_pdf = False

    if final_selected_vehicle_calc:
        try:
            current_state_dict = st.session_state.to_dict()
            total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)
            total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
            st.session_state["final_adjusted_cost"] = total_cost_num # Store calculated cost

            try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0))
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False
            if has_cost_error:
                error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
                st.error(f"비용 계산 오류: {error_item[2]}" if error_item else "비용 계산 중 오류 발생")
            elif cost_items:
                df_display = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"])
                st.dataframe(df_display.style.format({"금액": "{:,.0f}"}).set_properties(**{'text-align': 'right'}, subset=['금액']).set_properties(**{'text-align': 'left'}, subset=['항목', '비고']),
                             use_container_width=True, hide_index=True)
            else: st.info("ℹ️ 계산된 비용 항목이 없습니다.")
            st.write("")

            special_notes_display = st.session_state.get('special_notes')
            if special_notes_display and special_notes_display.strip(): st.subheader("📝 고객요구사항"); st.info(special_notes_display)

            # --- Move Info Summary (Restored) ---
            st.subheader("📋 이사 정보 요약")
            # (Summary generation and display logic remains the same)
            summary_generated = False
            try:
                if not callable(getattr(pdf_generator, 'generate_excel', None)): raise ImportError("pdf_generator.generate_excel is not available or callable.")
                if not isinstance(personnel_info, dict): personnel_info = {}
                excel_data_summary = pdf_generator.generate_excel(current_state_dict, cost_items, total_cost, personnel_info)
                if excel_data_summary:
                    excel_buffer = io.BytesIO(excel_data_summary); xls = pd.ExcelFile(excel_buffer)
                    if "견적 정보" in xls.sheet_names and "비용 내역 및 요약" in xls.sheet_names:
                        df_info = xls.parse("견적 정보", header=None); df_cost = xls.parse("비용 내역 및 요약", header=None)
                        info_dict = dict(zip(df_info[0].astype(str), df_info[1].astype(str))) if not df_info.empty and len(df_info.columns) > 1 else {}
                        def format_money_manwon_unit(amount):
                            try: amount_str = str(amount).replace(",", "").split()[0]; amount_float = float(amount_str); amount_int = int(amount_float);
                            if amount_int == 0: return "0"; manwon_value = amount_int // 10000; return f"{manwon_value}"
                            except: return "금액오류"
                        def get_cost_abbr_manwon_unit(kw, abbr, df):
                            if df.empty or len(df.columns) < 2: return f"{abbr} 정보 없음";
                            for i in range(len(df)):
                                if pd.notna(df.iloc[i, 0]) and str(df.iloc[i, 0]).strip().startswith(kw): formatted_amount = format_money_manwon_unit(df.iloc[i, 1]); return f"{abbr} {formatted_amount}"
                            return f"{abbr} 정보 없음"
                        def format_address(addr): return str(addr).strip() if isinstance(addr, str) and addr.strip() and addr.lower() != 'nan' else ""
                        def format_method(m): m = str(m).strip(); return "사" if "사다리차" in m else "승" if "승강기" in m else "계" if "계단" in m else "스카이" if "스카이" in m else "?"
                        from_addr = format_address(info_dict.get("출발지", st.session_state.get('from_location',''))); to_addr = format_address(info_dict.get("도착지", st.session_state.get('to_location','')))
                        phone = info_dict.get("고객 연락처", st.session_state.get('customer_phone','')); vehicle_type = final_selected_vehicle_calc
                        note = format_address(info_dict.get("고객요구사항", st.session_state.get('special_notes','')))
                        p_info = personnel_info if isinstance(personnel_info, dict) else {}; men = p_info.get('final_men', 0); women = p_info.get('final_women', 0); ppl = f"{men}+{women}" if women > 0 else f"{men}"
                        b_name = "포장 자재 📦"; move_t = st.session_state.base_move_type
                        def get_qty(key_suffix):
                            try: return int(st.session_state.get(f"qty_{move_t}_{b_name}_{key_suffix}", 0))
                            except: return 0
                        q_b = get_qty("바구니"); q_m = get_qty("중박스") if get_qty("중박스") > 0 else get_qty("중자바구니"); q_c = get_qty("옷바구니"); q_k = get_qty("책바구니")
                        bask_parts = [];
                        if q_b > 0: bask_parts.append(f"바{q_b}");
                        if q_m > 0: bask_parts.append(f"중{q_m}");
                        if q_c > 0: bask_parts.append(f"옷{q_c}"); # If exists
                        if q_k > 0: bask_parts.append(f"책{q_k}");
                        bask = " ".join(bask_parts)
                        cont_fee_str = get_cost_abbr_manwon_unit("계약금 (-)", "계", df_cost); rem_fee_str = get_cost_abbr_manwon_unit("잔금 (VAT 별도)", "잔", df_cost)
                        w_from = format_method(info_dict.get("출발 작업", st.session_state.get('from_method',''))); w_to = format_method(info_dict.get("도착 작업", st.session_state.get('to_method',''))); work = f"출{w_from}도{w_to}"
                        addr_separator = " - " if from_addr and to_addr else " "; first_line = f"{from_addr}{addr_separator}{to_addr} {vehicle_type}"
                        st.text(first_line.strip()); st.text("")
                        if phone and phone != '-': st.text(phone); st.text("")
                        personnel_line = f"{vehicle_type} {ppl}"; st.text(personnel_line); st.text("")
                        if bask: st.text(bask); st.text("")
                        st.text(work); st.text("")
                        st.text(f"{cont_fee_str} / {rem_fee_str}"); st.text("")
                        if note: notes_list = [n.strip() for n in note.split('.') if n.strip()];
                        for note_line in notes_list: st.text(note_line)
                        summary_generated = True
                    else: st.warning("⚠️ 요약 정보 생성 실패 (필수 Excel 시트 누락)")
                else: st.warning("⚠️ 요약 정보 생성 실패 (Excel 데이터 생성 오류)")
            except Exception as e: st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}"); traceback.print_exc()
            if not summary_generated: st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")
            st.divider()

        except Exception as calc_err_outer:
            st.error(f"비용 계산 중 오류 발생: {calc_err_outer}")
            traceback.print_exc()
            has_cost_error = True # Assume error if calculation fails

        # --- PDF Generation and Email Section ---
        st.subheader("📧 견적서 PDF 생성 및 이메일 발송")
        can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error

        if can_gen_pdf:
            if st.button("📄 PDF 견적서 생성 (이메일 발송 준비)"):
                pdf_bytes = None # Initialize
                try:
                    # Use calculation results if already available and valid
                    pdf_total_cost = st.session_state.get("final_adjusted_cost", 0)
                    # Ensure cost_items and personnel_info are available
                    if not cost_items and not has_cost_error:
                         pdf_total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())

                    pdf_bytes = pdf_generator.generate_pdf(st.session_state.to_dict(), cost_items, pdf_total_cost, personnel_info)
                    st.session_state['pdf_data_customer'] = pdf_bytes # Store even if None initially
                    if pdf_bytes:
                        st.success("✅ PDF 생성 완료! 아래에서 이메일로 발송하세요.")
                        st.rerun() # Rerun to show email section
                    else:
                        st.error("❌ PDF 생성 실패.")
                        if 'pdf_data_customer' in st.session_state:
                            del st.session_state['pdf_data_customer']
                except Exception as pdf_gen_err:
                     st.error(f"PDF 생성 중 예외 발생: {pdf_gen_err}")
                     traceback.print_exc()
                     if 'pdf_data_customer' in st.session_state:
                         del st.session_state['pdf_data_customer']

            # --- Email Sending Section (Show only if PDF is ready) ---
            if st.session_state.get('pdf_data_customer'):
                st.write("---") # Separator
                st.markdown("**이메일 발송**")
                default_email = st.session_state.get('customer_email', '')
                recipient_email = st.text_input("받는 사람 이메일 주소:", value=default_email, key="recipient_email_input")

                if st.button("📤 견적서 이메일 발송"):
                    if recipient_email:
                        pdf_bytes_to_send = st.session_state.get('pdf_data_customer')
                        if pdf_bytes_to_send:
                            ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                            try: now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M')
                            except Exception: now_str = datetime.now().strftime('%y%m%d_%H%M')
                            pdf_filename_for_email = f"{ph_part}_{now_str}_이삿날견적서.pdf"
                            email_subject = f"[이삿날] {st.session_state.get('customer_name','고객')}님 견적서입니다."
                            email_body = f"""안녕하세요, {st.session_state.get('customer_name','고객')}님.
요청하신 이삿날 견적서를 첨부하여 보내드립니다.

감사합니다.
"""
                            with st.spinner("📧 이메일 발송 중..."):
                                send_success = email_utils.send_quote_email(
                                    recipient_email=recipient_email, subject=email_subject, body=email_body,
                                    pdf_bytes=pdf_bytes_to_send, pdf_filename=pdf_filename_for_email )
                            if send_success: st.success(f"✅ '{recipient_email}' 주소로 견적서 이메일을 성공적으로 발송했습니다.")
                            else: st.error("❌ 이메일 발송 중 오류가 발생했습니다. 이메일 설정을 확인하거나 잠시 후 다시 시도해주세요.")
                        else: st.warning("⚠️ 이메일로 발송할 PDF 데이터가 없습니다. 먼저 PDF를 생성해주세요.")
                    else: st.warning("⚠️ 받는 사람 이메일 주소를 입력해주세요.")
            # If PDF not yet generated, show hint
            elif can_gen_pdf:
                 st.caption("PDF 생성 버튼을 눌러 이메일 발송을 준비하세요.")

        else: # Cannot generate PDF
            st.caption("PDF 생성 및 이메일 발송 불가 (차량 미선택 또는 비용 오류)")

    else: # Vehicle not selected
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시 및 이메일 발송은 차량 선택 후 가능합니다.")

    st.write("---")

    # --- Expander for Image Upload ---
    # Changed key to be unique
    with st.expander("결적서 이미지 업로드 및 미리보기 (문자 전송 준비용)", expanded=False):
        uploaded_file = st.file_uploader(
            "참고 이미지 업로드", # Changed label slightly
            type=['png', 'jpg', 'jpeg'],
            key="preview_image_uploader"  # <-- UNIQUE KEY
        )
        if uploaded_file:
            st.session_state["uploaded_file_for_preview"] = uploaded_file
            st.image(uploaded_file, caption="업로드된 참고 이미지 미리보기", use_column_width=True)
        elif "uploaded_file_for_preview" in st.session_state and st.session_state["uploaded_file_for_preview"] is not None:
             try: st.image(st.session_state["uploaded_file_for_preview"], caption="이전 업로드 이미지", use_column_width=True)
             except Exception as img_err: st.warning(f"이전 이미지 표시에 실패했습니다: {img_err}")

    st.caption("※ 이 탭에서는 생성된 견적서 PDF를 이메일로 발송하거나, 참고용 이미지를 업로드할 수 있습니다.")

# --- End of render_tab3 function ---