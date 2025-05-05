# pdf_generator.py (기본 운임 비고 수정 + 고객 요구사항 줄바꿈 처리 적용)

import pandas as pd
import io
import streamlit as st
import traceback
import utils # utils.py 필요
import data # data.py 필요
import os
from datetime import date

# --- ReportLab 관련 모듈 임포트 ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer # Spacer는 현재 사용되지 않음
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- 회사 정보 상수 정의 ---
COMPANY_ADDRESS = "서울 은평구 가좌로10길 33-1"
COMPANY_PHONE_1 = "010-5047-1111"
COMPANY_PHONE_2 = "1577-3101"
COMPANY_EMAIL = "move24day@gmail.com"

# --- 폰트 경로 설정 ---
# Streamlit 앱 실행 위치 기준으로 폰트 파일 경로 지정
# 예: 앱 루트에 폰트 파일이 있는 경우
NANUM_GOTHIC_FONT_PATH = "NanumGothic.ttf"
# 예: 'fonts' 폴더 안에 있는 경우
# NANUM_GOTHIC_FONT_PATH = "fonts/NanumGothic.ttf"

# --- PDF 생성 함수 ---
def generate_pdf(state_data, calculated_cost_items, total_cost, personnel_info):
    """주어진 데이터를 기반으로 견적서 PDF를 생성합니다."""
    buffer = io.BytesIO()
    try:
        # --- 폰트 파일 확인 및 등록 ---
        if not os.path.exists(NANUM_GOTHIC_FONT_PATH):
            st.error(f"PDF 생성 오류: 폰트 파일 '{NANUM_GOTHIC_FONT_PATH}'을(를) 찾을 수 없습니다. 앱 실행 경로를 확인하세요.")
            print(f"ERROR: Font file not found at '{NANUM_GOTHIC_FONT_PATH}'")
            return None
        try:
            pdfmetrics.registerFont(TTFont('NanumGothic', NANUM_GOTHIC_FONT_PATH))
            # Bold 폰트도 동일한 파일로 등록 (ReportLab에서 스타일로 굵게 처리 가능)
            pdfmetrics.registerFont(TTFont('NanumGothicBold', NANUM_GOTHIC_FONT_PATH))
            print("DEBUG: NanumGothic font registered successfully.")
        except Exception as font_e:
            st.error(f"PDF 생성 오류: 폰트 로딩 실패 ('{NANUM_GOTHIC_FONT_PATH}'). 상세: {font_e}")
            print(f"ERROR: Failed to load font '{NANUM_GOTHIC_FONT_PATH}': {font_e}")
            return None

        # --- Canvas 및 기본 설정 ---
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin_x = 1.5*cm
        margin_y = 1.5*cm
        line_height = 0.6*cm # 기본 줄 간격
        right_margin_x = width - margin_x
        page_number = 1

        # --- 페이지 템플릿 (상단 회사 정보) ---
        def draw_page_template(canvas_obj, page_num):
            canvas_obj.saveState()
            canvas_obj.setFont('NanumGothic', 7)
            company_info_line_height = 0.35 * cm
            company_info_y = height - margin_y
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"주소: {COMPANY_ADDRESS}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"전화: {COMPANY_PHONE_1} | {COMPANY_PHONE_2}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"이메일: {COMPANY_EMAIL}")
            # 페이지 번호 추가 (선택적)
            # canvas_obj.drawCentredString(width / 2.0, margin_y / 2, f"- {page_num} -")
            canvas_obj.restoreState()

        # --- 초기 페이지 그리기 및 제목 ---
        current_y = height - margin_y - 1*cm # 상단 여백 후 시작 Y 위치
        draw_page_template(c, page_number)
        c.setFont('NanumGothicBold', 18) # 제목 폰트
        c.drawCentredString(width / 2.0, current_y, "이삿날 견적서(계약서)")
        current_y -= line_height * 2 # 제목 아래 여백

        # --- 안내 문구 ---
        styles = getSampleStyleSheet()
        # 중앙 정렬 스타일 정의 (Paragraph용)
        center_style = ParagraphStyle(name='CenterStyle', fontName='NanumGothic', fontSize=10, leading=14, alignment=TA_CENTER)
        service_text = """고객님의 이사를 안전하고 신속하게 책임지는 이삿날입니다."""
        p_service = Paragraph(service_text, center_style)
        p_service_width, p_service_height = p_service.wrapOn(c, width - margin_x*2, 5*cm) # 너비 제한, 높이 자동 계산
        # 페이지에 공간이 부족하면 새 페이지 시작
        if current_y - p_service_height < margin_y:
            c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
        p_service.drawOn(c, margin_x, current_y - p_service_height); # Paragraph 그리기
        current_y -= (p_service_height + line_height) # 그린 높이만큼 Y 위치 이동

        # --- 기본 정보 그리기 ---
        c.setFont('NanumGothic', 11) # 기본 정보 폰트
        is_storage = state_data.get('is_storage_move')
        info_pairs = [
            ("고 객 명:", state_data.get('customer_name', '-')), ("연 락 처:", state_data.get('customer_phone', '-')),
            ("이 사 일:", str(state_data.get('moving_date', '-'))), ("견 적 일:", utils.get_current_kst_time_str("%Y-%m-%d")), # 날짜만 표시
            ("출 발 지:", state_data.get('from_location', '-')), ("도 착 지:", state_data.get('to_location', '-'))
        ]
        if is_storage:
            info_pairs.append(("보관 기간:", f"{state_data.get('storage_duration', 1)} 일"))
            # data 모듈 확인 후 기본값 사용
            default_storage = data.DEFAULT_STORAGE_TYPE if data and hasattr(data, 'DEFAULT_STORAGE_TYPE') else "-"
            info_pairs.append(("보관 유형:", state_data.get('storage_type', default_storage)))

        # 인원 정보 처리 (personnel_info가 없을 경우 대비)
        p_info = personnel_info if isinstance(personnel_info, dict) else {}
        final_men = p_info.get('final_men', 0)
        final_women = p_info.get('final_women', 0)
        personnel_text = f"남성 {final_men}명" + (f", 여성 {final_women}명" if final_women > 0 else "")
        info_pairs.append(("작업 인원:", personnel_text))
        info_pairs.append(("선택 차량:", state_data.get('final_selected_vehicle', '미선택')))

        # 정보 테이블 그리기 (Paragraph 사용하여 긴 주소 자동 줄바꿈)
        value_style = ParagraphStyle(name='InfoValueStyle', fontName='NanumGothic', fontSize=11, leading=13)
        label_width = 3 * cm # 라벨 너비
        value_x = margin_x + label_width # 값 시작 X 위치
        value_max_width = width - value_x - margin_x # 값 최대 너비

        for label, value in info_pairs:
            # 값을 Paragraph로 만들어 높이 계산
            value_para = Paragraph(str(value), value_style)
            value_para_width, value_para_height = value_para.wrapOn(c, value_max_width, line_height * 3) # 최대 3줄 가정
            row_height = max(line_height, value_para_height + 0.1*cm) # 라벨 높이와 값 높이 중 큰 값 사용

            # 페이지 남은 공간 확인 및 페이지 넘김
            if current_y - row_height < margin_y:
                c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
                c.setFont('NanumGothic', 11) # 폰트 리셋

            # 라벨과 값 그리기 (수직 중앙 정렬 비슷하게)
            c.drawString(margin_x, current_y - (row_height + 11)/2 + 6, label) # 라벨 위치 조정
            value_para.drawOn(c, value_x, current_y - value_para_height - (row_height - value_para_height)/2 + 2) # 값 Paragraph 그리기
            current_y -= row_height # 다음 행으로 Y 위치 이동

        current_y -= line_height * 0.5 # 정보 섹션 아래 여백

        # --- 비용 상세 내역 ---
        cost_start_y = current_y
        # 비용 섹션 시작 전 페이지 여유 공간 확인
        if cost_start_y < margin_y + 5*cm : # 최소 5cm 정도 여유 없으면 페이지 넘김
            c.showPage(); page_number += 1; draw_page_template(c, page_number); cost_start_y = height - margin_y - 1*cm
            c.setFont('NanumGothic', 11) # 폰트 리셋

        current_y = cost_start_y
        c.setFont('NanumGothicBold', 12); c.drawString(margin_x, current_y, "[ 비용 상세 내역 ]"); current_y -= line_height * 1.2
        # 비용 테이블 헤더
        c.setFont('NanumGothicBold', 10); cost_col1_x = margin_x; cost_col2_x = margin_x + 8*cm; cost_col3_x = margin_x + 11*cm
        c.drawString(cost_col1_x, current_y, "항목"); c.drawRightString(cost_col2_x + 2*cm, current_y, "금액"); c.drawString(cost_col3_x, current_y, "비고")
        c.setFont('NanumGothic', 10); current_y -= 0.2*cm; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height * 0.8

        # --- 비용 항목 처리 (날짜 할증 병합 및 기본 운임 비고 수정 적용) ---
        cost_items_processed = []
        date_surcharge_amount = 0
        date_surcharge_notes = "" # 사용되지 않지만 로직상 남겨둠
        date_surcharge_index = -1

        # calculated_cost_items가 유효한 리스트인지 확인
        temp_items = []
        if calculated_cost_items and isinstance(calculated_cost_items, list):
             # 오류 항목 제외하고 복사
             temp_items = [list(item) for item in calculated_cost_items if isinstance(item, (list, tuple)) and len(item) >= 2 and "오류" not in str(item[0])]

        # 날짜 할증 찾기
        for i, item in enumerate(temp_items):
             if str(item[0]) == "날짜 할증":
                 try: date_surcharge_amount = int(item[1])
                 except: date_surcharge_amount = 0
                 # 상세 노트는 더 이상 필요 없음
                 # if len(item) > 2: date_surcharge_notes = str(item[2])
                 date_surcharge_index = i
                 break

        # 기본 운임 찾기 및 날짜 할증 병합 (비고 수정 포함)
        base_fare_index = -1
        for i, item in enumerate(temp_items):
              if str(item[0]) == "기본 운임":
                 base_fare_index = i
                 if date_surcharge_index != -1 and date_surcharge_amount > 0: # 날짜 할증이 있었으면
                     try:
                         original_base_fare = int(item[1])
                         item[1] = original_base_fare + date_surcharge_amount # 금액 합산
                         # --- !!! 수정된 비고 생성 로직 !!! ---
                         item[2] = "이사 집중일 추가 운영 요금" # 고정 문구로 설정
                         # --- !!! 수정 완료 !!! ---
                     except Exception as e:
                          print(f"Error merging date surcharge into base fare: {e}")
                 # else: 날짜 할증 없을 시 기본 운임 비고는 변경 안 함
                 break # 기본 운임 찾음

        # 처리된 날짜 할증 항목 제거 (만약 찾았다면)
        if date_surcharge_index != -1:
              try:
                   del temp_items[date_surcharge_index]
              except IndexError:
                   print(f"Warning: Could not remove date surcharge item at index {date_surcharge_index}")


        # 최종 그릴 항목 리스트 생성 (처리된 temp_items 사용)
        for item_desc, item_cost, *item_note_tuple in temp_items:
             item_note = item_note_tuple[0] if item_note_tuple else ""
             try: item_cost_int = int(item_cost) # 금액은 정수로
             except: item_cost_int = 0
             cost_items_processed.append((str(item_desc), item_cost_int, str(item_note)))
        # --- 비용 항목 처리 끝 ---

        # --- 비용 테이블 그리기 ---
        if cost_items_processed:
            # 스타일 정의
            styleDesc = ParagraphStyle(name='CostDesc', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)
            styleCost = ParagraphStyle(name='CostAmount', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_RIGHT)
            styleNote = ParagraphStyle(name='CostNote', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)

            for item_desc, item_cost, item_note in cost_items_processed:
                cost_str = f"{item_cost:,.0f} 원" if item_cost is not None else "0 원"
                note_str = item_note if item_note else ""

                # Paragraph 객체 생성
                p_desc = Paragraph(item_desc, styleDesc)
                p_cost = Paragraph(cost_str, styleCost)
                p_note = Paragraph(note_str, styleNote)

                # 각 컬럼 너비 및 높이 계산
                desc_width = cost_col2_x - cost_col1_x - 0.5*cm
                cost_width = (cost_col3_x - cost_col2_x) + 1.5*cm # 금액 오른쪽 정렬 위해 약간 넓게
                note_width = right_margin_x - cost_col3_x
                desc_height = p_desc.wrap(desc_width, 1000)[1]
                cost_height = p_cost.wrap(cost_width, 1000)[1]
                note_height = p_note.wrap(note_width, 1000)[1]
                max_row_height = max(desc_height, cost_height, note_height, line_height * 0.8) # 행 높이 결정

                # 페이지 넘김 확인
                if current_y - max_row_height < margin_y:
                    c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
                    # 페이지 넘김 후 헤더 다시 그리기
                    c.setFont('NanumGothicBold', 10); c.drawString(cost_col1_x, current_y, "항목"); c.drawRightString(cost_col2_x + 2*cm, current_y, "금액"); c.drawString(cost_col3_x, current_y, "비고")
                    current_y -= 0.2*cm; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height * 0.8; c.setFont('NanumGothic', 10)

                # Paragraph 그리기 (Y 위치 조정하여 하단 정렬 효과)
                y_draw_base = current_y - max_row_height
                p_desc.drawOn(c, cost_col1_x, y_draw_base + (max_row_height - desc_height))
                p_cost.drawOn(c, cost_col2_x + 2*cm - cost_width, y_draw_base + (max_row_height - cost_height)) # 오른쪽 정렬 위해 X 위치 조정
                p_note.drawOn(c, cost_col3_x, y_draw_base + (max_row_height - note_height))
                current_y -= (max_row_height + 0.2*cm) # 다음 항목을 위한 Y 위치 이동 (간격 포함)
        else:
            # 비용 항목 없을 때 메시지
            if current_y < margin_y + 3*cm : c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
            c.drawString(cost_col1_x, current_y, "계산된 비용 내역이 없습니다."); current_y -= line_height

        # --- 비용 요약 ---
        summary_start_y = current_y
        if summary_start_y < margin_y + line_height * 5: # 요약 그릴 공간 확인
            c.showPage(); page_number += 1; draw_page_template(c, page_number); summary_start_y = height - margin_y - 1*cm
            c.setFont('NanumGothic', 11) # 폰트 리셋

        current_y = summary_start_y
        c.line(cost_col1_x, current_y, right_margin_x, current_y) # 구분선
        current_y -= line_height

        # 값 계산 (오류 방지)
        total_cost_num = int(total_cost) if isinstance(total_cost, (int, float)) else 0
        deposit_amount = state_data.get('deposit_amount', 0);
        try: deposit_amount = int(deposit_amount)
        except (ValueError, TypeError): deposit_amount = 0
        remaining_balance = total_cost_num - deposit_amount

        # 요약 항목 그리기
        c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "총 견적 비용 (VAT 별도)")
        total_cost_str = f"{total_cost_num:,.0f} 원"
        c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, total_cost_str); current_y -= line_height

        c.setFont('NanumGothic', 11); c.drawString(cost_col1_x, current_y, "계약금 (-)")
        deposit_str = f"{deposit_amount:,.0f} 원"
        c.setFont('NanumGothic', 12); c.drawRightString(right_margin_x, current_y, deposit_str); current_y -= line_height

        c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "잔금 (VAT 별도)")
        remaining_str = f"{remaining_balance:,.0f} 원"
        c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, remaining_str); current_y -= line_height

        # --- 고객요구사항 그리기 (수정됨: '.' 기준으로 줄바꿈 처리) ---
        special_notes = state_data.get('special_notes', '').strip()
        if special_notes:
            notes_section_start_y = current_y # 섹션 시작 Y 위치 기억

            # 섹션 제목 그리기 전 페이지 여유 공간 확인
            if notes_section_start_y < margin_y + line_height * 3:
                c.showPage(); page_number += 1; draw_page_template(c, page_number)
                current_y = height - margin_y - 1*cm # Y 위치 초기화
                notes_section_start_y = current_y
                c.setFont('NanumGothic', 11) # 폰트 리셋
            else:
                 current_y -= line_height # 제목을 위한 공간 확보

            # 섹션 제목 그리기
            c.setFont('NanumGothicBold', 11)
            c.drawString(margin_x, current_y, "[ 고객요구사항 ]")
            current_y -= line_height * 1.2 # 제목 아래 여백

            # 노트 각 줄 스타일 및 가용 너비 설정
            styleNotes = ParagraphStyle(name='NotesParagraph', fontName='NanumGothic', fontSize=10, leading=12, alignment=TA_LEFT)
            available_width = width - margin_x * 2

            # '.' 기준으로 노트 분리 및 빈 항목 제거
            notes_parts = [part.strip() for part in special_notes.split('.') if part.strip()]

            # 각 노트 조각을 별도의 Paragraph로 그리기
            for note_part in notes_parts:
                p_part = Paragraph(note_part.replace('\n', '<br/>'), styleNotes) # 내부 줄바꿈 처리
                part_width, part_height = p_part.wrapOn(c, available_width, 1000) # 높이 계산

                # 현재 페이지에 그릴 공간이 없으면 페이지 넘김
                if current_y - part_height < margin_y:
                    c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
                    c.setFont('NanumGothic', 11) # 폰트 리셋

                # Paragraph 그리기
                p_part.drawOn(c, margin_x, current_y - part_height)
                # 다음 Paragraph를 위해 Y 위치 업데이트 (약간의 간격 추가)
                current_y -= (part_height + line_height * 0.2) # 줄 간격 조절 가능

        # --- 고객 요구사항 섹션 끝 ---

        # --- 최종 저장 및 반환 ---
        c.save() # Canvas 내용을 buffer에 저장
        buffer.seek(0) # buffer의 읽기 위치를 처음으로 이동
        return buffer.getvalue() # buffer의 내용을 바이트로 반환

    except Exception as e:
        st.error(f"PDF 생성 중 예외 발생: {e}")
        print(f"Error during PDF generation: {e}")
        traceback.print_exc() # 콘솔에 상세 오류 출력
        return None
    # finally 블록 불필요 (BytesIO는 close 불필요)

# --- 엑셀 생성 함수 (generate_excel) ---
# 이 함수는 변경되지 않았으므로 기존 코드를 그대로 사용합니다.
def generate_excel(state_data, calculated_cost_items, total_cost, personnel_info):
    # ... (이전 버전의 generate_excel 코드 전체 내용 - 변경 없음) ...
    output = io.BytesIO()
    try:
        is_storage = state_data.get('is_storage_move', False); is_long_distance = state_data.get('apply_long_distance', False); is_waste = state_data.get('has_waste_check', False)
        from_method = state_data.get('from_method', '-'); to_method = state_data.get('to_method', '-'); to_floor = state_data.get('to_floor', '-'); use_sky_from = (from_method == "스카이 🏗️"); use_sky_to = (to_method == "스카이 🏗️")
        p_info = personnel_info if isinstance(personnel_info, dict) else {}; final_men = p_info.get('final_men', 0); final_women = p_info.get('final_women', 0); personnel_text = f"남성 {final_men}명" + (f", 여성 {final_women}명" if final_women > 0 else "")
        dest_address = state_data.get('to_location', '-');

        # 1. '견적 정보' 시트
        ALL_INFO_LABELS = ["회사명", "주소", "연락처", "이메일", "", "고객명", "고객 연락처", "견적일", "이사 종류", "", "이사일", "출발지", "도착지", "출발층", "도착층", "출발 작업", "도착 작업", "", "보관 이사", "보관 기간", "보관 유형", "", "장거리 적용", "장거리 구간", "", "스카이 사용 시간", "", "폐기물 처리(톤)", "", "날짜 할증 선택", "", "총 작업 인원", "", "선택 차량", "자동 추천 차량", "이사짐 총 부피", "이사짐 총 무게", "", "고객요구사항"]
        info_data_list = []
        for label in ALL_INFO_LABELS:
            value = '-'
            if not label: info_data_list.append(("", "")); continue
            if label == "회사명": value = "(주)이사데이"
            elif label == "주소": value = COMPANY_ADDRESS
            elif label == "연락처": value = f"{COMPANY_PHONE_1} | {COMPANY_PHONE_2}"
            elif label == "이메일": value = COMPANY_EMAIL
            elif label == "고객명": value = state_data.get('customer_name', '-')
            elif label == "고객 연락처": value = state_data.get('customer_phone', '-')
            elif label == "견적일": value = utils.get_current_kst_time_str("%Y-%m-%d")
            elif label == "이사 종류": value = state_data.get('base_move_type', '-')
            elif label == "이사일": value = str(state_data.get('moving_date', '-'))
            elif label == "출발지": value = state_data.get('from_location', '-')
            elif label == "도착지": value = dest_address
            elif label == "출발층": value = state_data.get('from_floor', '-')
            elif label == "도착층": value = to_floor
            elif label == "출발 작업": value = from_method
            elif label == "도착 작업": value = to_method
            elif label == "보관 이사": value = '예' if is_storage else '아니오'
            elif label == "보관 기간":
                duration = state_data.get('storage_duration', '-')
                value = f"{duration} 일" if is_storage and duration != '-' else '-'
            elif label == "보관 유형": value = state_data.get('storage_type', '-') if is_storage else '-'
            elif label == "장거리 적용": value = '예' if is_long_distance else '아니오'
            elif label == "장거리 구간": value = state_data.get('long_distance_selector', '-') if is_long_distance else '-'
            elif label == "스카이 사용 시간":
                sky_details = []
                if use_sky_from: sky_details.append(f"출발지 {state_data.get('sky_hours_from', 1)}시간")
                if use_sky_to: sky_details.append(f"도착지 {state_data.get('sky_hours_final', 1)}시간")
                value = ", ".join(sky_details) if sky_details else '-'
            elif label == "폐기물 처리(톤)": value = f"예 ({state_data.get('waste_tons_input', 0.5):.1f} 톤)" if is_waste else '아니오'
            elif label == "날짜 할증 선택":
                date_options_list = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]; date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options_list))]
                selected_dates_excel = [date_options_list[i] for i, key in enumerate(date_keys) if state_data.get(key, False)]; value = ", ".join(selected_dates_excel) if selected_dates_excel else '없음'
            elif label == "총 작업 인원": value = personnel_text
            elif label == "선택 차량": value = state_data.get('final_selected_vehicle', '미선택')
            elif label == "자동 추천 차량": value = state_data.get('recommended_vehicle_auto', '-')
            elif label == "이사짐 총 부피": value = f"{state_data.get('total_volume', 0.0):.2f} m³"
            elif label == "이사짐 총 무게": value = f"{state_data.get('total_weight', 0.0):.2f} kg"
            elif label == "고객요구사항": value = state_data.get('special_notes', '').strip() or '-'
            info_data_list.append((label, value))
        df_info = pd.DataFrame(info_data_list, columns=["항목", "내용"])

        # 2. '전체 품목 수량' 시트
        all_items_data = []; current_move_type = state_data.get('base_move_type', list(data.item_definitions.keys())[0] if data and hasattr(data,'item_definitions') and data.item_definitions else ''); item_defs = data.item_definitions.get(current_move_type, {}); processed_all_items = set()
        if isinstance(item_defs, dict):
            for section, item_list in item_defs.items():
                if section == "폐기 처리 품목 🗑️": continue
                if isinstance(item_list, list):
                    # Use helper function to get quantity robustly
                    for item_name in item_list:
                         if item_name in processed_all_items: continue
                         # Ensure item exists in data.items for validation (optional but good)
                         if data and hasattr(data, 'items') and item_name in data.items:
                              qty = utils.get_item_qty(state_data, item_name) # Use helper if utils has it, or the one defined in excel_filler
                              # qty = get_item_qty(state_data, item_name) # If using helper defined above in pdf_generator
                              all_items_data.append({"품목명": item_name, "수량": qty}); processed_all_items.add(item_name)
        if all_items_data: df_all_items = pd.DataFrame(all_items_data, columns=["품목명", "수량"])
        else: df_all_items = pd.DataFrame({"정보": ["정의된 품목 없음"]})

        # 3. '비용 내역 및 요약' 시트 (엑셀은 날짜 할증 분리 유지)
        cost_details_excel = []
        if calculated_cost_items and isinstance(calculated_cost_items, list):
            for item in calculated_cost_items:
                 if isinstance(item, (list, tuple)) and len(item) >= 2:
                    item_desc = str(item[0]); item_cost = 0; item_note = ""
                    try: item_cost = int(item[1])
                    except (ValueError, TypeError): pass
                    if len(item) > 2: item_note = str(item[2])
                    if "오류" not in item_desc:
                         cost_details_excel.append({"항목": item_desc, "금액": item_cost, "비고": item_note})
        if cost_details_excel: df_costs = pd.DataFrame(cost_details_excel, columns=["항목", "금액", "비고"])
        else: df_costs = pd.DataFrame([{"항목": "계산된 비용 없음", "금액": 0, "비고": ""}])
        num_total = total_cost if isinstance(total_cost,(int,float)) else 0
        deposit_amount = state_data.get('deposit_amount', 0); deposit_amount = int(deposit_amount) if deposit_amount else 0
        remaining_balance = num_total - deposit_amount
        summary_data = [
            {"항목": "--- 비용 요약 ---", "금액": "", "비고": ""},
            {"항목": "총 견적 비용 (VAT 별도)", "금액": num_total, "비고": "모든 항목 합계"},
            {"항목": "계약금 (-)", "금액": deposit_amount, "비고": ""},
            {"항목": "잔금 (VAT 별도)", "금액": remaining_balance, "비고": "총 견적 비용 - 계약금"}
        ]
        df_summary = pd.DataFrame(summary_data, columns=["항목", "금액", "비고"])
        df_costs_final = pd.concat([df_costs, df_summary], ignore_index=True)

        # 4. 엑셀 파일 쓰기
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_info.to_excel(writer, sheet_name='견적 정보', index=False)
            df_all_items.to_excel(writer, sheet_name='전체 품목 수량', index=False)
            df_costs_final.to_excel(writer, sheet_name='비용 내역 및 요약', index=False)
            # Adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_length = 0; column = col[0].column_letter
                    try: # Header length
                        header_value = worksheet[f"{column}1"].value
                        header_len = len(str(header_value)) if header_value is not None else 0
                    except: header_len = 0
                    max_length = header_len
                    # Cell content length
                    for cell in col:
                        try:
                            if cell.value is not None:
                                # Check for multiline strings
                                cell_value_str = str(cell.value)
                                lines = cell_value_str.split('\n')
                                cell_len = max(len(line) for line in lines) if lines else 0
                                if cell_len > max_length: max_length = cell_len
                        except: pass
                    adjusted_width = (max_length + 2) * 1.2 # Add padding
                    adjusted_width = min(adjusted_width, 60) # Set max width
                    adjusted_width = max(adjusted_width, header_len + 2) # Ensure header fits
                    worksheet.column_dimensions[column].width = adjusted_width

        excel_data = output.getvalue()
        return excel_data
    except Exception as e:
        st.error(f"엑셀 파일 생성 중 오류: {e}"); print(f"Error during Excel generation: {e}"); traceback.print_exc(); return None
    finally:
        if output: output.close()

# pdf_generator.py 파일 끝