# ui_tab3.py (Fixed NameError by importing 'date')
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date # *** NameError 해결: date import 추가 ***
import traceback

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator
    import excel_filler
    import email_utils
    # import mms_utils # 이전에 없었으므로 주석 처리 (필요시 해제)
    from state_manager import MOVE_TYPE_OPTIONS
    # 콜백 import 방식 수정 가능성 고려 (원본 코드 구조에 따라)
    from callbacks import sync_move_type, update_basket_quantities
    # 만약 mms_utils가 필요하다면 아래 주석 해제
    # import mms_utils
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    # (오류 메시지 부분은 원본 유지를 위해 그대로 둠)
    if 'email_utils' not in str(ie): st.warning("email_utils.py 파일이 필요합니다.")
    if 'excel_filler' not in str(ie): st.warning("excel_filler.py 파일이 필요합니다.")
    # if 'pdf2image' in str(ie): st.warning("pdf2image 라이브러리가 필요합니다. (`pip install pdf2image`)") # MMS 기능 미사용 시 주석 처리 가능
    # if 'mms_utils' not in str(ie): st.warning("mms_utils.py 파일 (MMS 발송 로직 포함)이 필요합니다.") # MMS 기능 미사용 시 주석 처리 가능
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, Summary, Files & Sending."""

    st.header("💰 계산 및 옵션")

    # --- Move Type Selection ---
    # (원본 코드 유지 - 아래는 제공된 코드 내용을 기반으로 함)
    st.subheader("🏢 이사 유형 확인/변경")
    current_move_type = st.session_state.get('base_move_type')
    current_index_tab3 = 0
    move_type_options_local = globals().get('MOVE_TYPE_OPTIONS') # Get safely
    if move_type_options_local and isinstance(move_type_options_local, (list, tuple)):
        try: current_index_tab3 = move_type_options_local.index(current_move_type)
        except ValueError:
            current_index_tab3 = 0
            if move_type_options_local: st.session_state.base_move_type = move_type_options_local[0]
            else: st.error("이사 유형 옵션을 data.py에서 찾을 수 없습니다.") # Use local variable
        st.radio("기본 이사 유형:", options=move_type_options_local, index=current_index_tab3, horizontal=True, # Use local variable
                 key="base_move_type_widget_tab3", on_change=sync_move_type, args=("base_move_type_widget_tab3",))
    else: st.error("이사 유형 옵션을 정의할 수 없습니다. data.py 또는 state_manager.py 파일을 확인하세요.")
    st.divider()


    # --- Vehicle Selection ---
    # (원본 코드 유지)
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
                # Sort by capacity using data.vehicle_specs
                available_trucks_widget = sorted(
                    [truck for truck in vehicle_prices_options_widget.keys() if truck in data.vehicle_specs], # Ensure truck exists in specs
                    key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0)
                )
            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
            final_vehicle_widget = st.session_state.get('final_selected_vehicle') # This gets updated by callback
            valid_auto_widget = (recommended_vehicle_auto_widget and "초과" not in recommended_vehicle_auto_widget and recommended_vehicle_auto_widget in available_trucks_widget)

            if use_auto_widget:
                # When using auto, the final_selected_vehicle is the one that matters
                if final_vehicle_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_widget}**")
                    spec = data.vehicle_specs.get(final_vehicle_widget) if hasattr(data, 'vehicle_specs') else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get('capacity', 'N/A')}m³, {spec.get('weight_capacity', 'N/A'):,}kg")
                        st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
                else: # Auto selected but no valid recommendation
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_widget and "초과" in recommended_vehicle_auto_widget: error_msg += f"물량 초과({recommended_vehicle_auto_widget}). 수동 선택 필요."
                    elif not recommended_vehicle_auto_widget and (st.session_state.get('total_volume', 0.0) > 0 or st.session_state.get('total_weight', 0.0) > 0): error_msg += "계산/정보 부족. 수동 선택 필요."
                    else: error_msg += "물품 미선택 또는 정보 부족. 수동 선택 필요."
                    st.error(error_msg)

            else: # Manual selection mode
                if not available_trucks_widget:
                    st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    current_index_widget = 0
                    # Ensure the current manual selection is valid for the available trucks
                    if current_manual_selection_widget not in available_trucks_widget:
                        current_manual_selection_widget = available_trucks_widget[0] # Default to first if invalid
                        st.session_state.manual_vehicle_select_value = current_manual_selection_widget # Update state
                    # Find index for selectbox
                    if current_manual_selection_widget:
                        try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError: current_index_widget = 0

                    st.selectbox("수동으로 차량 선택:",
                                 available_trucks_widget,
                                 index=current_index_widget,
                                 key="manual_vehicle_select_value",
                                 on_change=update_basket_quantities)

                    manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                    if manual_selected_display:
                        st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                        spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, 'vehicle_specs') else None
                        if spec_manual:
                            st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
    st.divider()


    # --- Work Conditions & Options ---
    # (원본 코드 유지)
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
             # Ensure the state is False if option is not available
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

    # --- Cost Adjustment & Deposit ---
    # (원본 코드 유지)
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        with col_adj1: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with col_adj2: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with col_adj3: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
    st.divider()


    # --- Final Quote Results ---
    # (원본 코드 유지)
    st.header("💵 최종 견적 결과")
    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle')
    total_cost = 0; cost_items = []; personnel_info = {}; has_cost_error = False; can_gen_pdf = False; can_gen_final_excel = False

    if final_selected_vehicle_calc:
        try:
            current_state_dict = st.session_state.to_dict()
            total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)
            total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
            st.session_state["final_adjusted_cost"] = total_cost_num # Store for downstream use
            has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False

            try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0))
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            if has_cost_error:
                error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
                st.error(f"비용 계산 오류: {error_item[2]}" if error_item and len(error_item)>2 else "비용 계산 중 오류 발생")
            elif cost_items:
                df_display = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"])
                st.dataframe(
                    df_display.style.format({"금액": "{:,.0f}"})
                                   .set_properties(**{'text-align': 'right'}, subset=['금액'])
                                   .set_properties(**{'text-align': 'left'}, subset=['항목', '비고']),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("ℹ️ 계산된 비용 항목이 없습니다.")
            st.write("")

            special_notes_display = st.session_state.get('special_notes')
            if special_notes_display and special_notes_display.strip():
                st.subheader("📝 고객요구사항")
                st.info(special_notes_display) # Use st.info for better visibility

            # --- Move Info Summary ---
            st.subheader("📋 이사 정보 요약")
            summary_generated = False
            try:
                 # Ensure functions are callable before calling
                if not callable(getattr(pdf_generator, 'generate_excel', None)):
                    raise ImportError("pdf_generator.generate_excel is not available or callable.")
                if not isinstance(personnel_info, dict):
                    personnel_info = {} # Ensure it's a dict

                # Generate summary excel data in memory
                excel_data_summary = pdf_generator.generate_excel(
                    current_state_dict, cost_items, total_cost, personnel_info
                )

                if excel_data_summary:
                    excel_buffer = io.BytesIO(excel_data_summary)
                    xls = pd.ExcelFile(excel_buffer)
                    if "견적 정보" in xls.sheet_names and "비용 내역 및 요약" in xls.sheet_names:
                        # Parse sheets - Use header=0 to get correct columns if header exists
                        df_info = xls.parse("견적 정보", header=0) # Assuming first row is header
                        df_cost = xls.parse("비용 내역 및 요약", header=0) # Assuming first row is header

                        # Convert info sheet to dictionary (safer approach)
                        info_dict = {}
                        if not df_info.empty and '항목' in df_info.columns and '내용' in df_info.columns:
                             info_dict = pd.Series(df_info.내용.values,index=df_info.항목).to_dict()


                        # --- Formatting Helper Functions ---
                        def format_money_manwon_unit(amount):
                            try:
                                # Handle potential non-numeric types before conversion
                                if amount is None or isinstance(amount, str) and not amount.replace(',','').replace('.','',1).isdigit():
                                    return "0"
                                amount_str = str(amount).replace(",", "").split()[0]
                                amount_float = float(amount_str)
                                amount_int = int(amount_float)
                                if amount_int == 0: return "0"
                                manwon_value = amount_int // 10000
                                return f"{manwon_value}"
                            except Exception as format_e:
                                print(f"Error formatting amount '{amount}': {format_e}")
                                return "금액오류"

                        def get_cost_abbr_manwon_unit(kw, abbr, df):
                            if df.empty or '항목' not in df.columns or '금액' not in df.columns:
                                return f"{abbr} 정보 없음"
                            # Iterate safely using .itertuples() or .iterrows()
                            for row in df.itertuples(index=False):
                                item_name = getattr(row, '항목', None)
                                item_amount = getattr(row, '금액', None)
                                if item_name and isinstance(item_name, str) and item_name.strip().startswith(kw):
                                    formatted_amount = format_money_manwon_unit(item_amount)
                                    return f"{abbr} {formatted_amount}"
                            return f"{abbr} 정보 없음" # Return if keyword not found

                        def format_address(addr):
                            return str(addr).strip() if isinstance(addr, str) and addr.strip() and addr.lower() != 'nan' else ""

                        def format_method(m):
                            m = str(m).strip()
                            if "사다리차" in m: return "사"
                            if "승강기" in m: return "승"
                            if "계단" in m: return "계"
                            if "스카이" in m: return "스카이"
                            return "?"
                        # --- End Formatting Helper Functions ---

                        # Extract data for summary display
                        from_addr = format_address(info_dict.get("출발지 주소", st.session_state.get('from_location','')))
                        to_addr = format_address(info_dict.get("도착지 주소", st.session_state.get('to_location','')))
                        phone = info_dict.get("고객 연락처", st.session_state.get('customer_phone',''))
                        vehicle_type = final_selected_vehicle_calc
                        note = format_address(info_dict.get("고객요구사항", st.session_state.get('special_notes',''))) # Use correct key if needed
                        p_info = personnel_info if isinstance(personnel_info, dict) else {}
                        men = p_info.get('final_men', 0); women = p_info.get('final_women', 0)
                        ppl = f"{men}+{women}" if women > 0 else f"{men}"

                        # Basket calculation (ensure keys exist)
                        b_name = "포장 자재 📦"; move_t = st.session_state.base_move_type
                        def get_qty(key_suffix):
                           try: return int(st.session_state.get(f"qty_{move_t}_{b_name}_{key_suffix}", 0))
                           except: return 0

                        q_b = get_qty("바구니")
                        # Handle potential naming variation for medium box/basket
                        q_m = get_qty("중박스") if f"qty_{move_t}_{b_name}_중박스" in st.session_state else get_qty("중자바구니")
                        q_c = get_qty("옷바구니") # Assuming this key exists if needed
                        q_k = get_qty("책바구니")
                        bask_parts = []
                        if q_b > 0: bask_parts.append(f"바{q_b}")
                        if q_m > 0: bask_parts.append(f"중{q_m}")
                        if q_c > 0: bask_parts.append(f"옷{q_c}")
                        if q_k > 0: bask_parts.append(f"책{q_k}")
                        bask = " ".join(bask_parts)

                        cont_fee_str = get_cost_abbr_manwon_unit("계약금 (-)", "계", df_cost)
                        rem_fee_str = get_cost_abbr_manwon_unit("잔금 (VAT 별도)", "잔", df_cost)
                        w_from = format_method(info_dict.get("출발 작업", st.session_state.get('from_method','')))
                        w_to = format_method(info_dict.get("도착 작업", st.session_state.get('to_method','')))
                        work = f"출{w_from}도{w_to}"

                        # Display summary lines
                        addr_separator = " - " if from_addr and to_addr else " "
                        first_line = f"{from_addr}{addr_separator}{to_addr} {vehicle_type}"
                        st.text(first_line.strip()); st.text("")
                        if phone and phone != '-': st.text(phone); st.text("")
                        personnel_line = f"{vehicle_type} {ppl}"; st.text(personnel_line); st.text("")
                        if bask: st.text(bask); st.text("")
                        st.text(work); st.text("")
                        st.text(f"{cont_fee_str} / {rem_fee_str}"); st.text("")
                        if note:
                            notes_list = [n.strip() for n in note.split('.') if n.strip()]
                            for note_line in notes_list: st.text(note_line)
                        summary_generated = True
                    else:
                        st.warning("⚠️ 요약 정보 생성 실패 (필수 Excel 시트 누락: '견적 정보' 또는 '비용 내역 및 요약')")
                else:
                    st.warning("⚠️ 요약 정보 생성 실패 (Excel 데이터 생성 오류)")
            except Exception as e:
                st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}")
                traceback.print_exc()

            if not summary_generated:
                st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")
            st.divider()


        except Exception as calc_err_outer:
            st.error(f"비용 계산 또는 요약 표시 중 오류 발생: {calc_err_outer}")
            traceback.print_exc()
            has_cost_error = True


        # --- File Generation, Download & Sending Section ---
        # (원본 코드 유지)
        st.subheader("📄 견적서 생성, 발송 및 다운로드")
        can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error
        can_gen_final_excel = bool(final_selected_vehicle_calc)

        cols_actions = st.columns(3) # MMS 기능 고려 시 3열 유지

        # --- Column 1: Final Excel ---
        with cols_actions[0]:
            st.markdown("**① Final 견적서 (Excel)**")
            if can_gen_final_excel:
                if st.button("📄 생성: Final 견적서", key="btn_gen_final_excel"):
                    try:
                        # Always recalculate right before generation for latest state
                        latest_total_cost_fe, latest_cost_items_fe, latest_personnel_info_fe = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                        if not isinstance(latest_personnel_info_fe, dict): latest_personnel_info_fe = {}

                        filled_excel_data = excel_filler.fill_final_excel_template(
                            st.session_state.to_dict(), latest_cost_items_fe, latest_total_cost_fe, latest_personnel_info_fe
                        )
                        if filled_excel_data:
                            st.session_state['final_excel_data'] = filled_excel_data
                            st.success("✅ Final Excel 생성 완료!")
                            st.rerun() # Rerun to enable download button
                        else:
                            if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']
                            st.error("❌ Final Excel 생성 실패.")
                    except Exception as fe_err:
                        st.error(f"Final Excel 생성 중 오류: {fe_err}")
                        traceback.print_exc()
                        if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']

                if st.session_state.get('final_excel_data'):
                    ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                    try: now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d')
                    except Exception: now_str = datetime.now().strftime('%y%m%d')
                    fname = f"{ph_part}_{now_str}_Final견적서.xlsx"
                    st.download_button("📥 다운로드 (Final Excel)", st.session_state['final_excel_data'], fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_final_excel')
                elif can_gen_final_excel: # Only show if generation is possible
                     st.caption("생성 버튼 클릭")
            else:
                st.caption("Excel 생성 불가 (차량 미선택)")


        # --- Column 2: PDF Actions (Generate, Download, Email) ---
        with cols_actions[1]:
            st.markdown("**② 고객용 견적서 (PDF)**")
            if can_gen_pdf:
                if st.button("📄 PDF 생성/재생성", key="btn_gen_pdf"): # Combined generate/regenerate label
                    pdf_bytes = None
                    try:
                        pdf_total_cost = st.session_state.get("final_adjusted_cost", 0)
                        # Recalculate if items/personnel info seems missing
                        if not cost_items or not personnel_info:
                             pdf_total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                        if not isinstance(personnel_info, dict): personnel_info = {}

                        pdf_bytes = pdf_generator.generate_pdf(st.session_state.to_dict(), cost_items, pdf_total_cost, personnel_info)
                        st.session_state['pdf_data_customer'] = pdf_bytes
                        if pdf_bytes:
                            st.success("✅ PDF 생성 완료!")
                            st.rerun() # Rerun to enable download/email
                        else:
                            st.error("❌ PDF 생성 실패.")
                            if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']
                    except Exception as pdf_gen_err:
                        st.error(f"PDF 생성 중 예외 발생: {pdf_gen_err}")
                        traceback.print_exc()
                        if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']

                if st.session_state.get('pdf_data_customer'):
                    pdf_bytes_dl = st.session_state.get('pdf_data_customer')
                    ph_part_dl = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                    try: now_str_dl = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M')
                    except Exception: now_str_dl = datetime.now().strftime('%y%m%d_%H%M')
                    fname_dl = f"{ph_part_dl}_{now_str_dl}_이삿날견적서.pdf"
                    st.download_button("📥 다운로드 (PDF)", pdf_bytes_dl, fname_dl, 'application/pdf', key='dl_pdf')
                    st.write("---")
                    st.markdown("**이메일 발송**")
                    default_email = st.session_state.get('customer_email', '')
                    recipient_email = st.text_input("받는 사람 이메일:", value=default_email, key="recipient_email_input")
                    if st.button("📧 PDF 이메일 발송"):
                        if recipient_email and "@" in recipient_email: # Basic check
                            pdf_bytes_to_send = st.session_state.get('pdf_data_customer')
                            if pdf_bytes_to_send:
                                pdf_filename_for_email = fname_dl # Use generated filename
                                email_subject = f"[이삿날] {st.session_state.get('customer_name','고객')}님 견적서입니다."
                                # Use provided customer name in body
                                customer_name_email = st.session_state.get('customer_name', '고객')
                                email_body = f"""안녕하세요, {customer_name_email}님.
요청하신 이삿날 견적서를 첨부하여 보내드립니다.

감사합니다."""
                                with st.spinner("📧 이메일 발송 중..."):
                                    send_success = email_utils.send_quote_email(
                                        recipient_email=recipient_email,
                                        subject=email_subject,
                                        body=email_body,
                                        pdf_bytes=pdf_bytes_to_send,
                                        pdf_filename=pdf_filename_for_email
                                    )
                                if send_success: st.success(f"✅ '{recipient_email}' 주소로 이메일 발송 성공.")
                                else: st.error("❌ 이메일 발송 실패.")
                            else: st.warning("⚠️ 발송할 PDF 없음. 먼저 생성하세요.")
                        else: st.warning("⚠️ 유효한 이메일 주소 입력 필요.")
                elif can_gen_pdf: # Only show if generation is possible
                     st.caption("PDF 생성 버튼 클릭")
            else:
                st.caption("PDF 생성 불가 (차량 미선택 또는 계산 오류)")


        # --- Column 3: MMS Sending ---
        # (MMS 부분은 원본 코드를 최대한 유지하되, 필요한 모듈 import 가정)
        with cols_actions[2]:
            st.markdown("**③ 견적서 이미지 (MMS)**")
            mms_available = False
            try:
                import mms_utils # Check if module exists
                import utils # Ensure utils has the converter
                if callable(getattr(utils, 'convert_pdf_to_image', None)) and \
                   callable(getattr(mms_utils, 'send_mms_with_image', None)):
                    mms_available = True
            except ImportError:
                mms_available = False

            if not mms_available:
                st.caption("MMS 발송 기능 비활성화됨 (필수 모듈/함수 없음)")
            elif can_gen_pdf:
                if st.session_state.get('pdf_data_customer'):
                    # st.write("---") # Redundant separator?
                    default_phone = st.session_state.get('customer_phone', '')
                    recipient_phone = st.text_input("받는 사람 휴대폰 번호:", value=default_phone, key="recipient_phone_input", placeholder="01012345678")
                    if st.button("📱 이미지 MMS 발송"):
                        if recipient_phone and len(recipient_phone) >= 10: # Basic phone check
                            pdf_bytes_mms = st.session_state.get('pdf_data_customer')
                            if pdf_bytes_mms:
                                image_bytes = None
                                with st.spinner("🔄 PDF를 이미지로 변환 중..."):
                                    try:
                                        # Ensure converter exists before calling
                                        if callable(getattr(utils, 'convert_pdf_to_image', None)):
                                             image_bytes = utils.convert_pdf_to_image(pdf_bytes_mms, fmt='JPEG')
                                        else:
                                             st.error("❌ PDF 이미지 변환 함수(utils.convert_pdf_to_image) 없음.")
                                    except Exception as img_conv_err:
                                         st.error(f"❌ 이미지 변환 오류: {img_conv_err}")
                                         traceback.print_exc()

                                if image_bytes:
                                    ph_part_mms = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                                    try: now_str_mms = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d')
                                    except Exception: now_str_mms = datetime.now().strftime('%y%m%d')
                                    image_filename = f"{ph_part_mms}_{now_str_mms}_견적서.jpg"
                                    customer_name_mms = st.session_state.get('customer_name','고객')
                                    mms_text = f"{customer_name_mms}님, 요청하신 이삿날 견적 이미지를 보내드립니다."

                                    with st.spinner(f"📱 MMS 발송 중... ({recipient_phone})"):
                                         try:
                                             # Ensure sender exists before calling
                                             if callable(getattr(mms_utils, 'send_mms_with_image', None)):
                                                 mms_success = mms_utils.send_mms_with_image(
                                                     recipient_phone=recipient_phone,
                                                     image_bytes=image_bytes,
                                                     filename=image_filename,
                                                     text_message=mms_text
                                                 )
                                             else:
                                                 st.error("❌ MMS 발송 함수(mms_utils.send_mms_with_image) 없음.")
                                                 mms_success = False
                                         except Exception as mms_err:
                                              st.error(f"❌ MMS 발송 중 오류: {mms_err}")
                                              traceback.print_exc()
                                              mms_success = False

                                    if mms_success: st.success(f"✅ '{recipient_phone}' 번호로 MMS 발송 성공.")
                                    # No need for explicit 'else' here if error is shown above
                                else:
                                    # Error message already shown if image_bytes is None due to conversion failure
                                    pass
                            else: st.warning("⚠️ MMS로 발송할 PDF 데이터 없음.")
                        else: st.warning("⚠️ 유효한 휴대폰 번호 입력 필요.")
                elif can_gen_pdf: # PDF generated but button not clicked yet
                    st.caption("MMS 발송 버튼 클릭")
            else:
                 st.caption("MMS 발송 불가 (PDF 생성 불가)")

    else: # Vehicle not selected
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시, 파일 생성 및 발송은 차량 선택 후 가능합니다.")

    st.write("---")


# --- End of render_tab3 function ---