import streamlit as st
import requests
import json
from demo import prompt1, prompt2, prompt3

# API_BASE = "http://127.0.0.1:8000"  # 실제 서버 주소/포트
API_BASE = "http://129.254.222.37:8004"  # 실제 서버 주소/포트

def call_pipeline_generation_stream(model_id: str, prompt: str):
    url = f"{API_BASE}/code/pipeline/generation_stream"
    payload = {"model_id": model_id, "prompt": prompt}
    with requests.post(url, json=payload, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield json.loads(line.decode("utf-8"))

def call_pipeline_fix_stream(code: str, analysis: str):
    url = f"{API_BASE}/code/pipeline/fix_stream"
    payload = {"code": code, "analysis": analysis}
    with requests.post(url, json=payload, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield json.loads(line.decode("utf-8"))

st.set_page_config(page_title="Code Pipeline Streaming Demo", layout="wide")
st.title("🔗 코드 파이프라인 스트리밍 데모")

# -------------------------
# 세션 상태 초기화
# -------------------------
if "model_id" not in st.session_state:
    st.session_state["model_id"] = None
if "prompt" not in st.session_state:
    st.session_state["prompt"] = "예시 코드를 생성해 주세요."
if "code" not in st.session_state:
    st.session_state["code"] = None
if "analysis" not in st.session_state:
    st.session_state["analysis"] = None
if "code_fixed" not in st.session_state:
    st.session_state["code_fixed"] = None
if "analysis_fixed" not in st.session_state:
    st.session_state["analysis_fixed"] = None

# -------------------------
# 사이드바
# -------------------------
st.sidebar.header("⚙️ 설정")

# 1. 모델 선택
st.sidebar.markdown("### 1. 모델 선택")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("🧑‍🎓 SKKU Model"):
        st.session_state["model_id"] = "skku"
with col2:
    if st.sidebar.button("🤖 GPT4o Model"):
        st.session_state["model_id"] = "gpt4o"

if st.session_state["model_id"]:
    st.sidebar.success(f"선택된 모델: {st.session_state['model_id']}")

# 2. 프롬프트 선택
st.sidebar.markdown("### 2. 프롬프트 선택")
col1, col2, col3 = st.sidebar.columns(3)
with col1:
    if st.sidebar.button("프롬프트1"):
        st.session_state["prompt"] = prompt1
with col2:
    if st.sidebar.button("프롬프트2"):
        st.session_state["prompt"] = prompt2
with col3:
    if st.sidebar.button("프롬프트3"):
        st.session_state["prompt"] = prompt3

st.sidebar.info(f"선택된 프롬프트: {st.session_state['prompt'][:40]}...")

# 사용자 프롬프트 입력
prompt = st.sidebar.text_area(
    "직접 프롬프트 입력", 
    value=st.session_state["prompt"], 
    key="prompt", 
    height=200
)

# -------------------------
# 메인 컨테이너 두 개 유지
# -------------------------
gen_container = st.container()
fix_container = st.container()

# -------------------------
# 3. 코드 생성 버튼
# -------------------------
st.sidebar.markdown("### 3. 코드 생성")
if st.sidebar.button("🚀 코드 생성"):
    if not st.session_state["model_id"]:
        st.error("먼저 모델을 선택하세요.")
    else:
        # 코드 생성 시작 시, 코드 수정 컨테이너 초기화
        with fix_container:
            st.empty()
        st.session_state["code_fixed"] = None
        st.session_state["analysis_fixed"] = None

        with gen_container:
            st.subheader("1️⃣ 코드 생성 및 분석 결과 (스트리밍)")
            code_box = st.empty()
            analysis_box = st.empty()

            for chunk in call_pipeline_generation_stream(st.session_state["model_id"], prompt):
                stage = chunk.get("stage")
                if stage == "generation":
                    st.session_state["code"] = chunk.get("code")
                    code_box.subheader("생성된 코드")
                    code_box.code(st.session_state["code"], language="cpp")
                elif stage == "analysis":
                    st.session_state["analysis"] = chunk.get("analysis")
                    analysis_box.subheader("분석 결과")
                    analysis_box.text_area("코드 분석 결과", st.session_state["analysis"], height=200)
                elif stage == "done":
                    st.success(chunk.get("message", "완료"))

# -------------------------
# 4. 코드 수정 버튼
# -------------------------
st.sidebar.markdown("### 4. 코드 수정")
if st.sidebar.button("🛠 코드 수정"):
    if not st.session_state["code"] or not st.session_state["analysis"]:
        st.warning("먼저 '코드 생성'을 실행해야 합니다.")
    else:
        with fix_container:
            st.subheader("2️⃣ 코드 수정 및 재분석 결과 (스트리밍)")
            fix_box = st.empty()
            postfix_box = st.empty()

            for chunk in call_pipeline_fix_stream(st.session_state["code"], st.session_state["analysis"]):
                stage = chunk.get("stage")
                if stage == "fix":
                    st.session_state["code_fixed"] = chunk.get("code_fixed")
                    fix_box.subheader("수정된 코드")
                    fix_box.code(st.session_state["code_fixed"], language="cpp")
                elif stage == "postfix_analysis":
                    st.session_state["analysis_fixed"] = chunk.get("analysis_fixed")
                    postfix_box.subheader("재분석 결과")
                    postfix_box.text_area("수정 코드 분석", st.session_state["analysis_fixed"], height=200)
                elif stage == "done":
                    st.success(chunk.get("message", "완료"))
