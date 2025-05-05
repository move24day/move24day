# excel_filler.py (사용자 제공 기준 코드 + 고객 요구사항 줄바꿈 처리 적용)

import openpyxl
import io
import streamlit as st
import os
import traceback # 상세 오류 출력을 위해 추가
from datetime import date # 날짜 타입 비교를 위해 date 임포트
import re # 차량 톤수 처리를 위해 필요할 수 있으므로 추가 (현재는 사용 안 함)

try:
    # data.py 파일 임포트 시도 (App.py와 같은 위치에 있어야 함)
    import data # data.py 필요
except ImportError:
    # data.py 로드 실패 시 사용자에게 알리고 None으로 설정
    st.error("data.py 파일을 찾을 수 없습니다. excel_filler.py와 같은 폴더에 있는지 확인하세요.")
    data = None # data 모듈이 없음을 표시

# --- 헬퍼 함수 정의 (사용자 제공 기준 코드) ---
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
    (고객 요구사항 B26+ 줄바꿈 처리 적용됨)
    """
    if not data:
        st.error("data.py 모듈 로드 실패로 Excel 생성을 진행할 수 없습니다.")
        return None

    try:
        # final.xlsx 경로 설정 (스크립트와 같은 디렉토리 가정)
        script_dir = os.path.dirname(__file__) if "__file__" in locals() else "."
        final_xlsx_path = os.path.join(script_dir, "final.xlsx") # 파일 이름 사용

        if not os.path.exists(final_xlsx_path):
            st.error(f"템플릿 파일 '{final_xlsx_path}'을 찾을 수 없습니다.")
            print(f"Error: Template file not found at '{final_xlsx_path}'")
            return None

        wb = openpyxl.load_workbook(final_xlsx_path)
        ws = wb.active # 활성 시트 사용 (템플릿에 시트가 하나만 있거나, 활성 시트에 작업하는 경우)
                      # 특정 시트 이름 사용 시: ws = wb['Sheet1'] 등으로 변경

        print(f"INFO [Excel Filler]: Template '{final_xlsx_path}' loaded, using active sheet.")

        # --- 1. 기본 정보 입력 (사용자 제공 기준 코드 - 셀 주소 확인 필요) ---
        # 주석: 아래 셀 주소들은 사용자의 기준 코드에 명시된 것을 따릅니다.
        #       실제 final.xlsx 템플릿과 일치하는지 확인이 필요합니다.
        # I1 -> J1: 이사 종류
        move_type_str = (
            ("보관 " if state_data.get('is_storage_move') else "") +
            ("사무실 " if "사무실" in state_data.get('base_move_type', "") else "") +
            ("장거리 " if state_data.get('apply_long_distance') else "") +
            ("가정" if "가정" in state_data.get('base_move_type', "") else "")
        ).strip() or state_data.get('base_move_type', "")
        ws['J1'] = move_type_str

        # B2 -> C2: 고객명
        ws['C2'] = state_data.get('customer_name', '')
        # f2 -> G2: 전화번호
        ws['G2'] = state_data.get('customer_phone', '')

        # J2 -> K2: 날짜 (템플릿 수식 사용 가정 - 주석 처리됨)
        # ws['K2'] = ...

        # J3 -> K3: 이사일
        moving_date_val = state_data.get('moving_date')
        if isinstance(moving_date_val, date): # datetime.date 객체인지 확인
             ws['K3'] = moving_date_val # 날짜 객체 그대로 넣으면 Excel에서 날짜로 인식
             ws['K3'].number_format = 'yyyy-mm-dd' # 날짜 형식 지정 (선택적)
        elif moving_date_val:
             ws['K3'] = str(moving_date_val) # 다른 타입이면 문자열로
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
        # c5 -> D5: 출발지 층수
        from_floor_str = str(state_data.get('from_floor', '')).strip()
        ws['D5'] = f"{from_floor_str}층" if from_floor_str else ''
        # c6 -> D6: 도착지 층수
        to_floor_str = str(state_data.get('to_floor', '')).strip()
        ws['D6'] = f"{to_floor_str}층" if to_floor_str else ''
        # D5 -> E5: 출발지 작업방법
        ws['E5'] = state_data.get('from_method', '')
        # D6 -> E6: 도착지 작업방법
        ws['E6'] = state_data.get('to_method', '')
        # A7 -> B7: 선택 차량 (견적 계산 기준 차량) - '톤' 포함된 원본 저장
        selected_vehicle = state_data.get('final_selected_vehicle', '')
        ws['B7'] = selected_vehicle if selected_vehicle else ''

        # G7 -> H7: 실제 투입 차량 정보
        dispatched_parts = []
        dispatched_1t = state_data.get('dispatched_1t', 0)
        dispatched_2_5t = state_data.get('dispatched_2_5t', 0)
        dispatched_3_5t = state_data.get('dispatched_3_5t', 0)
        dispatched_5t = state_data.get('dispatched_5t', 0)
        # Try converting to int, default to 0 on error
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


        # --- 2. 비용 정보 입력 (사용자 제공 기준 코드 - 셀 주소 확인 필요) ---
        basic_fare = 0; ladder_from = 0; ladder_to = 0; sky_cost=0; storage_cost=0; long_dist_cost=0; waste_cost=0; add_person_cost=0; date_surcharge=0; regional_surcharge=0; adjustment=0

        if calculated_cost_items and isinstance(calculated_cost_items, list):
            for item in calculated_cost_items:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    label, amount_raw = item[0], item[1]
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
                    # 조정 금액 처리: 할증(+)과 할인(-) 모두 반영하도록 '+' 사용
                    elif "조정" in label: adjustment += amount # Note: adjustment starts at 0

        # 비용 항목 셀에 기록 (셀 주소는 기준 코드 따름)
        ws['F22'] = basic_fare
        ws['F23'] = ladder_from # 출발지 작업 (사다리)
        ws['F24'] = ladder_to # 도착지 작업 (사다리)
        # 참고: 스카이 비용 등 다른 비용 항목도 템플릿에 셀이 있다면 여기에 추가
        # 예: ws['FXX'] = sky_cost
        # 예: ws['FYY'] = adjustment # 조정 금액 (+/-)

        # 계약금, 총비용, 잔금
        try: deposit_amount = int(state_data.get('deposit_amount', 0))
        except (ValueError, TypeError): deposit_amount = 0
        ws['J23'] = deposit_amount

        try: total_cost_num = int(total_cost)
        except (ValueError, TypeError): total_cost_num = 0
        ws['F25'] = total_cost_num # 총 견적 비용

        remaining_balance = total_cost_num - deposit_amount
        ws['J24'] = remaining_balance # 잔금


        # --- 3. 고객 요구사항 입력 (B26 셀부터 순차적으로 기록 - 수정됨) ---
        # !!! 경고: B26 셀이 Excel 템플릿('final.xlsx')에서 여러 행(B27, B28 등)에 걸쳐 병합되어 있다면, !!!
        # !!! 아래 로직은 예상대로 동작하지 않을 수 있습니다. 병합된 경우 B26에만 텍스트가 보이거나,      !!!
        # !!! openpyxl 라이브러리 버전에 따라 오류가 발생할 수 있습니다.                       !!!
        # !!! 만약 B26 셀이 병합되어 있다면, 템플릿에서 병합을 해제하거나,                     !!!
        # !!! 아래 로직 대신 원래 코드처럼 B26 하나에만 전체 내용을 쓰는 것을 고려해야 합니다.        !!!
        special_notes_str = state_data.get('special_notes', '')
        start_row_notes = 26 # 쓰기 시작할 행 번호
        print(f"DEBUG [Excel Filler B26+]: Received special_notes = '{special_notes_str[:50]}...'") # 디버깅: 앞 50자 출력

        # --- 이전에 작성된 노트 내용 지우기 (선택적이지만 권장) ---
        max_possible_note_lines = 20 # 예시: 최대 20줄 가정 (템플릿에 맞춰 조정 필요)
        for i in range(max_possible_note_lines):
             clear_cell_addr = f"B{start_row_notes + i}"
             try:
                 # 해당 셀에 값이 있을 경우에만 None으로 설정하여 지웁니다.
                 if ws[clear_cell_addr].value is not None:
                      ws[clear_cell_addr].value = None # 셀 내용 지우기
             except Exception as e:
                  print(f"Warning [Excel Filler B26+]: Could not clear cell {clear_cell_addr}: {e}")
        # --- 이전 노트 지우기 끝 ---

        if special_notes_str: # 요구사항 문자열이 있는 경우
            # 마침표(.) 기준으로 나누고, 각 부분의 앞뒤 공백 제거, 빈 부분은 제외
            notes_parts = [part.strip() for part in special_notes_str.split('.') if part.strip()]
            print(f"DEBUG [Excel Filler B26+]: Split into {len(notes_parts)} parts.")

            # 각 부분을 B열의 해당 행에 순차적으로 쓰기
            for i, part in enumerate(notes_parts):
                target_cell_notes = f"B{start_row_notes + i}" # 대상 셀 주소 계산 (B26, B27, ...)
                try:
                    ws[target_cell_notes] = part # 셀에 쓰기
                    print(f"DEBUG [Excel Filler B26+]: Writing '{part[:30]}...' to {target_cell_notes}")
                except Exception as e:
                    print(f"ERROR [Excel Filler B26+]: Failed to write special note to {target_cell_notes}: {e}")
        else: # 요구사항 문자열이 없는 경우
             print(f"DEBUG [Excel Filler B26+]: No special notes to write.")
             # 요구사항이 없을 때 B26 셀을 비우는 로직 (선택적)
             try:
                 if ws['B26'].value is not None: ws['B26'] = None
             except Exception as e:
                 print(f"Warning [Excel Filler B26+]: Could not clear B26 for empty notes: {e}")


        # --- 4. 품목 수량 입력 (사용자 제공 기준 코드 - 셀 주소 확인 필요) ---
        # 주석: 아래 셀 주소 및 품목명 매핑은 기준 코드 따름. 실제 템플릿과 data.py 확인 필요.
        # D열 (기존 C열)
        ws['D8'] = get_item_qty(state_data, '장롱') # 아직 1/3 계산 미적용
        ws['D9'] = get_item_qty(state_data, '더블침대')
        ws['D10'] = get_item_qty(state_data, '서랍장')
        ws['D11'] = get_item_qty(state_data, '서랍장(3단)')
        ws['D12'] = get_item_qty(state_data, '4도어 냉장고')
        ws['D13'] = get_item_qty(state_data, '김치냉장고(일반형)')
        ws['D14'] = get_item_qty(state_data, '김치냉장고(스탠드형)')
        ws['D15'] = get_item_qty(state_data, '소파(3인용)')
        ws['D16'] = get_item_qty(state_data, '소파(1인용)')
        ws['D17'] = get_item_qty(state_data, '식탁(4인)')
        ws['D18'] = get_item_qty(state_data, '에어컨')
        ws['D19'] = get_item_qty(state_data, '장식장')
        ws['D20'] = get_item_qty(state_data, '피아노(디지털)')
        ws['D21'] = get_item_qty(state_data, '세탁기 및 건조기')

        # H열 (기존 G열)
        ws['H9'] = get_item_qty(state_data, '사무실책상')
        ws['H10'] = get_item_qty(state_data, '책상&의자')
        ws['H11'] = get_item_qty(state_data, '책장')
        ws['H15'] = get_item_qty(state_data, '바구니')
        ws['H16'] = get_item_qty(state_data, '중박스') # 기준 코드에 '중박스'가 있었는지 확인 필요
        ws['H19'] = get_item_qty(state_data, '화분')
        ws['H20'] = get_item_qty(state_data, '책바구니')

        # L열 (기존 K열)
        ws['L8'] = get_item_qty(state_data, '스타일러')
        ws['L9'] = get_item_qty(state_data, '안마기')
        ws['L10'] = get_item_qty(state_data, '피아노(일반)')
        ws['L12'] = get_tv_qty(state_data) # 모든 TV 합산 수량
        ws['L16'] = get_item_qty(state_data, '금고')
        ws['L17'] = get_item_qty(state_data, '앵글')

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
