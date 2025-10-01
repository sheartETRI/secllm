import streamlit as st
import requests
import json

#API_BASE = "http://127.0.0.1:8000"  # 실제 서버 주소/포트로 수정
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
# API 호출 함수
# -------------------------
def call_pipeline(model_id: str, prompt: str):
    url = f"{API_BASE}/code/pipeline"
    payload = {"model_id": model_id, "prompt": prompt}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
    
def call_pipeline_stream(model_id: str, prompt: str):
    url = f"{API_BASE}/code/pipeline/stream"
    payload = {"model_id": model_id, "prompt": prompt}
    try:
        with requests.post(url, json=payload, stream=True) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield json.loads(line.decode("utf-8"))
    except Exception as e:
        yield {"error": str(e)}


# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Code Pipeline Demo", layout="wide")
st.title("🔗 코드 파이프라인 데모")

# 세션 상태에 기본 프롬프트 초기화
if "prompt" not in st.session_state:
    st.session_state["prompt"] = "예시 코드를 생성해 주세요."

# 사이드바 옵션
st.sidebar.header("설정")
pipeline_choice = st.sidebar.radio(
    "파이프라인 선택",
    ["Pipeline1: SKKU Model Pipeline", "Pipeline2: GPT4o Model Pipeline"]
)
run_mode = st.sidebar.radio("실행 모드", ["스트리밍", "일반"])

# 파이프라인별 모델 고정
if pipeline_choice.startswith("Pipeline1"):
    model_id = "skku"
else:
    model_id = "gpt4o"

# 프롬프트 프리셋 버튼
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

# 사용자 프롬프트 입력
prompt = st.sidebar.text_area("프롬프트 입력", value=st.session_state["prompt"], key="prompt", height=200)

# 실행 버튼
if st.sidebar.button("실행"):
    st.subheader("🚀 파이프라인 실행 결과")

    if run_mode == "일반":
        result = call_pipeline(model_id, prompt)
        if "error" in result:
            st.error(f"파이프라인 실행 실패: {result['error']}")
            st.stop()

        # 1. 코드 생성 결과
        st.subheader("1️⃣ Code Generation Response")
        st.code(result.get("code", ""), language="cpp")

        # 2. 분석 결과
        st.subheader("2️⃣ Code Analysis Response")
        st.write(f"**Vulnerability Type:** {result.get('vul_type', 'Unknown')}")
        st.text_area("분석 결과", result.get("analysis", ""), height=200)

        # 3. 수정 코드 (필요 시)
        if result.get("vul_type") != "Safe":
            st.subheader("3️⃣ Code Fix Response")
            st.code(result.get("code_fixed", ""), language="cpp")

            # 4. 수정 후 재분석
            st.subheader("4️⃣ Post-Fix Code Analysis Response")
            st.write(f"**Vulnerability Type (after fix):** {result.get('vul_type_fixed', 'Unknown')}")
            st.text_area("재분석 결과", result.get("analysis_fixed", ""), height=200)
        else:
            st.info("취약점이 발견되지 않아 코드 수정 단계는 건너뜁니다.")
    else:  # 스트리밍 모드
        st.info("스트리밍 모드로 실행 중...")

        # 제목 placeholder
        gen_title = st.empty()
        analysis_title = st.empty()
        fix_title = st.empty()
        postfix_title = st.empty()

        for chunk in call_pipeline_stream(model_id, prompt):
            if "error" in chunk:
                st.error(f"스트리밍 실패: {chunk['error']}")
                break

            stage = chunk.get("stage")
            if stage == "generation":
                gen_title.subheader("1️⃣ Code Generation")
                st.write("생성된 코드:")
                st.code(chunk.get("code", ""), language="cpp")

            elif stage == "analysis":
                analysis_title.subheader("2️⃣ Code Analysis")
                st.write(f"**Vulnerability Type:** {chunk.get('vul_type','Unknown')}")
                st.text_area("분석 결과", chunk.get("analysis",""), height=200)

            elif stage == "fix":
                fix_title.subheader("3️⃣ Code Fix")
                st.write("수정된 코드:")
                st.code(chunk.get("code_fixed",""), language="cpp")

            elif stage == "postfix_analysis":
                postfix_title.subheader("4️⃣ Post-Fix Analysis")
                st.write(f"**Vulnerability Type (after fix):** {chunk.get('vul_type_fixed','Unknown')}")
                st.text_area("재분석 결과", chunk.get("analysis_fixed",""), height=200)

            elif stage == "done":
                st.success(chunk.get("message","Done."))
