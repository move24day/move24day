# ui_tab3.py (사용자 제공 email_utils.py 사용하도록 수정)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date 
import traceback 
import re 

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator
    import excel_filler
    import email_utils # 사용자 제공 email_utils 임포트
    from state_manager import MOVE_TYPE_OPTIONS
    from callbacks import sync_move_type, update_basket_quantities
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    if 'email_utils' in str(e).lower():
        st.warning("email_utils.py 파일이 없거나 로드할 수 없습니다. 이메일 발송 기능이 비활성화됩니다.")
    st.stop()
except Exception as e: 
    st.error(f"UI Tab 3: 모듈 로딩 중 예상치 못한 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


def render_tab3():
    """Renders the UI for Tab 3: Costs, Options, and Downloads."""

    st.header("💰 계산 및 옵션 ")

    # --- Move Type Selection (Tab 3) ---
    st.subheader("🏢 이사 유형 ")
    current_move_type = st.session_state.get('base_move_type')
    move_type_options_local = globals().get('MOVE_TYPE_OPTIONS', [])

    current_index_tab3 = 0
    if move_type_options_local:
        try:
            current_index_tab3 = move_type_options_local.index(current_move_type)
        except (ValueError, TypeError):
            current_index_tab3 = 0
            if current_move_type not in move_type_options_local and move_type_options_local: # 옵션이 있고, 현재 값이 유효하지 않을 때
                 st.session_state.base_move_type = move_type_options_local[0]
                 print("Warning: Resetting base_move_type in Tab 3 due to invalid state.")
                 if 'base_move_type_widget_tab1' in st.session_state:
                      st.session_state.base_move_type_widget_tab1 = move_type_options_local[0]
    else:
        st.error("이사 유형 옵션(MOVE_TYPE_OPTIONS)을 불러올 수 없습니다.")
        return

    st.radio(
        "기본 이사 유형:",
        options=move_type_options_local, index=current_index_tab3, horizontal=True,
        key="base_move_type_widget_tab3",
        on_change=sync_move_type,
        args=("base_move_type_widget_tab3",)
    )
    st.divider()

    # --- Vehicle Selection ---
    with st.container(border=True):
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])

        with col_v1_widget:
            st.radio(
                "차량 선택 방식:",
                ["자동 추천 차량 사용", "수동으로 차량 선택"],
                key="vehicle_select_radio",
                help="자동 추천을 사용하거나, 목록에서 직접 차량을 선택합니다.",
                on_change=update_basket_quantities
            )

        with col_v2_widget:
            current_move_type_widget = st.session_state.get('base_move_type')
            vehicle_prices_options_widget = {}
            available_trucks_widget = []

            if current_move_type_widget and hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
                vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})

            if vehicle_prices_options_widget and hasattr(data, 'vehicle_specs') and isinstance(data.vehicle_specs, dict):
                available_trucks_widget = sorted(
                    [truck for truck in vehicle_prices_options_widget.keys() if truck in data.vehicle_specs],
                    key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0)
                )

            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_widget = st.session_state.get('recommended_vehicle_auto')
            final_vehicle_widget = st.session_state.get('final_selected_vehicle')

            valid_auto_widget = (recommended_vehicle_auto_widget and
                                "초과" not in recommended_vehicle_auto_widget and
                                recommended_vehicle_auto_widget in available_trucks_widget)

            if use_auto_widget:
                if final_vehicle_widget and final_vehicle_widget in available_trucks_widget:
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
                    if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else:
                        current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                        current_index_widget = 0
                        if current_manual_selection_widget in available_trucks_widget:
                            try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                            except ValueError: current_index_widget = 0
                        else:
                            current_index_widget = 0
                            if available_trucks_widget:
                                st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                        st.selectbox(
                            "수동으로 차량 선택:",
                            available_trucks_widget, index=current_index_widget,
                            key="manual_vehicle_select_value",
                            on_change=update_basket_quantities
                        )
                        manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                        if manual_selected_display:
                            st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                            spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, 'vehicle_specs') else None
                            if spec_manual:
                                st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg")
                                st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
            else: # Manual mode
                if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    current_index_widget = 0
                    if current_manual_selection_widget in available_trucks_widget:
                        try: current_index_widget = available_trucks_widget.index(current_manual_selection_widget)
                        except ValueError: current_index_widget = 0
                    else:
                        current_index_widget = 0
                        if available_trucks_widget:
                             st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                    st.selectbox(
                        "차량 직접 선택:",
                        available_trucks_widget, index=current_index_widget,
                        key="manual_vehicle_select_value",
                        on_change=update_basket_quantities
                    )
                    manual_selected_display = st.session_state.get('manual_vehicle_select_value')
                    if manual_selected_display:
                        st.info(f"ℹ️ 수동 선택됨: **{manual_selected_display}**")
                        spec_manual = data.vehicle_specs.get(manual_selected_display) if hasattr(data, 'vehicle_specs') else None
                        if spec_manual:
                            st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {st.session_state.get('total_volume',0.0):.2f}m³, {st.session_state.get('total_weight',0.0):.2f}kg")
    st.divider()

    # --- Work Conditions & Options ---
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
            st.write("")

        col_add1, col_add2 = st.columns(2)
        with col_add1: st.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men", help="기본 인원 외 추가로 필요한 남성 작업자 수")
        with col_add2: st.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women", help="기본 인원 외 추가로 필요한 여성 작업자 수")
        st.write("")

        st.subheader("🚚 실제 투입 차량 ")
        dispatched_cols = st.columns(4)
        with dispatched_cols[0]: st.number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        with dispatched_cols[1]: st.number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        with dispatched_cols[2]: st.number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        with dispatched_cols[3]: st.number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.")
        st.write("")

        base_w = 0
        remove_opt = False
        discount_amount = 0
        final_vehicle_for_options = st.session_state.get('final_selected_vehicle')
        current_move_type_options = st.session_state.get('base_move_type')

        if current_move_type_options and hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
            vehicle_prices_options_display = data.vehicle_prices.get(current_move_type_options, {})
            if final_vehicle_for_options and final_vehicle_for_options in vehicle_prices_options_display:
                base_info = vehicle_prices_options_display.get(final_vehicle_for_options, {})
                base_w_raw = base_info.get('housewife')
                try:
                    base_w = int(base_w_raw) if base_w_raw is not None else 0
                    if base_w > 0:
                         remove_opt = True
                         add_cost = getattr(data, 'ADDITIONAL_PERSON_COST', 0)
                         if isinstance(add_cost, (int, float)):
                             discount_amount = add_cost * base_w
                         else:
                             st.warning("data.ADDITIONAL_PERSON_COST가 숫자가 아닙니다. 할인 금액이 0으로 처리됩니다.")
                             discount_amount = 0
                except (ValueError, TypeError):
                     base_w = 0
                     print(f"Warning: Non-numeric 'housewife' value encountered: {base_w_raw}")

        if remove_opt:
            st.checkbox(f"기본 여성({base_w}명) 제외 (비용 할인: -{discount_amount:,.0f}원)", key="remove_base_housewife")
        else:
            if 'remove_base_housewife' in st.session_state:
                st.session_state.remove_base_housewife = False

        col_waste1, col_waste2 = st.columns([1, 2])
        with col_waste1: st.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check", help="톤 단위 직접 입력 방식입니다.")
        with col_waste2:
            if st.session_state.get('has_waste_check'):
                waste_cost_per_ton = getattr(data, 'WASTE_DISPOSAL_COST_PER_TON', 0)
                waste_cost_display = 0
                if isinstance(waste_cost_per_ton, (int, float)):
                    waste_cost_display = waste_cost_per_ton
                else:
                    st.warning("data.WASTE_DISPOSAL_COST_PER_TON 정의 오류.")
                st.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input", format="%.1f")
                if waste_cost_display > 0:
                    st.caption(f"💡 1톤당 {waste_cost_display:,}원 추가 비용 발생")

        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_surcharges_defined = hasattr(data, 'special_day_prices') and isinstance(data.special_day_prices, dict)
        if not date_surcharges_defined:
            st.warning("data.py에 날짜 할증(special_day_prices) 정보가 없습니다.")

        date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            with cols_date[i]:
                 surcharge_amount = 0
                 if date_surcharges_defined:
                     surcharge_amount = data.special_day_prices.get(option, 0)
                 help_text = f"{surcharge_amount:,}원 할증" if surcharge_amount > 0 else ""
                 st.checkbox(option, key=date_keys[i], help=help_text)
    st.divider()

    # --- Cost Adjustment & Deposit ---
    with st.container(border=True):
        st.subheader("💰 비용 조정 및 계약금")
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        with col_adj1: st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d", help="고객에게 받을 계약금 입력")
        with col_adj2: st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", help="견적 금액 외 추가 할증(+) 또는 할인(-) 금액 입력", format="%d")
        with col_adj3: st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d", help="추가되는 사다리차 비용")
    st.divider()

    # --- Final Quote Results ---
    st.header("💵 최종 견적 결과")

    final_selected_vehicle_calc = st.session_state.get('final_selected_vehicle')
    total_cost = 0
    cost_items = []
    personnel_info = {}
    has_cost_error = False

    if final_selected_vehicle_calc:
        try:
            current_state_dict = st.session_state.to_dict()
            total_cost, cost_items, personnel_info = calculations.calculate_total_moving_cost(current_state_dict)

            total_cost_num = total_cost if isinstance(total_cost, (int, float)) else 0
            try: deposit_amount_num = int(st.session_state.get('deposit_amount', 0))
            except (ValueError, TypeError): deposit_amount_num = 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            error_item = next((item for item in cost_items if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
            if error_item:
                has_cost_error = True
                st.error(f"비용 계산 오류: {error_item[2]}" if len(error_item)>2 else "비용 계산 중 오류 발생")
            elif cost_items:
                valid_cost_items = [item for item in cost_items if isinstance(item, (list, tuple)) and len(item) >= 2]
                if valid_cost_items:
                    df_display = pd.DataFrame(valid_cost_items, columns=["항목", "금액", "비고"])
                    st.dataframe(
                        df_display.style.format({"금액": "{:,.0f}"})
                                    .set_properties(**{'text-align': 'right'}, subset=['금액'])
                                    .set_properties(**{'text-align': 'left'}, subset=['항목', '비고']),
                        use_container_width=True, hide_index=True
                    )
                else: st.info("ℹ️ 유효한 비용 항목이 없습니다.")
            else: st.info("ℹ️ 계산된 비용 항목이 없습니다.")
            st.write("")

            special_notes_display = st.session_state.get('special_notes')
            if special_notes_display and special_notes_display.strip():
                st.subheader("📝 고객요구사항")
                st.info(special_notes_display)

            st.subheader("📋 이사 정보 요약")
            summary_generated = False
            try:
                if not (hasattr(pdf_generator, 'generate_excel') and callable(pdf_generator.generate_excel)):
                     st.error("Error: pdf_generator.generate_excel 함수를 찾을 수 없습니다.")
                     raise ImportError("generate_excel not found in pdf_generator")

                excel_data_summary = pdf_generator.generate_excel(current_state_dict, cost_items, total_cost, personnel_info)

                if excel_data_summary:
                    excel_buffer = io.BytesIO(excel_data_summary)
                    try: xls = pd.ExcelFile(excel_buffer, engine='openpyxl')
                    except Exception as pd_err:
                        st.warning(f"Pandas ExcelFile 읽기 실패, 기본 엔진 시도 중: {pd_err}")
                        excel_buffer.seek(0)
                        try: xls = pd.ExcelFile(excel_buffer)
                        except Exception as pd_err_fallback:
                            st.error(f"Excel 요약 데이터 읽기 실패: {pd_err_fallback}")
                            raise

                    required_sheets = ["견적 정보", "비용 내역 및 요약"]
                    if all(sheet in xls.sheet_names for sheet in required_sheets):
                        try:
                             df_info = xls.parse("견적 정보", header=0)
                             df_cost = xls.parse("비용 내역 및 요약", header=0)
                        except Exception as parse_err:
                             st.error(f"Excel 시트 파싱 오류: {parse_err}")
                             raise

                        info_dict = {}
                        if not df_info.empty and '항목' in df_info.columns and '내용' in df_info.columns:
                            try: info_dict = df_info.set_index('항목')['내용'].to_dict()
                            except Exception as dict_conv_err:
                                st.warning(f"견적 정보 시트 -> 사전 변환 오류: {dict_conv_err}")
                                info_dict = {}

                        def format_money_kor(amount):
                            try:
                                amount_float = float(str(amount).replace(",", "").split()[0])
                                amount_int = int(amount_float)
                                if amount_int >= 10000: return f"{amount_int // 10000}만원"
                                elif amount_int != 0: return f"{amount_int:,}원"
                                else: return "0원"
                            except: return "금액오류"

                        def format_address(addr):
                             addr_str = str(addr).strip()
                             return addr_str if pd.notna(addr) and addr_str and addr_str.lower() != 'nan' else ""

                        def get_cost_abbr(kw, abbr, df):
                            if not isinstance(df, pd.DataFrame) or df.empty or '항목' not in df.columns or '금액' not in df.columns:
                                return f"{abbr} 없음"
                            for index, row in df.iterrows():
                                item_name = row['항목']
                                item_amount = row['금액']
                                if isinstance(item_name, str) and item_name.strip().startswith(kw):
                                    return f"{abbr} {format_money_kor(item_amount)}"
                            return f"{abbr} 없음"

                        def format_method(m):
                             m_str = str(m).strip()
                             if "사다리차" in m_str: return "사"
                             if "승강기" in m_str: return "승"
                             if "계단" in m_str: return "계"
                             if "스카이" in m_str: return "스카이"
                             return "?"

                        customer_name = str(info_dict.get("고객명", st.session_state.get('customer_name','')))
                        from_addr = format_address(info_dict.get("출발지", st.session_state.get('from_location','')))
                        to_addr = format_address(info_dict.get("도착지", st.session_state.get('to_location','')))
                        phone = info_dict.get("고객 연락처", st.session_state.get('customer_phone',''))
                        vehicle_type = final_selected_vehicle_calc
                        note = format_address(info_dict.get("고객요구사항", st.session_state.get('special_notes','')))

                        vehicle_tonnage = ""
                        if isinstance(vehicle_type, str):
                             match = re.search(r'(\d+(\.\d+)?\s*톤)', vehicle_type)
                             if match: vehicle_tonnage = match.group(1).strip()
                             else: vehicle_tonnage = vehicle_type

                        p_info = personnel_info if isinstance(personnel_info, dict) else {}
                        men = p_info.get('final_men', 0)
                        women = p_info.get('final_women', 0)
                        ppl = f"{men}+{women}" if women > 0 else f"{men}"

                        b_name = "포장 자재 📦"
                        move_t = st.session_state.get('base_move_type', '')
                        q_b, q_m, q_k, q_mb = 0, 0, 0, 0
                        try:
                             if move_t:
                                 q_b = int(st.session_state.get(f"qty_{move_t}_{b_name}_바구니", 0))
                                 q_m = int(st.session_state.get(f"qty_{move_t}_{b_name}_중자바구니", 0))
                                 q_k = int(st.session_state.get(f"qty_{move_t}_{b_name}_책바구니", 0))
                                 q_mb = int(st.session_state.get(f"qty_{move_t}_{b_name}_중박스", 0))
                        except (ValueError, TypeError) as qty_err: print(f"Warning: Error converting basket quantity: {qty_err}")

                        bask_parts = []
                        if q_b > 0: bask_parts.append(f"바{q_b}")
                        if q_m > 0: bask_parts.append(f"중자{q_m}")
                        if q_mb > 0: bask_parts.append(f"중박{q_mb}")
                        if q_k > 0: bask_parts.append(f"책{q_k}")
                        bask = " ".join(bask_parts)

                        cont_fee = get_cost_abbr("계약금 (-)", "계", df_cost)
                        rem_fee = get_cost_abbr("잔금 (VAT 별도)", "잔", df_cost)
                        w_from = format_method(info_dict.get("출발 작업", st.session_state.get('from_method','')))
                        w_to = format_method(info_dict.get("도착 작업", st.session_state.get('to_method','')))
                        work = f"출{w_from}도{w_to}"

                        st.text(f"{str(from_addr)} -> {str(to_addr)} {vehicle_tonnage}"); st.text("")
                        if customer_name: st.text(f"{customer_name}"); st.text("")
                        phone_str = str(phone)
                        if phone_str and phone_str != '-': st.text(f"{phone_str}"); st.text("")
                        st.text(f"{str(vehicle_type)} | {str(ppl)}"); st.text("")
                        if from_addr: st.text(f"{from_addr}"); st.text("")
                        if to_addr: st.text(f"{to_addr}"); st.text("")
                        if bask: st.text(bask); st.text("")
                        st.text(str(work)); st.text("")
                        st.text(f"{str(cont_fee)} / {str(rem_fee)}"); st.text("")
                        if note:
                             notes_list = [n.strip() for n in note.split('.') if n.strip()]
                             for note_line in notes_list: st.text(note_line)
                        summary_generated = True
                    else: st.warning("⚠️ 요약 정보 생성 실패 (필수 Excel 시트 누락)")
                else: st.warning("⚠️ 요약 정보 생성 실패 (Excel 데이터 생성 오류)")
            except Exception as e:
                st.error(f"❌ 요약 정보 생성 중 오류 발생: {e}")
                traceback.print_exc()
            if not summary_generated: st.info("ℹ️ 요약 정보를 표시할 수 없습니다.")
            st.divider()

            # --- Download and Send Section ---
            st.subheader("📄 견적서 생성, 발송 및 다운로드")
            can_gen_pdf = bool(final_selected_vehicle_calc) and not has_cost_error
            can_gen_final_excel = bool(final_selected_vehicle_calc)

            cols_actions = st.columns([1,1,1]) 

            with cols_actions[0]: # Final Excel
                st.markdown("**① Final 견적서 (Excel)**")
                if can_gen_final_excel:
                    if st.button("📄 생성: Final 견적서", key="btn_gen_final_excel"):
                        with st.spinner("Final Excel 생성 중..."):
                            latest_total_cost_fe, latest_cost_items_fe, latest_personnel_info_fe = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                            filled_excel_data = excel_filler.fill_final_excel_template(
                                st.session_state.to_dict(), latest_cost_items_fe, latest_total_cost_fe, latest_personnel_info_fe
                            )
                        if filled_excel_data:
                            st.session_state['final_excel_data'] = filled_excel_data
                            st.success("✅ Final Excel 생성 완료!")
                        else:
                            if 'final_excel_data' in st.session_state: del st.session_state['final_excel_data']
                            st.error("❌ Final Excel 생성 실패.")
                    if st.session_state.get('final_excel_data'):
                        ph_part_fe = "XXXX"
                        if hasattr(utils, 'extract_phone_number_part'): ph_part_fe = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                        now_str_fe = ""
                        try: now_str_fe = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d')
                        except Exception: now_str_fe = datetime.now().strftime('%y%m%d')
                        fname_fe = f"{ph_part_fe}_{now_str_fe}_Final견적서.xlsx"
                        st.download_button(
                              label="📥 다운로드 (Excel)",
                              data=st.session_state['final_excel_data'],
                              file_name=fname_fe,
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              key='dl_final_excel'
                         )
                    elif 'final_excel_data' not in st.session_state: st.caption("생성 버튼을 눌러주세요.")
                else: st.caption("Excel 생성 불가 (차량 미선택)")

            with cols_actions[1]: # Customer PDF Download
                st.markdown("**② 고객용 견적서 (PDF)**")
                if can_gen_pdf:
                    if st.button("📄 생성: PDF 견적서", key="btn_gen_pdf"):
                        with st.spinner("PDF 견적서 생성 중..."):
                            latest_total_cost_pdf, latest_cost_items_pdf, latest_personnel_info_pdf = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                            pdf_cost_error = any(str(item[0]) == "오류" for item in latest_cost_items_pdf if isinstance(item, (list, tuple)) and len(item)>0)
                            if pdf_cost_error:
                                st.error("❌ PDF 생성 불가: 비용 계산 오류 발생.")
                                if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']
                            else:
                                pdf_bytes = pdf_generator.generate_pdf(
                                    st.session_state.to_dict(), latest_cost_items_pdf, latest_total_cost_pdf, latest_personnel_info_pdf
                                )
                                st.session_state['pdf_data_customer'] = pdf_bytes
                                if pdf_bytes: st.success("✅ PDF 생성 완료!")
                                else:
                                    st.error("❌ PDF 생성 실패.")
                                    if 'pdf_data_customer' in st.session_state: del st.session_state['pdf_data_customer']
                    if st.session_state.get('pdf_data_customer'):
                        ph_part_pdf = "XXXX"
                        if hasattr(utils, 'extract_phone_number_part'): ph_part_pdf = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                        now_str_pdf = ""
                        try: now_str_pdf = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M')
                        except Exception: now_str_pdf = datetime.now().strftime('%y%m%d_%H%M')
                        fname_pdf = f"{ph_part_pdf}_{now_str_pdf}_이삿날견적서.pdf"
                        st.download_button(
                             label="📥 다운로드 (PDF)",
                             data=st.session_state['pdf_data_customer'],
                             file_name=fname_pdf,
                             mime='application/pdf',
                             key='dl_pdf'
                         )
                    elif 'pdf_data_customer' not in st.session_state: st.caption("생성 버튼을 눌러주세요.")
                else: st.caption("PDF 생성 불가 (차량 미선택 또는 비용 오류)")

            with cols_actions[2]: # Email PDF
                st.markdown("**③ 견적서 이메일 발송**")
                customer_email = st.session_state.get('customer_email', '').strip()
                pdf_data_for_email = st.session_state.get('pdf_data_customer')

                # Check if email_utils and its function are available
                email_function_available = hasattr(email_utils, 'send_quote_email') and callable(email_utils.send_quote_email)
                
                if not email_function_available:
                    st.warning("이메일 발송 기능이 로드되지 않았습니다. (email_utils.py 확인 필요)")
                elif pdf_data_for_email and customer_email and can_gen_pdf : 
                    if st.button("📧 PDF 이메일 발송", key="btn_email_pdf"):
                        with st.spinner("이메일 발송 중..."):
                            email_subject = f"[이삿날] {st.session_state.get('customer_name','고객')}님 이사 견적서입니다."
                            email_body = (
                                f"{st.session_state.get('customer_name','고객')}님, 안녕하세요.\n\n"
                                f"이삿날 포장이사 견적서를 첨부 파일로 보내드립니다.\n"
                                f"확인 후 연락 부탁드립니다.\n\n"
                                f"감사합니다.\n이삿날 드림\n"
                                f"연락처: {getattr(data, 'COMPANY_PHONE_1', '회사 연락처 정보 없음')}" # getattr 사용
                            )
                            ph_part_email = "XXXX"
                            if hasattr(utils, 'extract_phone_number_part'): ph_part_email = utils.extract_phone_number_part(st.session_state.get('customer_phone', ''), 4, "0000")
                            now_str_email = ""
                            try: now_str_email = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%y%m%d_%H%M')
                            except Exception: now_str_email = datetime.now().strftime('%y%m%d_%H%M')
                            attachment_filename = f"{ph_part_email}_{now_str_email}_이삿날견적서.pdf"

                            # 사용자 제공 함수 사용
                            send_success = email_utils.send_quote_email(
                                recipient_email=customer_email,
                                subject=email_subject,
                                body=email_body,
                                pdf_bytes=pdf_data_for_email, # 인자 이름 pdf_bytes로 전달
                                pdf_filename=attachment_filename # 인자 이름 pdf_filename으로 전달
                            )
                            if send_success:
                                st.success(f"✅ {customer_email}(으)로 견적서 이메일 발송 완료!")
                            else:
                                st.error("❌ 이메일 발송 실패. 설정을 확인하거나 관리자에게 문의하세요.")
                elif not pdf_data_for_email:
                    st.caption("PDF 생성 후 발송 가능")
                elif not customer_email:
                    st.caption("고객 이메일 정보 없음")
                else: 
                    st.caption("PDF 생성 불가 상태")
        except Exception as calc_err_outer:
            st.error(f"최종 견적 표시 중 오류 발생: {calc_err_outer}")
            traceback.print_exc()
    else:
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시 및 다운로드는 차량 선택 후 가능합니다.")
