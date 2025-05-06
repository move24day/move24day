# pdf_generator.py (PDF 비용 누락 문제 해결, 엑셀 로직 개선, 날짜할증 병합)

import pandas as pd
import io
import streamlit as st
import traceback
import utils # utils.py 가 필요합니다
import data # data.py 가 필요합니다 (차량 부피 90% 적용된 버전)
import os
from datetime import date

# --- ReportLab 관련 모듈 임포트 ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- 회사 정보 상수 정의 ---
COMPANY_ADDRESS = "서울 은평구 가좌로10길 33-1"
COMPANY_PHONE_1 = "010-5047-1111"
COMPANY_PHONE_2 = "1577-3101"
COMPANY_EMAIL = "move24day@gmail.com"

# --- 폰트 경로 설정 ---
NANUM_GOTHIC_FONT_PATH = "NanumGothic.ttf"

# --- PDF 생성 함수 (날짜 할증 병합 로직 추가) ---
def generate_pdf(state_data, calculated_cost_items, total_cost, personnel_info):
    """주어진 데이터를 기반으로 견적서 PDF를 생성합니다."""
    buffer = io.BytesIO()
    try:
        # ... (폰트 처리, 기본 설정, 페이지 템플릿 정의 - 이전과 동일) ...
        if not os.path.exists(NANUM_GOTHIC_FONT_PATH):
            st.error(f"PDF 생성 오류: 폰트 파일 '{NANUM_GOTHIC_FONT_PATH}' 찾을 수 없음."); return None
        try:
            pdfmetrics.registerFont(TTFont('NanumGothic', NANUM_GOTHIC_FONT_PATH))
            pdfmetrics.registerFont(TTFont('NanumGothicBold', NANUM_GOTHIC_FONT_PATH))
        except Exception as font_e:
            st.error(f"PDF 생성 오류: 폰트 로딩 실패 ('{NANUM_GOTHIC_FONT_PATH}'). 상세: {font_e}"); return None

        c = canvas.Canvas(buffer, pagesize=A4); width, height = A4
        margin_x = 1.5*cm; margin_y = 1.5*cm; line_height = 0.6*cm
        right_margin_x = width - margin_x; page_number = 1

        def draw_page_template(canvas_obj, page_num): # 페이지 상단 정보
            canvas_obj.saveState(); canvas_obj.setFont('NanumGothic', 7)
            company_info_line_height = 0.35 * cm; company_info_y = height - margin_y
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"주소: {COMPANY_ADDRESS}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"전화: {COMPANY_PHONE_1} | {COMPANY_PHONE_2}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"이메일: {COMPANY_EMAIL}")
            canvas_obj.restoreState()

        current_y = height - margin_y - 1*cm
        draw_page_template(c, page_number)
        c.setFont('NanumGothicBold', 18)
        c.drawCentredString(width / 2.0, current_y, "이삿날 견적서(계약서)"); current_y -= line_height * 2
        styles = getSampleStyleSheet()
        center_style = ParagraphStyle(name='Center', fontName='NanumGothic', fontSize=10, leading=14, alignment=TA_CENTER)
        service_text = """고객님의 이사를 안전하고 신속하게 책임지는 이삿날입니다."""
        p_service = Paragraph(service_text, center_style)
        p_service_width, p_service_height = p_service.wrapOn(c, width - margin_x*2, 5*cm)
        if current_y - p_service_height < margin_y:
            c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
        p_service.drawOn(c, margin_x, current_y - p_service_height); current_y -= (p_service_height + line_height)

        # ... (기본 정보 그리기 - 이전과 동일) ...
        c.setFont('NanumGothic', 11); is_storage = state_data.get('is_storage_move')
        info_pairs = [
            ("고 객 명:", state_data.get('customer_name', '-')), ("연 락 처:", state_data.get('customer_phone', '-')),
            ("이 사 일:", str(state_data.get('moving_date', '-'))), ("견 적 일:", utils.get_current_kst_time_str()),
            ("출 발 지:", state_data.get('from_location', '-')), ("도 착 지:", state_data.get('to_location', '-'))
        ]
        if is_storage:
            info_pairs.append(("보관 기간:", f"{state_data.get('storage_duration', 1)} 일"))
            info_pairs.append(("보관 유형:", state_data.get('storage_type', data.DEFAULT_STORAGE_TYPE)))
        p_info = personnel_info if isinstance(personnel_info, dict) else {}
        final_men = p_info.get('final_men', 0); final_women = p_info.get('final_women', 0)
        personnel_text = f"남성 {final_men}명" + (f", 여성 {final_women}명" if final_women > 0 else "")
        info_pairs.append(("작업 인원:", personnel_text))
        info_pairs.append(("선택 차량:", state_data.get('final_selected_vehicle', '미선택')))
        value_style = ParagraphStyle(name='Value', fontName='NanumGothic', fontSize=11, leading=13)
        label_width = 3 * cm; value_x = margin_x + label_width
        for label, value in info_pairs:
            value_para = Paragraph(str(value), value_style)
            value_para_width, value_para_height = value_para.wrapOn(c, width - margin_x - value_x, line_height * 3)
            row_height = max(line_height, value_para_height + 0.1*cm)
            if current_y - row_height < margin_y:
                c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm; c.setFont('NanumGothic', 11)
            c.drawString(margin_x, current_y - (row_height - 11)/2, label)
            value_para.drawOn(c, value_x, current_y - value_para_height - (row_height - value_para_height)/2 + 2)
            current_y -= row_height
        current_y -= line_height * 0.5


        # 비용 내역
        cost_start_y = current_y
        if cost_start_y < margin_y + 5*cm :
            c.showPage(); page_number += 1; draw_page_template(c, page_number); cost_start_y = height - margin_y - 1*cm
        current_y = cost_start_y
        c.setFont('NanumGothicBold', 12); c.drawString(margin_x, current_y, "[ 비용 상세 내역 ]"); current_y -= line_height * 1.2
        c.setFont('NanumGothicBold', 10); cost_col1_x = margin_x; cost_col2_x = margin_x + 8*cm; cost_col3_x = margin_x + 11*cm
        c.drawString(cost_col1_x, current_y, "항목"); c.drawRightString(cost_col2_x + 2*cm, current_y, "금액"); c.drawString(cost_col3_x, current_y, "비고")
        c.setFont('NanumGothic', 10); current_y -= 0.2*cm; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height * 0.8

        # ========== 날짜 할증 병합 로직 추가 ==========
        cost_items_processed = []
        base_fare_item = None
        date_surcharge_amount = 0
        date_surcharge_notes = ""

        if calculated_cost_items and isinstance(calculated_cost_items, list):
            temp_items = [list(item) for item in calculated_cost_items if isinstance(item, (list, tuple)) and len(item) >= 2 and "오류" not in str(item[0])] # 수정 가능한 리스트로 복사

            # 날짜 할증 찾기 및 정보 추출
            date_surcharge_index = -1
            for i, item in enumerate(temp_items):
                if str(item[0]) == "날짜 할증":
                    try: date_surcharge_amount = int(item[1])
                    except: date_surcharge_amount = 0
                    if len(item) > 2: date_surcharge_notes = str(item[2])
                    date_surcharge_index = i
                    break

            # 기본 운임 찾기 및 날짜 할증 합치기
            base_fare_index = -1
            for i, item in enumerate(temp_items):
                 if str(item[0]) == "기본 운임":
                    base_fare_index = i
                    if date_surcharge_index != -1 and date_surcharge_amount > 0: # 날짜 할증이 있었으면
                        try:
                            original_base_fare = int(item[1])
                            item[1] = original_base_fare + date_surcharge_amount # 금액 합산
                            original_note = str(item[2]) if len(item) > 2 else ""
                            # 비고 업데이트 (기존 비고 + 할증 내용)
                            item[2] = f"{original_note} (날짜 할증 [{date_surcharge_notes}] 포함)"
                        except Exception as e:
                             print(f"Error merging date surcharge into base fare: {e}")
                    break # 기본 운임 찾음

            # 날짜 할증 항목 제거 (만약 찾았다면)
            if date_surcharge_index != -1:
                 del temp_items[date_surcharge_index]

            # 최종 그릴 항목 리스트 생성
            for item_desc, item_cost, *item_note_tuple in temp_items:
                item_note = item_note_tuple[0] if item_note_tuple else ""
                try: item_cost_int = int(item_cost) # 금액은 정수로
                except: item_cost_int = 0
                cost_items_processed.append((str(item_desc), item_cost_int, str(item_note)))

        # ==============================================

        # ========== 수정된 cost_items_processed 사용 ==========
        if cost_items_processed:
            styleDesc = ParagraphStyle(name='Desc', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)
            styleCost = ParagraphStyle(name='Cost', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_RIGHT)
            styleNote = ParagraphStyle(name='Note', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)

            for item_desc, item_cost, item_note in cost_items_processed: # 처리된 리스트 사용
                cost_str = f"{item_cost:,.0f} 원"; note_str = item_note if item_note else ""
                p_desc = Paragraph(item_desc, styleDesc); p_cost = Paragraph(cost_str, styleCost); p_note = Paragraph(note_str, styleNote)
                desc_width = cost_col2_x - cost_col1_x - 0.5*cm; cost_width = (cost_col3_x - cost_col2_x) + 1.5*cm; note_width = right_margin_x - cost_col3_x
                desc_height = p_desc.wrap(desc_width, 1000)[1]; cost_height = p_cost.wrap(cost_width, 1000)[1]; note_height = p_note.wrap(note_width, 1000)[1]
                max_row_height = max(desc_height, cost_height, note_height, line_height * 0.8)
                if current_y - max_row_height < margin_y: # 페이지 넘김
                    c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
                    c.setFont('NanumGothicBold', 10); c.drawString(cost_col1_x, current_y, "항목"); c.drawRightString(cost_col2_x + 2*cm, current_y, "금액"); c.drawString(cost_col3_x, current_y, "비고")
                    current_y -= 0.2*cm; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height * 0.8; c.setFont('NanumGothic', 10)
                y_draw_base = current_y - max_row_height
                p_desc.drawOn(c, cost_col1_x, y_draw_base + (max_row_height - desc_height))
                p_cost.drawOn(c, cost_col2_x + 2*cm - cost_width, y_draw_base + (max_row_height - cost_height))
                p_note.drawOn(c, cost_col3_x, y_draw_base + (max_row_height - note_height))
                current_y -= (max_row_height + 0.2*cm)
        # ====================================================

            # 비용 요약 (여기는 변경 없음 - total_cost는 이미 날짜 할증 포함)
            summary_start_y = current_y
            if summary_start_y < margin_y + line_height * 5:
                c.showPage(); page_number += 1; draw_page_template(c, page_number); summary_start_y = height - margin_y - 1*cm
            current_y = summary_start_y; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height
            total_cost_num = int(total_cost) if isinstance(total_cost, (int, float)) else 0
            deposit_amount = state_data.get('deposit_amount', 0);
            try: deposit_amount = int(deposit_amount)
            except (ValueError, TypeError): deposit_amount = 0
            remaining_balance = total_cost_num - deposit_amount
            c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "총 견적 비용 (VAT 별도)")
            total_cost_str = f"{total_cost_num:,.0f} 원"; c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, total_cost_str); current_y -= line_height
            c.setFont('NanumGothic', 11); c.drawString(cost_col1_x, current_y, "계약금 (-)")
            deposit_str = f"{deposit_amount:,.0f} 원"; c.setFont('NanumGothic', 12); c.drawRightString(right_margin_x, current_y, deposit_str); current_y -= line_height
            c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "잔금 (VAT 별도)")
            remaining_str = f"{remaining_balance:,.0f} 원"; c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, remaining_str); current_y -= line_height
        else: # 비용 내역 없을 때
             if current_y < margin_y + 5*cm: c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
             c.drawString(cost_col1_x, current_y, "계산된 비용 내역이 없습니다."); current_y -= line_height * 1.5
             c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height
             total_cost_num = 0; deposit_amount = state_data.get('deposit_amount', 0); deposit_amount = int(deposit_amount) if deposit_amount else 0; remaining_balance = -deposit_amount
             c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "총 견적 비용 (VAT 별도)"); c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, "0 원"); current_y -= line_height
             c.setFont('NanumGothic', 11); c.drawString(cost_col1_x, current_y, "계약금 (-)"); deposit_str = f"{deposit_amount:,.0f} 원"; c.setFont('NanumGothic', 12); c.drawRightString(right_margin_x, current_y, deposit_str); current_y -= line_height
             c.setFont('NanumGothicBold', 12); c.drawString(cost_col1_x, current_y, "잔금 (VAT 별도)"); c.setFont('NanumGothicBold', 14); c.drawRightString(right_margin_x, current_y, f"{remaining_balance:,.0f} 원"); current_y -= line_height

        # ... (고객요구사항 그리기 - 이전과 동일) ...
        special_notes = state_data.get('special_notes', '').strip()
        if special_notes:
            notes_start_y = current_y - line_height
            styleNotes = ParagraphStyle(name='Notes', fontName='NanumGothic', fontSize=10, leading=12, alignment=TA_LEFT)
            p_notes = Paragraph(special_notes.replace('\n', '<br/>'), styleNotes)
            req_width = width - margin_x*2; notes_height = p_notes.wrap(req_width, 1000)[1]
            needed_notes_height = notes_height + line_height * 1.5
            if notes_start_y - needed_notes_height < margin_y:
                c.showPage(); page_number += 1; draw_page_template(c, page_number); notes_start_y = height - margin_y - 1*cm
            current_y = notes_start_y; c.setFont('NanumGothicBold', 11); c.drawString(margin_x, current_y, "[ 고객요구사항 ]"); current_y -= line_height * 1.2
            p_notes.drawOn(c, margin_x, current_y - notes_height)


        c.save(); buffer.seek(0); return buffer.getvalue()
    except Exception as e:
        st.error(f"PDF 생성 중 예외 발생: {e}"); print(f"Error during PDF generation: {e}"); traceback.print_exc(); return None
    finally:
        if buffer: buffer.close()


# --- 엑셀 생성 함수 (변경 없음) ---
# generate_excel 함수는 이전 최종 버전과 동일하게 유지됩니다.
# 엑셀에서는 날짜 할증이 별도 항목으로 표시되는 것이 더 명확할 수 있습니다.
# 만약 엑셀에서도 병합을 원하시면 추가 수정이 필요합니다.
def generate_excel(state_data, calculated_cost_items, total_cost, personnel_info):
    # ... (이전 최종 버전의 generate_excel 코드 전체) ...
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
            elif label == "견적일": value = utils.get_current_kst_time_str()
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
        all_items_data = []; current_move_type = state_data.get('base_move_type', list(data.item_definitions.keys())[0]); item_defs = data.item_definitions.get(current_move_type, {}); processed_all_items = set()
        if isinstance(item_defs, dict):
            for section, item_list in item_defs.items():
                if section == "폐기 처리 품목 🗑️": continue
                if isinstance(item_list, list):
                    for item_name in item_list:
                        if item_name in processed_all_items or item_name not in data.items: continue
                        widget_key = f"qty_{current_move_type}_{section}_{item_name}"; qty = state_data.get(widget_key, 0);
                        try: qty = int(qty) if qty is not None else 0
                        except (ValueError, TypeError): qty = 0
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
            df_info.to_excel(writer, sheet_name='견적 정보', index=False); df_all_items.to_excel(writer, sheet_name='전체 품목 수량', index=False); df_costs_final.to_excel(writer, sheet_name='비용 내역 및 요약', index=False)
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_length = 0; column = col[0].column_letter
                    try: header_len = len(str(worksheet[f"{column}1"].value))
                    except: header_len = 0
                    max_length = header_len
                    for cell in col:
                        try:
                            if cell.value is not None:
                                cell_value_str = str(cell.value)
                                if len(cell_value_str) > max_length: max_length = len(cell_value_str)
                        except: pass
                    adjusted_width = (max_length + 2) * 1.2
                    adjusted_width = min(adjusted_width, 60)
                    worksheet.column_dimensions[column].width = adjusted_width

        excel_data = output.getvalue()
        return excel_data
    except Exception as e:
        st.error(f"엑셀 파일 생성 중 오류: {e}"); print(f"Error during Excel generation: {e}"); traceback.print_exc(); return None
    finally:
        if output: output.close()