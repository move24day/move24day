# excel_filler.py (get_item_qty 삭제, utils.get_item_qty 사용)

import openpyxl
import io
import streamlit as st
import os
import traceback
from datetime import date
import re
import utils # <--- utils 모듈 임포트

try:
    import data
except ImportError:
    st.error("data.py 파일을 찾을 수 없습니다. excel_filler.py와 같은 폴더에 있는지 확인하세요.")
    data = None

# --- HELPER 함수 get_item_qty 정의 *삭제* ---

# --- 수정된 get_tv_qty (utils 사용) ---
def get_tv_qty(state_data):
    """모든 크기의 TV 수량을 합산하여 반환 (utils.get_item_qty 사용)"""
    if not data or not hasattr(data, 'items') or not isinstance(data.items, dict): return 0
    total_tv_qty = 0
    tv_keys = [key for key in data.items if key.startswith("TV(")]
    for tv_item_name in tv_keys:
        # utils의 함수 호출로 변경
        total_tv_qty += utils.get_item_qty(state_data, tv_item_name)
    return total_tv_qty
# --- 헬퍼 함수 끝 ---


def fill_final_excel_template(state_data, calculated_cost_items, total_cost, personnel_info):
    """
    final.xlsx 템플릿을 열고 값을 채웁니다.
    (B26+ 고객요구사항, B7 차량 톤수, D8 장롱 1/3 수량, utils.get_item_qty 사용 적용)
    """
    if not data:
        st.error("data.py 모듈 로드 실패로 Excel 생성을 진행할 수 없습니다.")
        return None

    try:
        # final.xlsx 경로 설정
        script_dir = os.path.dirname(__file__) if "__file__" in locals() else "."
        final_xlsx_path = os.path.join(script_dir, "final.xlsx")

        if not os.path.exists(final_xlsx_path):
            st.error(f"템플릿 파일 '{final_xlsx_path}'을 찾을 수 없습니다.")
            print(f"Error: Template file not found at '{final_xlsx_path}'")
            return None

        wb = openpyxl.load_workbook(final_xlsx_path)
        # 시트 이름 확인 필요 (활성 시트 또는 특정 이름)
        # ws = wb.active
        ws = wb['Sheet1'] # 예시: 실제 시트 이름 사용 ('Sheet1' 등)

        print(f"INFO [Excel Filler]: Template '{final_xlsx_path}' loaded, using sheet '{ws.title}'")

        # --- 1. 기본 정보 입력 ---
        # ... (기존 기본 정보 입력 로직 - 변경 없음) ...
        move_type_str = ( ("보관 " if state_data.get('is_storage_move') else "") + ("사무실 " if "사무실" in state_data.get('base_move_type', "") else "") + ("장거리 " if state_data.get('apply_long_distance') else "") + ("가정" if "가정" in state_data.get('base_move_type', "") else "") ).strip() or state_data.get('base_move_type', "")
        ws['J1'] = move_type_str; ws['C2'] = state_data.get('customer_name', ''); ws['G2'] = state_data.get('customer_phone', '')
        moving_date_val = state_data.get('moving_date');
        if isinstance(moving_date_val, date): ws['K3'] = moving_date_val; ws['K3'].number_format = 'yyyy-mm-dd'
        elif moving_date_val: ws['K3'] = str(moving_date_val)
        else: ws['K3'] = ''
        ws['C3'] = state_data.get('from_location', ''); ws['C4'] = state_data.get('to_location', '')
        try: ws['L5'] = int(personnel_info.get('final_men', 0) or 0)
        except (ValueError, TypeError): ws['L5'] = 0
        try: ws['L6'] = int(personnel_info.get('final_women', 0) or 0)
        except (ValueError, TypeError): ws['L6'] = 0
        from_floor_str = str(state_data.get('from_floor', '')).strip(); ws['D5'] = f"{from_floor_str}층" if from_floor_str else ''
        to_floor_str = str(state_data.get('to_floor', '')).strip(); ws['D6'] = f"{to_floor_str}층" if to_floor_str else ''
        ws['E5'] = state_data.get('from_method', ''); ws['E6'] = state_data.get('to_method', '')

        # --- 차량 정보 (B7: 톤수만, H7: 실제 투입) ---
        # B7: 선택 차량 - '톤' 제외 수정 적용
        selected_vehicle = state_data.get('final_selected_vehicle', '')
        vehicle_tonnage = '';
        if isinstance(selected_vehicle, str) and selected_vehicle.strip():
            try:
                match = re.search(r'(\d+(\.\d+)?)', selected_vehicle);
                if match: vehicle_tonnage = match.group(1)
                else: vehicle_tonnage_cleaned = re.sub(r'[^\d.]', '', selected_vehicle); vehicle_tonnage = vehicle_tonnage_cleaned if vehicle_tonnage_cleaned else ''
            except Exception as e: print(f"ERROR [Excel Filler B7]: Error processing vehicle: {e}"); vehicle_tonnage = ''
        elif selected_vehicle: vehicle_tonnage = str(selected_vehicle)
        ws['B7'] = vehicle_tonnage

        # H7: 실제 투입 차량 정보 (기존 로직 유지)
        dispatched_parts = []; dispatched_1t = state_data.get('dispatched_1t', 0); dispatched_2_5t = state_data.get('dispatched_2_5t', 0); dispatched_3_5t = state_data.get('dispatched_3_5t', 0); dispatched_5t = state_data.get('dispatched_5t', 0)
        try: dispatched_1t = int(dispatched_1t or 0)
        except: dispatched_1t = 0
        try: dispatched_2_5t = int(dispatched_2_5t or 0)
        except: dispatched_2_5t = 0
        try: dispatched_3_5t = int(dispatched_3_5t or 0)
        except: dispatched_3_5t = 0
        try: dispatched_5t = int(dispatched_5t or 0)
        except: dispatched_5t = 0
        if dispatched_1t > 0: dispatched_parts.append(f"1톤: {dispatched_1t}")
        if dispatched_2_5t > 0: dispatched_parts.append(f"2.5톤: {dispatched_2_5t}")
        if dispatched_3_5t > 0: dispatched_parts.append(f"3.5톤: {dispatched_3_5t}")
        if dispatched_5t > 0: dispatched_parts.append(f"5톤: {dispatched_5t}")
        ws['H7'] = ", ".join(dispatched_parts) if dispatched_parts else ''

        # --- 2. 비용 정보 입력 (기존 로직 유지) ---
        basic_fare = 0; ladder_from = 0; ladder_to = 0; sky_cost=0; storage_cost=0; long_dist_cost=0; waste_cost=0; add_person_cost=0; date_surcharge=0; regional_surcharge=0; adjustment=0
        if calculated_cost_items and isinstance(calculated_cost_items, list):
            for item in calculated_cost_items:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    label, amount_raw = item[0], item[1];
                    try: amount = int(amount_raw)
                    except (ValueError, TypeError): amount = 0
                    if label == '기본 운임': basic_fare = amount
                    elif label == '출발지 사다리차': ladder_from = amount
                    elif label == '도착지 사다리차': ladder_to = amount
                    elif label == '스카이 장비': sky_cost = amount
                    elif label == '보관료': storage_cost = amount
                    elif label == '장거리 운송료': long_dist_cost = amount
                    elif label == '폐기물 처리(톤)': waste_cost = amount
                    elif label == '추가 인력': add_person_cost = amount
                    elif label == '날짜 할증': date_surcharge = amount
                    elif label == '지방 사다리 추가요금': regional_surcharge = amount
                    elif "조정" in label: adjustment += amount
        ws['F22'] = basic_fare; ws['F23'] = ladder_from; ws['F24'] = ladder_to
        try: deposit_amount = int(state_data.get('deposit_amount', 0))
        except (ValueError, TypeError): deposit_amount = 0
        ws['J23'] = deposit_amount
        try: total_cost_num = int(total_cost)
        except (ValueError, TypeError): total_cost_num = 0
        ws['F25'] = total_cost_num
        remaining_balance = total_cost_num - deposit_amount
        ws['J24'] = remaining_balance

        # --- 3. 고객 요구사항 입력 (B26 셀부터 순차 기록 - 기존 수정 유지) ---
        # !!! 병합된 셀 경고는 여전히 유효합니다 !!!
        special_notes_str = state_data.get('special_notes', ''); start_row_notes = 26
        max_possible_note_lines = 20
        for i in range(max_possible_note_lines):
             clear_cell_addr = f"B{start_row_notes + i}";
             try:
                 if ws[clear_cell_addr].value is not None: ws[clear_cell_addr].value = None
             except Exception as e: print(f"Warning [Excel Filler B26+]: Could not clear cell {clear_cell_addr}: {e}")
        if special_notes_str:
            notes_parts = [part.strip() for part in special_notes_str.split('.') if part.strip()]
            for i, part in enumerate(notes_parts):
                target_cell_notes = f"B{start_row_notes + i}";
                try: ws[target_cell_notes] = part
                except Exception as e: print(f"ERROR [Excel Filler B26+]: Failed to write note to {target_cell_notes}: {e}")
        else:
             try:
                 if ws['B26'].value is not None: ws['B26'] = None
             except Exception as e: print(f"Warning [Excel Filler B26+]: Could not clear B26 for empty notes: {e}")


        # --- 4. 품목 수량 입력 (utils.get_item_qty 사용, D8 장롱 수량 처리) ---
        # D열
        # D8: 장롱 수량 1/3 계산 적용
        original_jangrong_qty = utils.get_item_qty(state_data, '장롱') # utils 사용
        jangrong_formatted_qty = "0.0"
        try: calculated_qty = original_jangrong_qty / 3.0; jangrong_formatted_qty = f"{calculated_qty:.1f}"
        except ZeroDivisionError: jangrong_formatted_qty = "0.0"
        except Exception as e: print(f"ERROR [Excel Filler D8]: Error calculating Jangrong qty: {e}"); jangrong_formatted_qty = "Error"
        ws['D8'] = jangrong_formatted_qty # 계산된 값 입력

        # 다른 품목들은 utils.get_item_qty 호출
        ws['D9'] = utils.get_item_qty(state_data, '더블침대')
        ws['D10'] = utils.get_item_qty(state_data, '서랍장')
        ws['D11'] = utils.get_item_qty(state_data, '서랍장(3단)')
        ws['D12'] = utils.get_item_qty(state_data, '4도어 냉장고')
        ws['D13'] = utils.get_item_qty(state_data, '김치냉장고(일반형)')
        ws['D14'] = utils.get_item_qty(state_data, '김치냉장고(스탠드형)')
        ws['D15'] = utils.get_item_qty(state_data, '소파(3인용)')
        ws['D16'] = utils.get_item_qty(state_data, '소파(1인용)')
        ws['D17'] = utils.get_item_qty(state_data, '식탁(4인)')
        ws['D18'] = utils.get_item_qty(state_data, '에어컨')
        ws['D19'] = utils.get_item_qty(state_data, '장식장')
        ws['D20'] = utils.get_item_qty(state_data, '피아노(디지털)')
        ws['D21'] = utils.get_item_qty(state_data, '세탁기 및 건조기')

        # H열
        ws['H9'] = utils.get_item_qty(state_data, '사무실책상')
        ws['H10'] = utils.get_item_qty(state_data, '책상&의자')
        ws['H11'] = utils.get_item_qty(state_data, '책장')
        ws['H15'] = utils.get_item_qty(state_data, '바구니')
        ws['H16'] = utils.get_item_qty(state_data, '중박스')
        ws['H19'] = utils.get_item_qty(state_data, '화분')
        ws['H20'] = utils.get_item_qty(state_data, '책바구니')

        # L열
        ws['L8'] = utils.get_item_qty(state_data, '스타일러')
        ws['L9'] = utils.get_item_qty(state_data, '안마기')
        ws['L10'] = utils.get_item_qty(state_data, '피아노(일반)')
        ws['L12'] = get_tv_qty(state_data) # 수정된 get_tv_qty 호출
        ws['L16'] = utils.get_item_qty(state_data, '금고')
        ws['L17'] = utils.get_item_qty(state_data, '앵글')


        # --- 5. 완료된 엑셀 파일을 메모리에 저장 ---
        output = io.BytesIO()
        wb.save(output)
        output.seek(0) # 버퍼 포인터 리셋
        print("INFO [Excel Filler]: Excel file generation complete.")
        return output.getvalue() # 바이트 데이터 반환

    except FileNotFoundError:
        st.error(f"Excel 템플릿 파일 '{final_xlsx_path}'을(를) 찾을 수 없습니다.")
        print(f"Error: Template file not found at '{final_xlsx_path}' during generation.")
        return None
    except Exception as e:
        st.error(f"Excel 생성 중 오류 발생: {e}")
        print(f"Error during Excel generation: {e}")
        traceback.print_exc() # 콘솔/로그에 상세 오류 출력
        return None