# excel_filler.py (병합된 셀 오류 수정, 실제 투입 차량 H7 추가, 셀 매핑 수정, date import 추가)

import openpyxl
import io
import streamlit as st
import os
import traceback # 상세 오류 출력을 위해 추가
from datetime import date # 날짜 타입 비교를 위해 date 임포트

try:
    # data.py 파일 임포트 시도 (App.py와 같은 위치에 있어야 함)
    import data # data.py 필요
except ImportError:
    # data.py 로드 실패 시 사용자에게 알리고 None으로 설정
    st.error("data.py 파일을 찾을 수 없습니다. excel_filler.py와 같은 폴더에 있는지 확인하세요.")
    data = None # data 모듈이 없음을 표시

# --- 헬퍼 함수 정의 ---
def get_item_qty(state_data, item_name_to_find):
    """state_data에서 특정 품목명의 수량을 찾아 반환 (Robust search across sections)"""
    if not data or not hasattr(data, 'item_definitions') or not hasattr(data, 'items'): return 0
    current_move_type = state_data.get('base_move_type');
    if not current_move_type: return 0

    # Search specifically defined sections first
    item_definitions_for_type = data.item_definitions.get(current_move_type, {})
    if isinstance(item_definitions_for_type, dict):
        for section, item_list in item_definitions_for_type.items():
            # if section == "폐기 처리 품목 🗑️": continue # Skip waste
            if isinstance(item_list, list):
                 if item_name_to_find in item_list:
                     # Construct the key based on the found section
                     key = f"qty_{current_move_type}_{section}_{item_name_to_find}"
                     if key in state_data:
                         try: return int(state_data.get(key, 0) or 0)
                         except (ValueError, TypeError): return 0
                     # else:
                         # print(f"Debug: Key '{key}' constructed but not found in state_data for item '{item_name_to_find}'")

    # print(f"Warning: Item '{item_name_to_find}' quantity not found in state_data.")
    return 0 # Return 0 if not found

def get_tv_qty(state_data):
    """모든 크기의 TV 수량을 합산하여 반환"""
    if not data or not hasattr(data, 'items') or not isinstance(data.items, dict): return 0
    total_tv_qty = 0
    # Find all keys in data.items that start with "TV("
    tv_keys = [key for key in data.items if key.startswith("TV(")]
    for tv_item_name in tv_keys:
        total_tv_qty += get_item_qty(state_data, tv_item_name) # Use the robust get_item_qty
    return total_tv_qty
# --- 헬퍼 함수 끝 ---


def fill_final_excel_template(state_data, calculated_cost_items, total_cost, personnel_info):
    """
    final.xlsx 템플릿을 열고, 주어진 이사 데이터로 고정된 셀에 값을 채운 후
    (모든 열을 오른쪽으로 한 칸 이동 가정) 메모리상의 완성된 엑셀 파일을 반환합니다.
    """
    if not data:
         st.error("data.py 모듈 로드 실패로 Excel 생성을 진행할 수 없습니다.")
         return None

    try:
        # Assume final.xlsx is in the same directory as the script
        script_dir = os.path.dirname(__file__) if "__file__" in locals() else "."
        final_xlsx_path = os.path.join(script_dir, "final.xlsx")


        if not os.path.exists(final_xlsx_path):
            st.error(f"템플릿 파일 '{final_xlsx_path}'을 찾을 수 없습니다.")
            print(f"Error: Template file not found at '{final_xlsx_path}'") # Debugging
            return None

        wb = openpyxl.load_workbook(final_xlsx_path)
        ws = wb.active

        # --- 1. 기본 정보 입력 (모든 열 +1 가정 - Adjust cell refs accordingly) ---
        # Example: B2 becomes C2, I1 becomes J1 etc.
        # I1 -> J1: 이사 종류
        move_type_str = (
            ("보관 " if state_data.get('is_storage_move') else "") +
            ("사무실 " if "사무실" in state_data.get('base_move_type', "") else "") +
            ("장거리 " if state_data.get('apply_long_distance') else "") +
            ("가정" if "가정" in state_data.get('base_move_type', "") else "")
        ).strip() or state_data.get('base_move_type', "") # Fallback if logic fails
        ws['J1'] = move_type_str

        # B2 -> C2: 고객명
        ws['C2'] = state_data.get('customer_name', '')
        # f2 -> G2: 전화번호
        ws['G2'] = state_data.get('customer_phone', '')

        # J2 -> K2: 날짜 (Template might use =TODAY(), so skip setting it)
        # ws['K2'] = ... # Deleted

        # J3 -> K3: 이사일
        moving_date_val = state_data.get('moving_date')
        # Format date if it's a date object
        # *** Check if moving_date_val is an instance of the imported 'date' ***
        if isinstance(moving_date_val, date):
             ws['K3'] = moving_date_val.strftime('%Y-%m-%d')
        elif moving_date_val:
             ws['K3'] = str(moving_date_val) # Use string representation if not date object
        else: ws['K3'] = ''

        # B3 -> C3: 출발지
        ws['C3'] = state_data.get('from_location', '')
        # B4 -> C4: 도착지
        ws['C4'] = state_data.get('to_location', '')
        # K5 -> L5: 작업인원 남
        try: ws['L5'] = int(personnel_info.get('final_men', 0) or 0)
        except (ValueError, TypeError): ws['L5'] = 0
        # K6 -> L6: 작업인원 여
        try: ws['L6'] = int(personnel_info.get('final_women', 0) or 0)
        except (ValueError, TypeError): ws['L6'] = 0
        # c5 -> D5: 출발지 층수 ("층" 포함 if needed)
        from_floor_str = str(state_data.get('from_floor', '')).strip()
        ws['D5'] = f"{from_floor_str}층" if from_floor_str else ''

        # c6 -> D6: 도착지 층수 ("층" 포함 if needed)
        to_floor_str = str(state_data.get('to_floor', '')).strip()
        ws['D6'] = f"{to_floor_str}층" if to_floor_str else '' # Added "층" for consistency

        # D5 -> E5: 출발지 작업방법
        ws['E5'] = state_data.get('from_method', '')
        # D6 -> E6: 도착지 작업방법
        ws['E6'] = state_data.get('to_method', '')
        # A7 -> B7: 선택 차량 (견적 계산 기준 차량)
        selected_vehicle = state_data.get('final_selected_vehicle', '')
        ws['B7'] = selected_vehicle if selected_vehicle else ''

        # *** G7 -> H7: 실제 투입 차량 정보 ***
        dispatched_parts = []
        dispatched_1t = state_data.get('dispatched_1t', 0)
        dispatched_2_5t = state_data.get('dispatched_2_5t', 0)
        dispatched_3_5t = state_data.get('dispatched_3_5t', 0)
        dispatched_5t = state_data.get('dispatched_5t', 0)
        if dispatched_1t > 0: dispatched_parts.append(f"1톤: {dispatched_1t}")
        if dispatched_2_5t > 0: dispatched_parts.append(f"2.5톤: {dispatched_2_5t}")
        if dispatched_3_5t > 0: dispatched_parts.append(f"3.5톤: {dispatched_3_5t}")
        if dispatched_5t > 0: dispatched_parts.append(f"5톤: {dispatched_5t}")
        ws['H7'] = ", ".join(dispatched_parts) if dispatched_parts else '' # H7 셀에 기록


        # --- 2. 비용 정보 입력 (모든 열 +1 가정) ---
        basic_fare = 0; ladder_from = 0; ladder_to = 0; sky_cost=0; storage_cost=0; long_dist_cost=0; waste_cost=0; add_person_cost=0; date_surcharge=0; regional_surcharge=0; adjustment=0

        if calculated_cost_items and isinstance(calculated_cost_items, list):
            for item in calculated_cost_items:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    label, amount_raw = item[0], item[1]
                    try: amount = int(amount_raw)
                    except (ValueError, TypeError): amount = 0

                    # Map cost items to specific variables
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
                    elif "조정" in label: adjustment += amount # Capture both 할증/할인


        # e22 -> F22: 기본운임
        ws['F22'] = basic_fare
        # e23 -> F23: 출발지 작업운임(사다리차/스카이 등)
        ws['F23'] = ladder_from # Or maybe ladder_from + relevant sky_cost? Check template logic
        # e24 -> F24: 도착지 작업운임(사다리차/스카이 등)
        ws['F24'] = ladder_to # Or maybe ladder_to + relevant sky_cost? Check template logic

        # Add other potential costs if template has cells for them (example cells)
        # ws['FXX'] = sky_cost # If separate sky cell
        # ws['FYY'] = storage_cost # If separate storage cell
        # ws['FZZ'] = long_dist_cost # If separate long distance cell
        # ws['FAA'] = waste_cost
        # ws['FBB'] = add_person_cost
        # ws['FCC'] = date_surcharge # Or maybe added to base fare in template?
        # ws['FDD'] = regional_surcharge
        # ws['FEE'] = adjustment # If separate adjustment cell

        # i23 -> J23: 계약금
        try: deposit_amount = int(state_data.get('deposit_amount', 0))
        except (ValueError, TypeError): deposit_amount = 0
        ws['J23'] = deposit_amount

        # e25 -> F25: 총 견적비용
        try: total_cost_num = int(total_cost)
        except (ValueError, TypeError): total_cost_num = 0
        ws['F25'] = total_cost_num

        # I24 -> J24: 잔금
        remaining_balance = total_cost_num - deposit_amount
        ws['J24'] = remaining_balance

        # --- 3. 고객 요구사항 입력 (B26 셀 하나에만 기록) ---
        special_notes_str = state_data.get('special_notes', '')
        # *** 병합된 셀 오류 수정을 위해 B26 셀에만 값을 씀 ***
        ws['B26'] = special_notes_str.strip() if special_notes_str else ''
        # ws['B27'] = '' # Clear other potential cells if they were part of merge
        # ws['B28'] = '' # Clear other potential cells if they were part of merge


        # --- 4. 품목 수량 입력 (모든 열 +1 가정 및 품목 매핑 수정 + 바구니 추가) ---
        # Ensure all item names match data.py exactly
        # Verify cell references (D8, H8 etc.) match the template AFTER shifting columns

        # C -> D 열로 이동
        ws['D8'] = get_item_qty(state_data, '장롱')
        ws['D9'] = get_item_qty(state_data, '더블침대')
        ws['D10'] = get_item_qty(state_data, '서랍장')
        ws['D11'] = get_item_qty(state_data, '서랍장(3단)')
        ws['D12'] = get_item_qty(state_data, '4도어 냉장고')
        ws['D13'] = get_item_qty(state_data, '김치냉장고(일반형)')
        ws['D14'] = get_item_qty(state_data, '김치냉장고(스탠드형)')
        ws['D15'] = get_item_qty(state_data, '소파(3인용)')
        ws['D16'] = get_item_qty(state_data, '소파(1인용)')
        ws['D17'] = get_item_qty(state_data, '식탁(4인)') # Check if this includes chairs
        ws['D18'] = get_item_qty(state_data, '에어컨')
        ws['D19'] = get_item_qty(state_data, '장식장')
        ws['D20'] = get_item_qty(state_data, '피아노(디지털)')
        ws['D21'] = get_item_qty(state_data, '세탁기 및 건조기') # Check if this is combined or separate

        # g -> H 열로 이동
        # ws['H8'] = get_item_qty(state_data, '책바구니') # *** MOVED to H20 ***
        ws['H9'] = get_item_qty(state_data, '사무실책상')
        ws['H10'] = get_item_qty(state_data, '책상&의자') # Check if this is combined
        ws['H11'] = get_item_qty(state_data, '책장')
        # ws['H14'] = 0 # Original comment - cell likely reused or empty
        ws['H15'] = get_item_qty(state_data, '바구니') # Mapped 바구니 to H15
        ws['H16'] = get_item_qty(state_data, '중박스') # Mapped 중박스 to H16
        # Remove or remap H17 if it was a duplicate '중박스'
        # ws['H17'] = get_item_qty(state_data, 'ANOTHER_ITEM') # Example if H17 is for something else
        ws['H19'] = get_item_qty(state_data, '화분')
        ws['H20'] = get_item_qty(state_data, '책바구니') # *** MOVED from H8 ***

        # k -> L 열로 이동
        ws['L8'] = get_item_qty(state_data, '스타일러')
        ws['L9'] = get_item_qty(state_data, '안마기')
        ws['L10'] = get_item_qty(state_data, '피아노(일반)')
        # ws['L11'] = ? # Verify L11 content
        ws['L12'] = get_tv_qty(state_data) # *** MOVED from L19 ***
        # ... check L13-L15 ...
        ws['L16'] = get_item_qty(state_data, '금고')
        ws['L17'] = get_item_qty(state_data, '앵글')
        # ws['L18'] = ? # Verify L18 content
        # ws['L19'] = get_tv_qty(state_data) # *** MOVED to L12 ***

        # --- 5. 완료된 엑셀 파일을 메모리에 저장 ---
        output = io.BytesIO()
        wb.save(output)
        output.seek(0) # Reset buffer position to the beginning
        return output.getvalue() # Return bytes

    except FileNotFoundError:
         st.error(f"Excel 템플릿 파일 '{final_xlsx_path}'을(를) 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
         print(f"Error: Template file not found at '{final_xlsx_path}' during generation.")
         return None
    except Exception as e:
        # *** 오류 메시지에 상세 정보 추가 ***
        st.error(f"Excel 생성 중 오류 발생: {e}")
        print(f"Error during Excel generation: {e}")
        traceback.print_exc() # Print detailed traceback to console/log
        return None
    # No finally block needed as BytesIO handles closing internally
