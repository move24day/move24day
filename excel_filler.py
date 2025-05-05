# excel_filler.py (수정 사항 전체 반영된 예시 파일)

import openpyxl # Excel 처리 라이브러리
import io       # 메모리 내 파일 처리를 위함
import re       # 정규 표현식 (차량 톤수 추출용)
import streamlit as st # 오류 메시지 표시용 (선택적)
# import math # 필요 시 사용

# --- 설정 값 ---

# 실제 템플릿 파일 이름 및 경로 (스크립트와 같은 위치에 있다고 가정)
TEMPLATE_FILE_PATH = 'final.xlsx'

# 실제 템플릿 파일 안에 있는 시트 이름 (따옴표 안에 정확히 입력)
# 이전 'SHEET1' 오류를 바탕으로 'Sheet1'로 가정. 실제와 다르면 수정 필요.
TARGET_SHEET_NAME = 'Sheet1'

# --- 템플릿 채우기 함수 ---

def fill_final_excel_template(state_data, cost_items, total_cost, personnel_info):
    """
    세션 상태 데이터를 기반으로 Final 견적서 Excel 템플릿('final.xlsx')을 채웁니다.
    B7(차량 톤수), D8(장롱 수량 1/3), B26+(고객요구사항 줄바꿈) 수정 포함.

    Args:
        state_data (dict): 현재 세션 상태를 나타내는 딕셔너리.
        cost_items (list): 계산된 비용 항목 리스트.
        total_cost (float): 계산된 총 비용.
        personnel_info (dict): 인원 정보 딕셔너리.

    Returns:
        bytes or None: 생성된 Excel 파일의 바이트 데이터 또는 오류 발생 시 None.
    """
    print(f"INFO [Excel Filler]: Starting Excel generation with template '{TEMPLATE_FILE_PATH}', sheet '{TARGET_SHEET_NAME}'")
    try:
        # --- 1. 템플릿 파일 로드 ---
        try:
            wb = openpyxl.load_workbook(TEMPLATE_FILE_PATH)
            # 지정된 이름의 시트 가져오기
            sheet = wb[TARGET_SHEET_NAME]
            print(f"INFO [Excel Filler]: Template loaded and sheet '{TARGET_SHEET_NAME}' accessed.")
        except FileNotFoundError:
            error_msg = f"엑셀 템플릿 파일을 찾을 수 없습니다: '{TEMPLATE_FILE_PATH}'"
            st.error(error_msg)
            print(f"ERROR [Excel Filler]: {error_msg}")
            return None
        except KeyError:
            error_msg = f"엑셀 템플릿에 '{TARGET_SHEET_NAME}' 시트가 없습니다. 시트 이름을 확인하세요."
            st.error(error_msg)
            print(f"ERROR [Excel Filler]: {error_msg}")
            return None
        except Exception as e:
             error_msg = f"엑셀 템플릿 로드 중 오류 발생: {e}"
             st.error(error_msg)
             print(f"ERROR [Excel Filler]: {error_msg}")
             return None

        # --- 2. (기존 로직) 다른 셀들 채우기 ---
        # !!! 중요: 여기에 기존 템플릿의 다른 셀들(고객명, 날짜, 비용 항목 등)을 채우는 코드를 넣으세요. !!!
        # 예시:
        # sheet['C4'] = state_data.get('customer_name', '') # 고객명 (실제 셀 주소는 템플릿에 맞게)
        # sheet['C5'] = state_data.get('customer_phone', '') # 연락처 (실제 셀 주소는 템플릿에 맞게)
        # ... 비용 항목(cost_items) 및 총 비용(total_cost) 등을 채우는 로직 ...
        print("INFO [Excel Filler]: Placeholder for filling other cells.")


        # --- 3. 요청된 수정 사항 적용 ---

        # 3-1. 차량 톤수 처리 (B7 셀)
        vehicle_str = state_data.get('final_selected_vehicle', '')
        print(f"DEBUG [Excel Filler B7]: Received vehicle_str = '{vehicle_str}', Type = {type(vehicle_str)}")
        vehicle_tonnage = ''
        if isinstance(vehicle_str, str) and vehicle_str.strip():
            try:
                match = re.search(r'(\d+(\.\d+)?)', vehicle_str) # 숫자와 소수점 부분 찾기
                if match:
                    vehicle_tonnage = match.group(1) # 찾은 숫자 부분 사용
                    print(f"DEBUG [Excel Filler B7]: Regex matched, tonnage = '{vehicle_tonnage}'")
                else: # 정규식 실패 시 '톤' 글자 제거 시도
                    print(f"DEBUG [Excel Filler B7]: Regex failed, trying replace method.")
                    vehicle_tonnage_replaced = vehicle_str.replace('톤', '').strip()
                    if re.fullmatch(r'\d+(\.\d+)?', vehicle_tonnage_replaced): # 제거 후 숫자인지 확인
                        vehicle_tonnage = vehicle_tonnage_replaced
                        print(f"DEBUG [Excel Filler B7]: Replace succeeded, tonnage = '{vehicle_tonnage}'")
                    else:
                        print(f"DEBUG [Excel Filler B7]: Replace result '{vehicle_tonnage_replaced}' is not a valid number.")
                        vehicle_tonnage = '' # 유효하지 않으면 빈 값
            except Exception as e:
                print(f"ERROR [Excel Filler B7]: Error processing vehicle_str '{vehicle_str}': {e}")
                vehicle_tonnage = '' # 오류 시 빈 값
        elif vehicle_str: # None 이나 빈 문자열이 아닌 다른 타입 처리 시도
            print(f"Warning [Excel Filler B7]: vehicle_str is not a string: '{vehicle_str}'. Attempting conversion.")
            try: # 문자열 변환 후 로직 재시도
                temp_str = str(vehicle_str)
                match = re.search(r'(\d+(\.\d+)?)', temp_str)
                if match: vehicle_tonnage = match.group(1)
                else:
                    vehicle_tonnage = temp_str.replace('톤', '').strip()
                    if not re.fullmatch(r'\d+(\.\d+)?', vehicle_tonnage): vehicle_tonnage = ''
            except Exception as e:
                print(f"ERROR [Excel Filler B7]: Error converting/processing non-string vehicle_str: {e}")
                vehicle_tonnage = ''

        print(f"DEBUG [Excel Filler B7]: Final vehicle_tonnage to write = '{vehicle_tonnage}'")
        try:
            sheet['B7'] = vehicle_tonnage # B7 셀에 최종 값 쓰기
        except Exception as e:
            print(f"ERROR [Excel Filler B7]: Failed to write tonnage to cell B7: {e}")


        # 3-2. 장롱 수량 처리 (D8 셀)
        current_move_type = state_data.get('base_move_type', '')
        jangrong_formatted_qty = "0.0" # 기본값

        # --- !!! 중요: 아래 키 구성이 실제 state_manager.py 와 data.py 정의와 일치하는지 확인 !!! ---
        # '주요 품목'은 data.py 에서 장롱이 포함된 실제 섹션 이름이어야 합니다.
        wardrobe_section_name = "주요 품목" # 예시: 실제 섹션 이름으로 변경 필요
        jangrong_key = f"qty_{current_move_type}_{wardrobe_section_name}_장롱"
        # --- 확인 필요 끝 ---
        print(f"DEBUG [Excel Filler D8]: Using wardrobe key = '{jangrong_key}'")

        if current_move_type: # 이사 유형이 있어야 키 구성 가능
            original_qty_str = state_data.get(jangrong_key) # state_data에서 값 가져오기
            if original_qty_str is not None: # 키가 존재하면
                try:
                    original_qty = int(original_qty_str) # 정수로 변환
                    calculated_qty = original_qty / 3.0 # 3으로 나누기
                    # 소수점 첫째 자리까지 문자열로 포맷
                    jangrong_formatted_qty = f"{calculated_qty:.1f}"
                    print(f"DEBUG [Excel Filler D8]: Original={original_qty}, Calculated={calculated_qty:.1f}")
                except (ValueError, TypeError): # 변환 실패 시
                    print(f"Warning [Excel Filler D8]: Could not convert qty '{original_qty_str}' for key '{jangrong_key}'.")
                    jangrong_formatted_qty = "0.0" # 오류 시 0.0
            else: # 키가 state_data에 없으면
                print(f"Warning [Excel Filler D8]: Key '{jangrong_key}' not found in state_data.")
        else: # 이사 유형이 없으면
             print(f"Warning [Excel Filler D8]: Cannot determine wardrobe key, current_move_type is empty.")

        print(f"DEBUG [Excel Filler D8]: Final wardrobe qty to write = '{jangrong_formatted_qty}'")
        try:
            sheet['D8'] = jangrong_formatted_qty # D8 셀에 최종 값 쓰기
        except Exception as e:
            print(f"ERROR [Excel Filler D8]: Failed to write wardrobe quantity to cell D8: {e}")


        # 3-3. 고객요구사항 줄바꿈 처리 (B26 셀부터)
        special_notes = state_data.get('special_notes', '')
        start_row_notes = 26 # 쓰기 시작할 행 번호
        print(f"DEBUG [Excel Filler B26+]: Received special_notes = '{special_notes[:50]}...'") # 앞 50자만 출력

        # --- 이전에 작성된 노트 내용 지우기 (선택적이지만 권장) ---
        max_possible_note_lines = 20 # 예시: 최대 20줄 가정 (필요시 조정)
        for i in range(max_possible_note_lines):
             clear_cell_addr = f"B{start_row_notes + i}"
             try:
                 if sheet[clear_cell_addr].value is not None:
                      sheet[clear_cell_addr].value = None # 셀 내용 지우기
             except Exception as e:
                  print(f"Warning [Excel Filler B26+]: Could not clear cell {clear_cell_addr}: {e}")
        # --- 이전 노트 지우기 끝 ---

        if special_notes: # 요구사항이 있는 경우
            # 마침표(.) 기준으로 나누고, 각 부분의 앞뒤 공백 제거, 빈 부분은 제외
            notes_parts = [part.strip() for part in special_notes.split('.') if part.strip()]
            print(f"DEBUG [Excel Filler B26+]: Split into {len(notes_parts)} parts.")

            # 각 부분을 B열의 해당 행에 순차적으로 쓰기
            for i, part in enumerate(notes_parts):
                target_cell_notes = f"B{start_row_notes + i}" # 대상 셀 주소 계산 (B26, B27, ...)
                try:
                    sheet[target_cell_notes] = part # 셀에 쓰기
                    print(f"DEBUG [Excel Filler B26+]: Writing '{part[:30]}...' to {target_cell_notes}")
                except Exception as e:
                    print(f"ERROR [Excel Filler B26+]: Failed to write special note to {target_cell_notes}: {e}")
        else: # 요구사항이 없는 경우
             print(f"DEBUG [Excel Filler B26+]: No special notes to write.")


        # --- 4. 수정된 Workbook을 메모리 버퍼에 저장 ---
        excel_buffer = io.BytesIO() # 메모리 버퍼 생성
        wb.save(excel_buffer)       # 버퍼에 Excel 파일 저장
        excel_buffer.seek(0)        # 버퍼의 포인터를 처음으로 이동
        print("INFO [Excel Filler]: Excel file generated successfully in memory.")
        return excel_buffer.getvalue() # 버퍼의 바이트 데이터를 반환

    # --- 5. 예외 처리 ---
    except Exception as e:
        # 예상치 못한 오류 발생 시 처리
        error_msg = f"Excel 파일 생성 중 예기치 않은 오류 발생: {e}"
        st.error(error_msg) # Streamlit UI에 오류 표시 (선택적)
        import traceback
        traceback.print_exc() # 콘솔에 전체 오류 스택 출력
        print(f"FATAL ERROR [Excel Filler]: Unexpected error during Excel generation: {e}")
        return None

# --- (파일의 끝) ---

# 예시: 이 함수를 테스트하기 위한 간단한 방법 (실제 앱에서는 app.py 등에서 호출됨)
if __name__ == '__main__':
    # 테스트용 가상 데이터 생성
    mock_state_data = {
        'final_selected_vehicle': '5톤 트럭',
        'base_move_type': '가정 이사 🏠',
        'qty_가정 이사 🏠_주요 품목_장롱': '10', # 장롱 키는 실제 키로 맞춰야 함
        'special_notes': '첫번째 요구사항입니다. 두번째 입니다. 세번째. 네번째 문장.'
        # ... 기타 필요한 state_data 값들 ...
    }
    mock_cost_items = []
    mock_total_cost = 0
    mock_personnel_info = {}

    print("--- Running Test ---")
    excel_bytes = fill_final_excel_template(mock_state_data, mock_cost_items, mock_total_cost, mock_personnel_info)

    if excel_bytes:
        # 테스트 결과 파일로 저장해보기 (선택적)
        try:
            with open("test_output.xlsx", "wb") as f:
                f.write(excel_bytes)
            print("--- Test finished. Output saved to test_output.xlsx ---")
        except Exception as write_e:
            print(f"--- Test finished. Could not save output file: {write_e} ---")
    else:
        print("--- Test failed. No Excel data generated. ---")
