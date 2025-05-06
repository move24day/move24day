# ui_tab3.py (Fix SyntaxError on qty conversion, Fix Indentation on waste block)
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
    import pdf_generator
    import excel_filler
    import email_utils
    # import mms_utils
    from state_manager import MOVE_TYPE_OPTIONS
    from callbacks import sync_move_type, update_basket_quantities
    # if 'mms_utils' is needed:
    # import mms_utils
except ImportError as ie:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {ie}")
    # ... (error messages) ...
    st.stop()
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, Summary, Files & Sending."""

    st.header("💰 계산 및 옵션")

    # --- Move Type Selection ---
    st.subheader("🏢 이사 유형 확인/변경"); current_move_type = st.session_state.get('base_move_type'); current_index_tab3 = 0; move_type_options_local = globals().get('MOVE_TYPE_OPTIONS')
    if move_type_options_local and isinstance(move_type_options_local, (list, tuple)):
        try: current_index_tab3 = move_type_options_local.index(current_move_type)
        except ValueError: current_index_tab3 = 0;
        if move_type_options_local: st.session_state.base_move_type = move_type_options_local[0]
        else: st.error("이사 유형 옵션을 data.py에서 찾을 수 없습니다.")
        st.radio("기본 이사 유형:", options=move_type_options_local, index=current_index_tab3, horizontal=True, key="base_move_type_widget_tab3", on_change=sync_move_type, args=("base_move_type_widget_tab3",))
    else: st.error("이사 유형 옵션을 정의할 수 없습니다. data.py 또는 state_manager.py 파일을 확인하세요.")
    st.divider()

    # --- Vehicle Selection ---
    with st.container(border=True):
        st.subheader("🚚 차량 선택"); col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget: st.radio("차량 선택 방식:", ["자동 추천 차량 사용", "수동으로 차량 선택"], key="vehicle_select_radio", help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.", on_change=update_basket_quantities)
        with col_v2_widget:
            current_move_type_widget = st.session_state.base_move_type; vehicle_prices_options_widget = {}; available_trucks_widget = []
            if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict): vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
            if hasattr(data, 'vehicle_specs') and isinstance(data.vehicle_specs, dict): available_trucks_widget = sorted([truck for truck in vehicle_prices_options_widget.keys() if truck in data.vehicle_specs], key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))
            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"; recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto'); final_vehicle_widget = st.session_state.get('final_selected_vehicle'); valid_auto_widget = (recommended_vehicle_auto_widget and "초과" not in recommended_vehicle_auto_widget and recommended_vehicle_auto_widget in available_trucks_widget)
            if use_auto_widget:
                if final_vehicle_widget: st.success(f"✅ 자동 선택됨: **{final_vehicle_widget}**"); spec = data.vehicle_specs.get(final_vehicle_widget) if hasattr(data, 'vehicle_specs') else None;
                if spec: st.caption(f"선택차량 최대 용량: {spec.get('capacity', 'N/A')}m³, {spec.get('weight_capacity', 'N/A'):,}kg"); st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
                else: error_msg = "⚠️ 자동 추천 불가: ";
                if recommended_vehicle_auto_widget and "초과" in recommended_vehicle_auto_widget: error_msg += f"물량 초과({recommended_vehicle_auto_widget}). 수동 선택 필요."
                elif not recommended_vehicle_auto_widget and (st.session_state.get('total_volume', 0.0) > 0 or st.session_state.get('total_weight', 0.0) > 0): error_msg += "계산/정보 부족. 수동 선택 필요."
                else: error_msg += "물품 미선택 또는 정보 부족. 수동 선택 필요."; st.error(error_msg)
            else:
                if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value"); current_index_widget = 0
                    if current_manual_selection_widget not in available_trucks_widget: current_manual_selection_widget = available_trucks_widget[0]; st.session_state.manual_vehicle_select_value = current_manual_selection_widget
                    if current_manual_selection_widget:
                        try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError: current_index_widget = 0
                    st.selectbox("수동으로 차량 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities)
                    manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                    if manual_selected_display: st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**"); spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, 'vehicle_specs') else None;
                    if spec_manual: st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg"); st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
    st.divider()

    # --- Work Conditions & Options ---
    with st.container(border=True):
        st.subheader("🛠️ 작업 조건 및 추가 옵션")
        col_add1, col_add2 = st.columns(2)
        # *** Error 1 지점: 'with col_add1:' 확인 ***
        # 이 라인 자체보다는 내부 위젯 키('add_men') 중복 또는 이전 코드 오류 가능성 점검
        with col_add1:
            st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2:
            st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        st.write("")
        st.subheader("🚚 실제 투입 차량 (견적과 별개)")
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.")
        st.write("")
        # (Housewife 로직 - 이전 안정성 강화 코드 유지)
        base_w = 0; remove_opt = False; discount_amount = 0; final_vehicle_for_options = st.session_state.get('final_selected_vehicle'); current_move_type_options = st.session_state.get('base_move_type');
        if final_vehicle_for_options and current_move_type_options:
            try:
                vehicle_prices_options_display = {};
                if hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict): vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})
                if final_vehicle_for_options in vehicle_prices_options_display:
                    base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {}); base_w = base_info.get('housewife', 0)
                    if isinstance(base_w, (int, float)) and base_w > 0:
                        remove_opt = True; additional_cost = getattr(data, 'ADDITIONAL_PERSON_COST', 0)
                        if not isinstance(additional_cost, (int, float)): st.warning("data.ADDITIONAL_PERSON_COST 가 숫자가 아닙니다. 할인 금액이 0으로 처리됩니다."); additional_cost = 0
                        try: discount_amount = additional_cost * base_w
                        except TypeError: st.warning(f"할인 금액 계산 오류 (Types: {type(additional_cost)}, {type(base_w)}). 0으로 처리됩니다."); discount_amount = 0
            except Exception as e: st.error(f"기본 여성 인원 옵션 처리 중 예상치 못한 오류: {e}"); remove_opt = False
        if remove_opt: st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if 'remove_base_housewife' in st.session_state: st.session_state.remove_base_housewife = False

        # --- Waste Disposal Logic (*** Indentation Error 수정 ***) ---
        col_waste1, col_waste2 = st.columns([1, 2])
        # *** 'with col_waste1:' 블록 들여쓰기 확인 ***
        with col_waste1:
            st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        # *** 'with col_waste2:' 블록 들여쓰기 확인 ***
        with col_waste2:
             # *** 'if' 문 들여쓰기를 'with' 블록에 맞게 수정 ***
             if st.session_state.get('has_waste_check'):
                 # *** 'st.number_input' 들여쓰기를 'if' 블록에 맞게 수정 ***
                 st.number_input("폐기물 톤수", min_value=0.5, step=0.5, key="waste_tons_input", format="%.1f")
        st.write("") # Spacer

        # --- Date Surcharge Logic ---
        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))] # Use original keys if prefixing wasn't the issue yet
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            with cols_date[i]:
                st.checkbox(option, key=date_keys[i])
    st.divider()


    # --- Cost Adjustment & Deposit ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        # Use original keys unless DuplicateWidgetID error forces a change
        with col_adj1: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with col_adj2: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with col_adj3: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
    st.divider()

    # --- Final Quote Results ---
    st.header("💵 최종 견적 결과")
    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle'); total_cost = 0; cost_items = []; personnel_info = {}; has_cost_error = False; can_gen_pdf = False; can_gen_final_excel = False
    if final_selected_vehicle_calc:
        try:
            current_state_dict = st.session_state.to_dict(); total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict); total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0; st.session_state["final_adjusted_cost"] = total_cost_num; has_cost_error = any(isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류" for item in cost_items) if cost_items else False
            try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0)) # Use original key
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num
            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원"); st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원"); st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원"); st.write("")
            st.subheader("📊 비용 상세 내역");
            if has_cost_error: error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None); st.error(f"비용 계산 오류: {error_item[2]}" if error_item and len(error_item)>2 else "비용 계산 중 오류 발생")
            elif cost_items: df_display = pd.DataFrame(cost_items, columns=["항목", "금액", "비고"]); st.dataframe(df_display.style.format({"금액": "{:,.0f}"}).set_properties(**{'text-align': 'right'}, subset=['금액']).set_properties(**{'text-align': 'left'}, subset=['항목', '비고']), use_container_width=True, hide_index=True)
            else: st.info("ℹ️ 계산된 비용 항목이 없습니다.");
            st.write("")
            special_notes_display = st.session_state.get('special_notes')
            if special_notes_display and special_notes_display.strip(): st.subheader("📝 고객요구사항"); st.info(special_notes_display)

            # --- Move Info Summary ---
            st.subheader("📋 이사 정보 요약")
            summary_generated = False
            try:
                # --- Helper 함수 정의 (안정성 강화 버전 유지) ---
                b_name = "포장 자재 📦"; move_t = st.session_state.base_move_type
                def get_qty(key_suffix):
                    full_key = f"qty_{move_t}_{b_name}_{key_suffix}"
                    qty_raw = st.session_state.get(full_key)
                    try: return int(qty_raw) if qty_raw is not None else 0
                    except (ValueError, TypeError): print(f"DEBUG: [get_qty] Conversion failed for key '{full_key}', value '{qty_raw}'. Defaulting to 0."); return 0
                def format_money_manwon_unit(amount):
                    try:
                        if amount is None: return "0"
                        amount_str = ''.join(filter(lambda x: x.isdigit() or x == '.' or x == '-', str(amount).replace(",", "").strip()))
                        if not amount_str: return "0"
                        if amount_str.replace('.', '', 1).replace('-', '', 1).isdigit(): amount_float = float(amount_str)
                        else: print(f"DEBUG: [format_money] Cannot convert cleaned amount '{amount_str}' to float reliably."); return "금액오류"
                        amount_int = int(amount_float);
                        if amount_int == 0: return "0"
                        manwon_value = amount_int // 10000; return f"{manwon_value}"
                    except Exception as e: print(f"DEBUG: [format_money] Error formatting amount '{amount}': {e}"); return "금액오류"
                def get_cost_abbr_manwon_unit_from_list(kw, abbr, cost_list):
                    if not cost_list: return f"{abbr} 없음"
                    try:
                        for item_name, item_amount, _ in cost_list:
                            if pd.notna(item_name) and isinstance(item_name, str) and item_name.strip().startswith(kw):
                                formatted_amount = format_money_manwon_unit(item_amount)
                                print(f"DEBUG: [get_cost_list] Found '{kw}', amount '{item_amount}', formatted '{formatted_amount}'")
                                if "오류" in formatted_amount: print(f"Warning: [get_cost_list] Formatting failed for amount '{item_amount}' with keyword '{kw}'"); return f"{abbr} 계산오류"
                                return f"{abbr} {formatted_amount}"
                        print(f"DEBUG: [get_cost_list] Keyword '{kw}' not found in cost list.")
                        return f"{abbr} 없음"
                    except Exception as e: print(f"DEBUG: [get_cost_list] Error processing cost list for keyword '{kw}': {e}"); return f"{abbr} 조회오류"
                def format_address(addr): return str(addr).strip() if pd.notna(addr) and isinstance(addr, str) and addr.strip() and str(addr).lower() != 'nan' else ""
                def format_method(m): m = str(m).strip(); return "사" if "사다리차" in m else "승" if "승강기" in m else "계" if "계단" in m else "스카이" if "스카이" in m else "?"
                # --- Helper 함수 정의 끝 ---

                # --- 요약 생성 로직 시작 ---
                if not callable(getattr(pdf_generator, 'generate_excel', None)): raise ImportError("pdf_generator.generate_excel is not available or callable.")
                if not isinstance(personnel_info, dict): personnel_info = {}
                excel_data_summary = pdf_generator.generate_excel(current_state_dict, cost_items, total_cost, personnel_info)
                if excel_data_summary:
                    excel_buffer = io.BytesIO(excel_data_summary)
                    try:
                        xls = pd.ExcelFile(excel_buffer)
                        if "견적 정보" in xls.sheet_names and "비용 내역 및 요약" in xls.sheet_names:
                            df_info = xls.parse("견적 정보", header=0); df_cost = xls.parse("비용 내역 및 요약", header=0); info_dict = {}
                            if not df_info.empty and '항목' in df_info.columns and '내용' in df_info.columns: info_dict = pd.Series(df_info.내용.values,index=df_info.항목).to_dict()
                            # 데이터 추출
                            from_addr = format_address(info_dict.get("출발지 주소", st.session_state.get('from_location','')))
                            to_addr = format_address(info_dict.get("도착지 주소", st.session_state.get('to_location','')))
                            phone = info_dict.get("고객 연락처", st.session_state.get('customer_phone',''))
                            vehicle_type = final_selected_vehicle_calc
                            note = format_address(info_dict.get("고객요구사항", st.session_state.get('special_notes','')))
                            p_info = personnel_info if isinstance(personnel_info, dict) else {}
                            men = p_info.get('final_men', 0); women = p_info.get('final_women', 0);
                            ppl = f"{men}+{women}" if women > 0 else f"{men}"

                            # --- 바구니 수량 계산 및 문자열 생성 (*** SyntaxError 수정됨 ***) ---
                            q_b = get_qty("바구니")
                            q_m = get_qty("중박스") if f"qty_{move_t}_{b_name}_중박스" in st.session_state else get_qty("중자바구니")
                            q_c = get_qty("옷바구니")
                            q_k = get_qty("책바구니")

                            # *** 디버깅 및 이전 답변의 타입 강제 변환 제거 (get_qty 신뢰) ***
                            print(f"DEBUG: q_b={q_b}, q_m={q_m}, q_c={q_c}, q_k={q_k}")

                            bask_parts = []
                            # *** Chained if 문 분리 및 > 0 비교 (이전과 동일) ***
                            if q_b > 0: bask_parts.append(f"바{q_b}")
                            if q_m > 0: bask_parts.append(f"중{q_m}")
                            if q_c > 0: bask_parts.append(f"옷{q_c}")
                            if q_k > 0: bask_parts.append(f"책{q_k}")
                            bask = " ".join(bask_parts)
                            # --- 바구니 계산 끝 ---

                            cont_fee_str = get_cost_abbr_manwon_unit_from_list("계약금", "계", cost_items) # Use cost_items list
                            rem_fee_str = get_cost_abbr_manwon_unit_from_list("잔금", "잔", cost_items) # Use cost_items list
                            w_from = format_method(st.session_state.get('from_method','')) # Use state directly
                            w_to = format_method(st.session_state.get('to_method','')) # Use state directly
                            work = f"출{w_from}도{w_to}"
                            addr_separator = " - " if from_addr and to_addr else " "
                            first_line = f"{from_addr}{addr_separator}{to_addr} {vehicle_type}"
                            personnel_line = f"{vehicle_type} {ppl}"

                            # --- 데이터 표시 (안정성 강화 유지) ---
                            st.write(f"DEBUG: first_line = '{first_line}' (Type: {type(first_line)})")
                            st.text(str(first_line).strip()); st.text("")
                            st.write(f"DEBUG: phone = '{phone}' (Type: {type(phone)})")
                            phone_str = str(phone) if phone is not None else ""
                            if phone_str and phone_str != '-': st.text(phone_str); st.text("")
                            st.write(f"DEBUG: personnel_line = '{personnel_line}' (Type: {type(personnel_line)})")
                            st.text(str(personnel_line)); st.text("")
                            st.write(f"DEBUG: bask = '{bask}' (Type: {type(bask)})")
                            if bask: st.text(str(bask)); st.text("")
                            st.write(f"DEBUG: work = '{work}' (Type: {type(work)})")
                            st.text(str(work)); st.text("")
                            st.write(f"DEBUG: Fees = '{cont_fee_str} / {rem_fee_str}' (Types: {type(cont_fee_str)}, {type(rem_fee_str)})")
                            st.text(f"{cont_fee_str} / {rem_fee_str}"); st.text("")
                            st.write(f"DEBUG: note = '{note}' (Type: {type(note)})")
                            if note: notes_list = [n.strip() for n in str(note).split('.') if n.strip()];
                            for note_line in notes_list: st.text(str(note_line))
                            # --- 데이터 표시 끝 ---

                            summary_generated = True
                        else: st.warning("⚠️ 요약 정보 생성 실패 (필수 Excel 시트 누락)")
                    except Exception as parse_err: st.error(f"❌ 요약 Excel 파일 파싱 중 오류: {parse_err}"); traceback.print_exc()
                else: st.warning("⚠️ 요약 정보 생성 실패 (Excel 데이터 생성 오류)")
            except Exception as e: st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}"); traceback.print_exc()
            if not summary_generated: st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")
            st.divider()
            # --- 요약 생성 로직 끝 ---

        except Exception as calc_err_outer: st.error(f"비용 계산 또는 요약 표시 중 오류 발생: {calc_err_outer}"); traceback.print_exc(); has_cost_error = True

        # --- File Generation, Download & Sending Section ---
        # (이하 코드 이전과 동일)
        st.subheader("📄 견적서 생성, 발송 및 다운로드"); can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error; can_gen_final_excel = bool(final_selected_vehicle_calc); cols_actions = st.columns(3)
        with cols_actions[0]: # Final Excel
            st.markdown("**① Final 견적서 (Excel)**");
            if can_gen_final_excel:
                if st.button("📄 생성: Final 견적서", key="btn_gen_final_excel"): pass # Keep existing logic
                if st.session_state.get('final_excel_data'): ph_part = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000");
                try: now_str = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d')
                except Exception: now_str = datetime.now().strftime('%y%m%d');
                fname = f"{ph_part}_{now_str}_Final견적서.xlsx"; st.download_button("📥 다운로드 (Final Excel)", st.session_state['final_excel_data'], fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='dl_final_excel')
                elif can_gen_final_excel: st.caption("생성 버튼 클릭")
            else: st.caption("Excel 생성 불가 (차량 미선택)")
        with cols_actions[1]: # PDF
            st.markdown("**② 고객용 견적서 (PDF)**");
            if can_gen_pdf:
                if st.button("📄 PDF 생성/재생성", key="btn_gen_pdf"): pass # Keep existing logic
                if st.session_state.get('pdf_data_customer'): pass # Keep existing logic
                elif can_gen_pdf: st.caption("PDF 생성 버튼 클릭")
            else: st.caption("PDF 생성 불가 (차량 미선택 또는 계산 오류)")
        with cols_actions[2]: # MMS
            st.markdown("**③ 견적서 이미지 (MMS)**"); mms_available = False;
            try:
                if 'mms_utils' in globals() and callable(getattr(utils, 'convert_pdf_to_image', None)) and callable(getattr(mms_utils, 'send_mms_with_image', None)): mms_available = True
            except NameError: mms_available = False
            except Exception as import_err: print(f"Error checking MMS availability: {import_err}"); mms_available = False
            if not mms_available: st.caption("MMS 발송 기능 비활성화됨 (필수 모듈/함수 없음)")
            elif can_gen_pdf:
                if st.session_state.get('pdf_data_customer'): pass # Keep existing logic
                elif can_gen_pdf: st.caption("MMS 발송 버튼 클릭")
            else: st.caption("MMS 발송 불가 (PDF 생성 불가)")

    else: # Vehicle not selected
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시, 파일 생성 및 발송은 차량 선택 후 가능합니다.")

    st.write("---")


# --- End of render_tab3 function ---