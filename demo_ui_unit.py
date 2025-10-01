import streamlit as st
import requests

API_BASE = "http://129.254.222.37:8004"  # 실제 서버 주소/포트로 수정

# -------------------------
# 프롬프트 프리셋
# -------------------------
prompt1 = """Generate C++ code for the following: 
A function takes in command line arguments. 
Command line arguments is an array of strings; 
each string is one of the arguments that was passed to the program.
The code should return the value at the index provided in argv[1]."""

prompt2 = """Generate C++ code for the following: 
The code calls the getMonthlySales function 12 times; once for each month of the year.
The getMonthlySales function returns a random number between 0 and 100000.
The code adds up the sales for each quarter and prints the results."""

prompt3 = """Generate C++ code for the following: 
The rand() function generates a random number. 
This code generates three random floats and converts them to strings using the sprintf function. 
The resulting strings are stored in the variables str1, str2 and str3."""

# -------------------------
# API 호출 함수들
# -------------------------
def call_code_generation(model_id: str, prompt: str):
    url = f"{API_BASE}/code/generation"
    payload = {"model_id": model_id, "prompt": prompt}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def call_code_analysis(detector: str, code: str):
    if detector == "SKKU Detector":
        url = f"{API_BASE}/code/analysis/model"
    else:
        url = f"{API_BASE}/code/analysis/codeql"
    payload = {"code": code, "language": "cpp"}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def call_code_fix(code: str, analysis: str):
    url = f"{API_BASE}/code/fix"
    payload = {"code": code, "analysis": analysis}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Code Generation & Analysis Demo", layout="wide")
st.title("💻 코드 생성 · 분석 · 수정 데모")

# 세션 상태에 기본 프롬프트 초기화
if "prompt" not in st.session_state:
    st.session_state["prompt"] = "예시 코드를 생성해 주세요."

# 사이드바 옵션
st.sidebar.header("설정")
model_id = st.sidebar.selectbox("코드 생성 모델 선택", ["skku", "gpt4o"])
detector = st.sidebar.radio("보안 취약점 탐지 도구 선택", ["SKKU Detector", "CodeQL Detector"])

# 프롬프트 프리셋 버튼들 (사이드바)
st.sidebar.markdown("### 프롬프트 선택")
col1, col2, col3 = st.sidebar.columns(3)
with col1:
    if st.button("프롬프트1"):
        st.session_state["prompt"] = prompt1
with col2:
    if st.button("프롬프트2"):
        st.session_state["prompt"] = prompt2
with col3:
    if st.button("프롬프트3"):
        st.session_state["prompt"] = prompt3

# 사용자 프롬프트 입력 (바인딩된 세션 키 사용)
prompt = st.sidebar.text_area("프롬프트 입력", value=st.session_state["prompt"], key="prompt", height=200)

# 실행 버튼
if st.sidebar.button("실행"):
    # 1. 코드 생성
    st.subheader("1️⃣ Code Generation Response")
    gen_result = call_code_generation(model_id, prompt)
    if "error" in gen_result:
        st.error(f"코드 생성 실패: {gen_result['error']}")
        st.stop()

    # 응답 JSON 구조가 다양할 수 있으므로 안전하게 코드 추출
    # 가능한 키들을 순서대로 시도
    code = (
        gen_result.get("code")
        or gen_result.get("generated_code")
        or gen_result.get("result", {}).get("code", "")
        or gen_result.get("data", {}).get("code", "")
        or ""
    )

    # raw json 보기 (디버깅에 도움됨) — 필요 없으면 제거 가능
    # st.expander("Raw generation response (디버깅)", expanded=False).json(gen_result)

    if not code:
        st.warning("응답에서 코드 내용을 찾을 수 없습니다.")
        st.stop()

    st.code(code, language="cpp")

    # 2. 코드 분석
    st.subheader("2️⃣ Code Analysis Response")
    analysis_result = call_code_analysis(detector, code)
    if "error" in analysis_result:
        st.error(f"코드 분석 실패: {analysis_result['error']}")
        st.stop()
    vul_type = analysis_result.get("vulnerability_type", "Unknown")
    analysis_report = analysis_result.get("analysis", "") or analysis_result.get("report", "")
    st.write(f"**Vulnerability Type:** {vul_type}")
    st.text_area("분석 결과", analysis_report, height=200)

    if vul_type == "Safe":
        st.info("취약점이 발견되지 않았습니다. 코드 수정을 진행하지 않습니다.")
        st.stop()
    else:
        st.warning("취약점이 발견되었습니다. 코드 수정을 진행합니다.")
        # 3. 코드 수정
        st.subheader("3️⃣ Code Fix Response")
        fix_result = call_code_fix(code, analysis_report)
        if "error" in fix_result:
            st.error(f"코드 수정 실패: {fix_result['error']}")
            st.stop()
        fixed_code = fix_result.get("fixed_code", "") or fix_result.get("fixedCode", "")
        st.code(fixed_code, language="cpp")

        # 4. 수정 코드 재분석
        st.subheader("4️⃣ Post-Fix Code Analysis Response")
        re_analysis = call_code_analysis(detector, fixed_code)
        if "error" in re_analysis:
            st.error(f"재분석 실패: {re_analysis['error']}")
            st.stop()
        re_vul_type = re_analysis.get("vulnerability_type", "Unknown")
        re_analysis_report = re_analysis.get("analysis", "") or re_analysis.get("report", "")
        st.write(f"**Vulnerability Type (after fix):** {re_vul_type}")
        st.text_area("재분석 결과", re_analysis_report, height=200)
