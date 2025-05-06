# ui_tab3.py (Restored features and fixed duplicate key)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date # date 추가
import traceback # Keep for error handling

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # Needed for generate_excel (used in summary) and generate_pdf
    import excel_filler # Needed for the final excel generation
    import excel_summary_generator # Assuming this exists based on previous context
    # Import MOVE_TYPE_OPTIONS from state_manager
    from state_manager import MOVE_TYPE_OPTIONS
    # Import callbacks needed in this tab
    from callbacks import sync_move_type, update_basket_quantities
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션")

    # --- Move Type Selection (Restored) ---
    st.subheader("🏢 이사 유형 확인/변경")
    current_move_type = st.session_state.get('base_move_type')
    current_index_tab3 = 0 # Default index
    if 'MOVE_TYPE_OPTIONS' in globals() and MOVE_TYPE_OPTIONS and isinstance(MOVE_TYPE_OPTIONS, (list, tuple)):
        try:
            current_index_tab3 = MOVE_TYPE_OPTIONS.index(current_move_type)
        except ValueError:
            current_index_tab3 = 0
            if MOVE_TYPE_OPTIONS:
                 st.session_state.base_move_type = MOVE_TYPE_OPTIONS[0]
                 print("Warning: Resetting base_move_type in Tab 3 due to invalid state.")
            else:
                 st.error("이사 유형 옵션을 data.py에서 찾을 수 없습니다.")

        st.radio(
            "기본 이사 유형:",
            options=MOVE_TYPE_OPTIONS, index=current_index_tab3, horizontal=True,
            key="base_move_type_widget_tab3", # Keep unique key for this widget
            on_change=sync_move_type,
            args=("base_move_type_widget_tab3",)
        )
    else:
         st.error("이사 유형 옵션을 정의할 수 없습니다. data.py 또는 state_manager.py 파일을 확인하세요.")

    st.divider()

    # --- Vehicle Selection (Restored) ---
    with st.container(border=True):
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget:
            # Use update_basket_quantities callback for vehicle changes
            st.radio(
                "차량 선택 방식:",
                ["자동 추천 차량 사용", "수동으로 차량 선택"],
                key="vehicle_select_radio",
                help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.",
                on_change=update_basket_quantities
            )
        with col_v2_widget:
            current_move_type_widget = st.session_state.base_move_type
            # Ensure data module and attributes exist
            vehicle_prices_options_widget = {}
            available_trucks_widget = []
            if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
                 vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
            if hasattr(data, 'vehicle_specs') and isinstance(data.vehicle_specs, dict):
                 available_trucks_widget = sorted(vehicle_prices_options_widget.keys(), key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))

            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
            # update_basket_quantities callback now sets final_selected_vehicle
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
            # Display manual selection box only when manual mode is selected OR auto fails
            if not use_auto_widget or (use_auto_widget and not valid_auto_widget):
                 if not available_trucks_widget:
                     st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                 else:
                     # Ensure manual_vehicle_select_value is valid or set default
                     current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                     current_index_widget = 0
                     if current_manual_selection_widget not in available_trucks_widget:
                         current_manual_selection_widget = available_trucks_widget[0] if available_trucks_widget else None
                         st.session_state.manual_vehicle_select_value = current_manual_selection_widget # Update state if invalid

                     if current_manual_selection_widget: # Check if selection is possible
                         try:
                             current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                         except ValueError:
                             current_index_widget = 0 # Default to first if index fails

                     st.selectbox(
                         "수동으로 차량 선택:" if not use_auto_widget else "수동 선택 (자동 추천 불가):",
                         available_trucks_widget,
                         index=current_index_widget,
                         key="manual_vehicle_select_value",
                         on_change=update_basket_quantities # Update baskets on manual change too
                     )
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
        sky_from = st.session_state.get('from_method') == "스카이 🏗️"
        sky_to = st.session_state.get('to_method') == "스카이 🏗️"
        if sky_from or sky_to:
            st.warning("스카이 작업 선택됨 - 시간 입력 필요", icon="🏗️")
            cols_sky = st.columns(2)
            with cols_sky[0]:
                if sky_from: st.number_input("출발 스카이 시간(h)", min_value=1, step=1, key="sky_hours_from")
            with cols_sky[1]:
                if sky_to: st.number_input("도착 스카이 시간(h)", min_value=1, step=1, key="sky_hours_final")
            st.write("") # Spacer

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
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.")
        st.write("")

        # Remove housewife option logic (check base housewife count for selected vehicle)
        base_w = 0
        remove_opt = False
        final_vehicle_for_options = st.session_state.get('final_selected_vehicle')
        current_move_type_options = st.session_state.base_move_type
        vehicle_prices_options_display = {}
        if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
             vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})

        if final_vehicle_for_options and final_vehicle_for_options in vehicle_prices_options_display:
            base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {})
            base_w = base_info.get('housewife', 0)
        if base_w > 0:
            remove_opt = True

        if remove_opt:
            discount_amount = data.ADDITIONAL_PERSON_COST * base_w if hasattr(data, 'ADDITIONAL_PERSON_COST') else 0
            st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,}원)", key="remove_base_housewife")
        else:
             # Ensure the checkbox state is False if the option shouldn't be available
             if 'remove_base_housewife' in st.session_state:
                 st.session_state.remove_base_housewife = False

        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
             if st.session_state.get('has_waste_check'):
                 st.number_input("폐기물 톤수", min_value=0.5, step=0.5, key="waste_tons_input", format="%.1f")
        st.write("")

        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            with cols_date[i]:
                st.checkbox(option, key=date_keys[i])

    st.divider()

    # --- Cost Adjustment & Deposit (Restored) ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        with col_adj1: st.number_input( "📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력" )
        with col_adj2: st.number_input( "💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d" )
        with col_adj3: st.number_input( "🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용" )
    st.divider()

    # --- Final Quote Results (Restored) ---
    st.header("💵 최종 견적 결과")
    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle')
    if final_selected_vehicle_calc:
        try:
            current_state_dict = st.session_state.to_dict()
            # Run calculation
            total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)
            total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
            st.session_state["final_adjusted_cost"] = total_cost_num # Store calculated cost

            # Calculate remaining balance
            try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0))
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            # Display costs
            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            # Display cost details
            st.subheader("📊 비용 상세 내역")
            has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False
            if has_cost_error:
                error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
                st.error(f"비용 계산 오류: {error_item[2]}" if error_item else "비용 계산 중 오류 발생")
            elif cost_items:
                df_display = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"])
                st.dataframe(
                    df_display.style.format({"금액": "{:,.0f}"})
                    .set_properties(**{'text-align': 'right'}, subset=['금액'])
                    .set_properties(**{'text-align': 'left'}, subset=['항목', '비고']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("ℹ️ 계산된 비용 항목이 없습니다.")
            st.write("")

            # Display special notes
            special_notes_display = st.session_state.get('special_notes')
            if special_notes_display and special_notes_display.strip():
                st.subheader("📝 고객요구사항")
                st.info(special_notes_display)

            # --- Move Info Summary (Restored and Updated Format) ---
            st.subheader("📋 이사 정보 요약")
            summary_generated = False
            try:
                # Ensure dependencies exist and are callable
                if not callable(getattr(pdf_generator, 'generate_excel', None)): raise ImportError("pdf_generator.generate_excel is not available or callable.")
                if not isinstance(personnel_info, dict): personnel_info = {}

                # Generate summary Excel data in memory (used for parsing)
                excel_data_summary = pdf_generator.generate_excel(current_state_dict, cost_items, total_cost, personnel_info)
                if excel_data_summary:
                    excel_buffer = io.BytesIO(excel_data_summary)
                    xls = pd.ExcelFile(excel_buffer)
                    if "견적 정보" in xls.sheet_names and "비용 내역 및 요약" in xls.sheet_names:
                        df_info = xls.parse("견적 정보", header=None)
                        df_cost = xls.parse("비용 내역 및 요약", header=None)
                        info_dict = dict(zip(df_info[0].astype(str), df_info[1].astype(str))) if not df_info.empty and len(df_info.columns) > 1 else {}

                        # Helper functions for formatting (copied from previous version)
                        def format_money_manwon_unit(amount):
                            try:
                                amount_str = str(amount).replace(",", "").split()[0]; amount_float = float(amount_str); amount_int = int(amount_float)
                                if amount_int == 0: return "0"
                                manwon_value = amount_int // 10000; return f"{manwon_value}"
                            except (ValueError, TypeError, IndexError): return "금액오류"
                        def get_cost_abbr_manwon_unit(kw, abbr, df):
                            if df.empty or len(df.columns) < 2: return f"{abbr} 정보 없음"
                            for i in range(len(df)):
                                if pd.notna(df.iloc[i, 0]) and str(df.iloc[i, 0]).strip().startswith(kw):
                                    formatted_amount = format_money_manwon_unit(df.iloc[i, 1]); return f"{abbr} {formatted_amount}"
                            return f"{abbr} 정보 없음"
                        def format_address(addr): return str(addr).strip() if isinstance(addr, str) and addr.strip() and addr.lower() != 'nan' else ""
                        def format_method(m): m = str(m).strip(); return "사" if "사다리차" in m else "승" if "승강기" in m else "계" if "계단" in m else "스카이" if "스카이" in m else "?"

                        # Extract data for summary
                        from_addr = format_address(info_dict.get("출발지", st.session_state.get('from_location',''))); to_addr = format_address(info_dict.get("도착지", st.session_state.get('to_location','')))
                        phone = info_dict.get("고객 연락처", st.session_state.get('customer_phone','')); vehicle_type = final_selected_vehicle_calc
                        note = format_address(info_dict.get("고객요구사항", st.session_state.get('special_notes','')))
                        p_info = personnel_info if isinstance(personnel_info, dict) else {}; men = p_info.get('final_men', 0); women = p_info.get('final_women', 0); ppl = f"{men}+{women}" if women > 0 else f"{men}"
                        b_name = "포장 자재 📦"; move_t = st.session_state.base_move_type
                        # Get basket quantities (handle potential key errors)
                        def get_qty(key_suffix):
                            try: return int(st.session_state.get(f"qty_{move_t}_{b_name}_{key_suffix}", 0))
                            except: return 0
                        q_b = get_qty("바구니"); q_m = get_qty("중박스") if get_qty("중박스") > 0 else get_qty("중자바구니"); q_c = get_qty("옷바구니"); q_k = get_qty("책바구니")
                        bask_parts = [];
                        if q_b > 0: bask_parts.append(f"바{q_b}")
                        if q_m > 0: bask_parts.append(f"중{q_m}")
                        if q_c > 0: bask_parts.append(f"옷{q_c}") # If exists
                        if q_k > 0: bask_parts.append(f"책{q_k}")
                        bask = " ".join(bask_parts)
                        cont_fee_str = get_cost_abbr_manwon_unit("계약금 (-)", "계", df_cost); rem_fee_str = get_cost_abbr_manwon_unit("잔금 (VAT 별도)", "잔", df_cost)
                        w_from = format_method(info_dict.get("출발 작업", st.session_state.get('from_method',''))); w_to = format_method(info_dict.get("도착 작업", st.session_state.get('to_method',''))); work = f"출{w_from}도{w_to}"

                        # Display summary
                        addr_separator = " - " if from_addr and to_addr else " "; first_line = f"{from_addr}{addr_separator}{to_addr} {vehicle_type}"
                        st.text(first_line.strip()); st.text("")
                        if phone and phone != '-': st.text(phone); st.text("")
                        personnel_line = f"{vehicle_type} {ppl}"; st.text(personnel_line); st.text("")
                        if bask: st.text(bask); st.text("")
                        st.text(work); st.text("")
                        st.text(f"{cont_fee_str} / {rem_fee_str}"); st.text("")
                        if note:
                            notes_list = [n.strip() for n in note.split('.') if n.strip()];
                            for note_line in notes_list: st.text(note_line)

                        summary_generated = True
                    else: st.warning("⚠️ 요약 정보 생성 실패 (필수 Excel 시트 누락)")
                else: st.warning("⚠️ 요약 정보 생성 실패 (Excel 데이터 생성 오류)")
            except Exception as e: st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}"); traceback.print_exc()
            if not summary_generated: st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")

        except Exception as calc_err_outer:
            st.error(f"비용 계산 중 오류 발생: {calc_err_outer}")
            traceback.print_exc()
            has_cost_error = True # Assume error if calculation fails
            can_gen_pdf = False
            can_gen_final_excel = False
            can_gen_summary_excel = False

        st.divider()

        # --- Download Section (Restored structure) ---
        st.subheader("📄 견적서 파일 다운로드")
        # Re-check flags based on calculation results
        can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error
        can_gen_final_excel = bool(final_selected_vehicle_calc)
        can_gen_summary_excel = bool(final_selected_vehicle_calc) and not has_cost_error

        cols_dl = st.columns(3)
        with cols_dl[0]:
            st.markdown("**① Final 견적서 (Excel)**")
            if can_gen_final_excel:
                 if st.button("📄 생성: Final 견적서"):
                     # Ensure latest data is used
                     latest_total_cost_fe, latest_cost_items_fe, latest_personnel_info_fe = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                     filled_excel_data = excel_filler.fill_final_excel_template(st.session_state.to_dict(), latest_cost_items_fe, latest_total_cost_fe, latest_personnel_info_fe)
                     if filled_excel_data: st.session_state['final_excel_data'] = filled_excel_data; st.success("✅ Final Excel 생성 완료!")
                     else:
                         if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']
                         st.error("❌ Final Excel 생성 실패.")
                 if st.session_state.get('final_excel_data'):
                     ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d') if pytz else datetime.now().strftime('%y%m%d')
                     fname = f"{ph_part}_{now_str}_Final견적서.xlsx"
                     st.download_button("📥 다운로드 (Final Excel)", st.session_state['final_excel_data'], fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_final_excel')
                 else: st.caption("생성 버튼 클릭")
            else: st.caption("Excel 생성 불가")

        with cols_dl[1]:
            st.markdown("**② 고객용 견적서 (PDF)**")
            if can_gen_pdf:
                if st.button("📄 생성: PDF 견적서"):
                    latest_total_cost_pdf_recalc, latest_cost_items_pdf, latest_personnel_info_pdf = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                    pdf_bytes = pdf_generator.generate_pdf(st.session_state.to_dict(), latest_cost_items_pdf, latest_total_cost_pdf_recalc, latest_personnel_info_pdf)
                    st.session_state['pdf_data_customer'] = pdf_bytes
                    if pdf_bytes: st.success("✅ PDF 생성 완료!")
                    else:
                         if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']
                         st.error("❌ PDF 생성 실패.")
                if st.session_state.get('pdf_data_customer'):
                    ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M') if pytz else datetime.now().strftime('%y%m%d_%H%M')
                    fname = f"{ph_part}_{now_str}_이삿날견적서.pdf"
                    st.download_button("📥 다운로드 (PDF)", st.session_state['pdf_data_customer'], fname, 'application/pdf', key='dl_pdf')
                else: st.caption("생성 버튼 클릭")
            else: st.caption("PDF 생성 불가 (비용 오류?)")

        with cols_dl[2]:
             st.markdown("**③ 요약 Excel**")
             if can_gen_summary_excel:
                 if st.button("📊 생성: 요약 Excel"):
                     # Recalculate or use stored if confident state hasn't changed
                     summ_total_cost, summ_cost_items, summ_personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                     # Ensure excel_summary_generator is correctly imported and used
                     excel_bytes = excel_summary_generator.generate_summary_excel(
                         st.session_state.to_dict(),
                         summ_cost_items, # Use fresh calculation results
                         summ_personnel_info, # Use fresh calculation results
                         vehicle_info={}, # Placeholder
                         waste_info={
                             "total_waste_tons": st.session_state.get("waste_tons_input", 0),
                             "total_waste_cost": st.session_state.get("waste_tons_input", 0) * data.WASTE_DISPOSAL_COST_PER_TON if hasattr(data,'WASTE_DISPOSAL_COST_PER_TON') else 0
                         }
                     )
                     if excel_bytes: st.session_state['summary_excel_data'] = excel_bytes; st.success("✅ 요약 Excel 생성 완료!")
                     else:
                         if 'summary_excel_data' in st.session_state: del st.session_state['summary_excel_data']
                         st.error("❌ 요약 Excel 생성 실패.")
                 if st.session_state.get('summary_excel_data'):
                     ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000"); now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d') if pytz else datetime.now().strftime('%y%m%d')
                     fname = f"{ph_part}_{now_str}_견적서_요약.xlsx"
                     st.download_button("📥 다운로드 (요약 Excel)", st.session_state['summary_excel_data'], fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_summary_excel')
                 else: st.caption("생성 버튼 클릭")
             else: st.caption("Excel 생성 불가 (비용 오류?)")

    else: # Vehicle not selected
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시 및 다운로드는 차량 선택 후 가능합니다.")

    st.write("---")

    # --- Expander for Image Upload (Moved near bottom as a utility?) ---
    # Kept the key change here
    with st.expander("결적서 이미지 업로드 및 미리보기 (문자 전송 준비용)", expanded=False): # Default to collapsed
        uploaded_file = st.file_uploader(
            "이미지 파일을 업로드하세요",
            type=['png', 'jpg', 'jpeg'],
            key="preview_image_uploader"  # <-- UNIQUE KEY
        )
        if uploaded_file:
            st.session_state["uploaded_file_for_preview"] = uploaded_file
            st.image(uploaded_file, caption="업로드된 결적서 이미지 미리보기", use_column_width=True)
        elif "uploaded_file_for_preview" in st.session_state and st.session_state["uploaded_file_for_preview"] is not None:
             try: st.image(st.session_state["uploaded_file_for_preview"], caption="이전 업로드 이미지", use_column_width=True)
             except Exception as img_err: st.warning(f"이전 이미지 표시에 실패했습니다: {img_err}")

    st.caption("※ 이 탭에서는 생성된 견적서를 PDF 또는 Excel로 다운로드하거나, 이미지를 업로드해서 문자 전송 등을 준비할 수 있습니다.")

# --- End of render_tab3 function ---