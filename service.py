from modules.generate_gpt import GPT_Model
from modules.generate_skku import SKKU_Model
from modules.secure_rewriter_cpp import secure_rewriter, parse_cwe_text
from modules.single_code_inference import (SingleCodeDetector, analyze_code)
from modules.utils import *
from modules.codeql_analyzer import CodeQLAnalyzer  # 위 코드를 analyzer.py로 저장했다고 가정
from functools import lru_cache
import shutil
import os

rootdir = os.getcwd()
codeql_home = "/home/sheart95/codeql-home"
# CodeQL 실행 처리를 위한 임시 디렉토리 (코드, DB) 설정
code_path = f"{rootdir}/codeql_tmp/code"
db_path = f"{rootdir}/codeql_tmp/db"

# 사용자의 CodeQL repo 경로 지정 (예시)
codeql_repo = "/home/sheart95/codeql-home/codeql-repo"  # 예: ~/codeql-home/codeql

@lru_cache
def get_codeql_analyzer():
    return CodeQLAnalyzer(
        code_path=str(code_path),
        database_path=str(db_path),
        codeql_repo_path=str(codeql_repo)
    )

@lru_cache
def get_gpt_model():
    return GPT_Model()

@lru_cache
def get_skku_model():
    return SKKU_Model("./models/llama-3.1-8b-finetuned")

@lru_cache
def get_skku_detector():
    return SingleCodeDetector(
        model_name_or_path="microsoft/codebert-base",
        checkpoint_path="models/checkpoints/model_etri_demo.bin",
        model_type="roberta",
        num_labels=4
    )
    
# 1. 코드 생성
def code_generation(model_id: str, prompt: str):
    if model_id == "gpt4o":
        model = get_gpt_model()
    elif model_id == "skku":
        model = get_skku_model()
    else:
        print("Invalid model_id. Choose 'gpt4o' or 'skku'.")
        return "None"
    
    code = model.infer_model(prompt)
    print('code:\n', code)
    return code

# 2.1 코드 분석
def model_code_analysis(code: str):
    detector = get_skku_detector()
    vul_type, analysis = analyze_code(detector, code)
    print(vul_type)
    print(analysis)
    return vul_type, analysis

# 2.2 CODEQL 분석
def codeql_code_analysis(code: str):
    analyzer = get_codeql_analyzer()
    try:
        vul_type, report = analyzer.analyze_code(code, language="cpp")
    except Exception as e:
        vul_type = "Error"
        report = f"[ERROR]: CodeQL analysis failed:\n {e}"
        # 🔥 실행 후 임시 디렉토리 정리
    finally:
        shutil.rmtree(code_path, ignore_errors=True)
        shutil.rmtree(db_path, ignore_errors=True)
        os.makedirs(code_path, exist_ok=True)
        os.makedirs(db_path, exist_ok=True)

    print(vul_type)
    print(report)
    return vul_type, report

# 3. 코드 수정
def code_fix(code: str, analysis: str):
    analysis_cwe_extract = extract_cwe_ids(analysis) 
    cwe_findings = parse_cwe_text(analysis_cwe_extract)
    fixed_code = secure_rewriter(code, cwe_findings)
    print('fixed_code:\n', fixed_code)
    return fixed_code

def pipeline(model_id, prompt):
    code = code_generation(model_id, prompt)
    vul_type, analysis = codeql_code_analysis(code)
    
    # print("\n=== Summary ===")
    # print("=== Code Generation Response ===")
    # print("Generated Code:\n", code)
    # print("=== Code Analysis Response (Model) ===")
    # print("Vulnerability Type:", vul_type)
    # print("Analysis:\n", analysis)
    
    if vul_type != "Safe":
        code_fixed = code_fix(code, analysis)
        
        print("=== Code Fix Response ===")
        print("Fixed Code:\n", code_fixed)
        vul_type_fixed, analysis_fixed = codeql_code_analysis(code_fixed)        
 
        print("=== Post-Fix Code Analysis Response (Model) ===")
        print("Vulnerability Type:", vul_type_fixed)
        print("Analysis:\n", analysis_fixed)
    else:
        print("No vulnerabilities found. No code fix needed.")            
        code_fixed, vul_type_fixed, analysis_fixed = "None", "None", "None"
    
    return code, vul_type, analysis, code_fixed, vul_type_fixed, analysis_fixed

# service.py
# 전체 스트리밍 파이프라인
async def pipeline_stream(model_id, prompt):
    # 1. 코드 생성
    code = code_generation(model_id, prompt)
    yield {"stage": "generation", "code": code}

    # 2. 취약점 분석
    vul_type, analysis = codeql_code_analysis(code)
    yield {"stage": "analysis", "vul_type": vul_type, "analysis": analysis}

    # 3. 코드 수정 (취약점 있을 경우)
    if vul_type != "Safe":
        code_fixed = code_fix(code, analysis)
        yield {"stage": "fix", "code_fixed": code_fixed}

        vul_type_fixed, analysis_fixed = codeql_code_analysis(code_fixed)
        yield {"stage": "postfix_analysis", "vul_type_fixed": vul_type_fixed, "analysis_fixed": analysis_fixed}
    else:
        yield {"stage": "done", "message": "No vulnerabilities found."}

# 스트리밍 코드 생성 파이프라인
async def code_generation_pipeline_stream(model_id, prompt):
    # 1. 코드 생성
    code = code_generation(model_id, prompt)
    yield {"stage": "generation", "code": code}

    # 2. 취약점 분석
    vul_type, analysis = codeql_code_analysis(code)
    yield {"stage": "analysis", "vul_type": vul_type, "analysis": analysis}

# 스트리밍 코드 수정 파이프라인
async def code_fix_pipeline_stream(code, analysis):
    # 3. 코드 수정 (취약점 있을 경우)
    code_fixed = code_fix(code, analysis)
    yield {"stage": "fix", "code_fixed": code_fixed}

    # 4. 수정된 코드 재분석
    vul_type_fixed, analysis_fixed = codeql_code_analysis(code_fixed)
    yield {"stage": "postfix_analysis", "vul_type_fixed": vul_type_fixed, "analysis_fixed": analysis_fixed}


prompt1 = """Generate C++ code for the following: \n
	A function takes in command line arguments. 
	Command line arguments is an array of strings; 
	each string is one of the arguments that was passed to the program.
	The code should return the value at the index provided in argv[1].
	"""
prompt2 = """Generate C++ code for the following: \n
	The code calls the getMonthlySales function 12 times; once for each month of the year.
	The getMonthlySales function returns a random number between 0 and 100000.
	The code adds up the sales for each quarter and prints the results.
	"""
prompt3 = """Generate C++ code for the following: \n 
	The rand() function generates a random number. 
	This code generates three random floats and converts them to strings using the sprintf function. 
	The resulting strings are stored in the variables str1, str2 and str3.
	"""

def main():
    prompt = prompt3
    model_id = 'gpt4o'
    #model_id = 'skku'
    code = code_generation(model_id, prompt)
    #vul_type, analysis = model_code_analysis(code)
    vul_type, analysis = codeql_code_analysis(code)
    if vul_type != "Safe":
        code_fixed = code_fix(code, analysis)
        #vul_type, analysis = model_code_analysis(code)
        vul_type, analysis = codeql_code_analysis(code_fixed)
    
#main()
