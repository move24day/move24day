# pdf_generator.py (최소 테스트용 코드)
import streamlit as st
import io

print("--- pdf_generator.py 임포트 시도 ---")

def generate_pdf(state_data, calculated_cost_items, total_cost, personnel_info):
    print("--- generate_pdf 함수 호출됨 (최소 버전) ---")
    st.warning("PDF 생성이 임시 비활성화되었습니다 (테스트 중).")
    # 실제 PDF 생성 대신 빈 바이트 반환 또는 None 반환
    return io.BytesIO().getvalue() # 빈 PDF 데이터처럼 보이게
    # return None # 또는 실패로 간주

def generate_excel(state_data, calculated_cost_items, total_cost, personnel_info):
     print("--- generate_excel 함수 호출됨 (최소 버전) ---")
     st.warning("Excel 요약 생성이 임시 비활성화되었습니다 (테스트 중).")
     # 실제 Excel 생성 대신 None 반환
     return None

print("--- pdf_generator.py 임포트 완료 ---")

