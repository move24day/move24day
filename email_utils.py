# email_utils.py (임시 테스트 내용)
import streamlit as st
print("--- email_utils.py 임포트 성공! ---") # 임포트 성공 확인 메시지

def send_quote_email(recipient_email, subject, body, pdf_bytes, pdf_filename="견적서.pdf"):
    print("--- send_quote_email 함수 호출됨 (임시 버전) ---")
    st.info("임시 이메일 함수가 호출되었습니다.")
    # 실제 이메일 발송은 안 하고 무조건 성공으로 간주
    return True