# email_utils.py

import streamlit as st
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import traceback

def send_quote_email(recipient_email, subject, body, pdf_bytes, pdf_filename="견적서.pdf"):
    """견적서 PDF를 이메일로 발송합니다."""

    # 1. 자격 증명 및 서버 정보 가져오기 (Streamlit Secrets)
    try:
        creds = st.secrets["email_credentials"]
        sender_email = creds["sender_email"]
        sender_password = creds["sender_password"]
        smtp_server = creds["smtp_server"]
        smtp_port = creds["smtp_port"]
    except KeyError as e:
        st.error(f"Streamlit Secrets에 이메일 설정({e})이 누락되었습니다. '.streamlit/secrets.toml' 파일을 확인하세요.")
        return False
    except Exception as e:
        st.error(f"Streamlit Secrets 로딩 중 오류: {e}")
        return False

    # 2. 수신자 이메일 유효성 검사 (간단하게)
    if not recipient_email or "@" not in recipient_email or "." not in recipient_email.split('@')[-1]:
        st.error(f"유효하지 않은 이메일 주소입니다: {recipient_email}")
        return False

    # 3. 이메일 메시지 생성 (MIMEMultipart 사용)
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    # 이메일 본문 추가
    message.attach(MIMEText(body, "plain", "utf-8")) # UTF-8 인코딩 명시

    # PDF 첨부파일 추가
    if pdf_bytes:
        try:
            # pdf_filename을 UTF-8로 인코딩 시도 -> MIMEApplication에서 처리하도록 변경
            # encoded_filename = pdf_filename.encode('utf-8').decode('latin-1') # 호환성 문제 가능성
            part = MIMEApplication(pdf_bytes, Name=pdf_filename) # 파일명 직접 사용
            # Content-Disposition 헤더는 filename* 파라미터를 사용하여 UTF-8 인코딩 명시 가능
            part.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', pdf_filename))
            message.attach(part)
            print(f"DEBUG: PDF attached with filename: {pdf_filename}")
        except Exception as e:
            st.error(f"PDF 첨부파일 처리 중 오류: {e}")
            print(f"Error attaching PDF: {e}")
            return False # PDF 첨부 실패 시 발송 중단

    # 4. SMTP 서버 연결 및 이메일 발송
    server = None # 서버 객체 초기화
    try:
        context = ssl.create_default_context()
        print(f"DEBUG: Connecting to SMTP: {smtp_server}:{smtp_port}")
        if smtp_port == 465: # SSL 포트
             server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
             print("DEBUG: Using SMTP_SSL.")
        elif smtp_port == 587: # TLS 포트
             server = smtplib.SMTP(smtp_server, smtp_port)
             print("DEBUG: Using SMTP with STARTTLS.")
             server.ehlo() # Can be helpful before starttls
             server.starttls(context=context) # TLS 보안 연결 시작
             server.ehlo() # Starttls 후 다시 ehlo
        else: # 기타 포트
             server = smtplib.SMTP(smtp_server, smtp_port)
             print(f"DEBUG: Using SMTP on port {smtp_port}. Consider security implications.")
             # 필요시 server.starttls() 또는 다른 보안 설정 추가

        print(f"DEBUG: Logging in as {sender_email}")
        server.login(sender_email, sender_password)
        print("DEBUG: Login successful.")

        server.send_message(message) # 메시지 발송
        print(f"DEBUG: Email sent successfully to {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        st.error("이메일 로그인 실패: 이메일 주소 또는 앱 비밀번호를 확인하세요.")
        print("Error: SMTP Authentication Error. Check email/password.")
        return False
    except smtplib.SMTPServerDisconnected:
        st.error("SMTP 서버 연결이 끊겼습니다. 잠시 후 다시 시도하세요.")
        print("Error: SMTP Server Disconnected.")
        return False
    except smtplib.SMTPException as e:
        st.error(f"SMTP 오류 발생: {e}")
        print(f"Error: SMTP Exception: {e}")
        return False
    except ConnectionRefusedError:
         st.error(f"SMTP 서버 연결 거부: 서버 주소({smtp_server}) 또는 포트({smtp_port})를 확인하세요.")
         print(f"Error: Connection Refused for SMTP server {smtp_server}:{smtp_port}")
         return False
    except Exception as e:
        st.error(f"이메일 발송 중 예상치 못한 오류 발생: {e}")
        print(f"Error: Unexpected error sending email: {e}")
        traceback.print_exc()
        return False
    finally:
        # 서버 연결 종료 (연결이 성공적으로 수립되었을 경우)
        if server:
            try:
                 server.quit()
                 print("DEBUG: SMTP connection closed.")
            except Exception as e:
                 print(f"Warning: Error quitting SMTP server: {e}")