from modules.generate_gpt import GPT_Model
from modules.generate_skku import SKKU_Model
from modules.secure_rewriter_cpp import secure_rewriter, parse_cwe_text
from modules.single_code_inference import (SingleCodeDetector, analyze_code)
from modules.utils import *
from modules.codeql_analyzer import CodeQLAnalyzer  # 위 코드를 analyzer.py로 저장했다고 가정

# CodeQL 실행 처리를 위한 임시 디렉토리 (코드, DB) 설정
code_path = "codeql_tmp/code"
db_path = "codeql_tmp/db"

# 사용자의 CodeQL repo 경로 지정 (예시)
codeql_repo = "/home/sheart95/codeql-home/codeql-repo"  # 예: ~/codeql-home/codeql

# 분석기 초기화
analyzer = CodeQLAnalyzer(
    code_path=str(code_path),
    database_path=str(db_path),
    codeql_repo_path=str(codeql_repo)
)

model_gpt = GPT_Model()
model_skku = SKKU_Model("./models/llama-3.1-8b-finetuned")
models = {"gpt4o": model_gpt, "skku": model_skku}

detector = SingleCodeDetector(
        model_name_or_path="microsoft/codebert-base",
        checkpoint_path="models/checkpoints/model_etri_demo.bin",  # Optional
        model_type="roberta",
        num_labels=4
    )
        
# 1. 코드 생성
def code_generation(model_id: str, prompt: str):
    model = models.get(model_id)
    if model is None:
        print("Invalid model_id. Choose 'gpt4o' or 'skku'.")
        return "None"
    
    code = model.infer_model(prompt)
    print('code:\n', code)
    return code

# 2.1 코드 분석
def model_code_anaysis(code: str):
    vul_type, analysis = analyze_code(detector, code)
    print(analysis)
    return vul_type, analysis

# 2.2 CODEQL 분석
def codeql_code_analysis(code: str):
    from codeql_test import codeql_analyze  # codeql_test.py의 함수를 임포트
    report = codeql_analyze(code)
    print(report)
    return report

# 3. 코드 수정
def code_fix(code: str, analysis: str):
    analysis_cwe_extract = extract_cwe_ids(analysis) 
    cwe_findings = parse_cwe_text(analysis_cwe_extract)
    fixed_code = secure_rewriter(code, cwe_findings)
    print('fixed_code:\n', fixed_code)
    return fixed_code

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
    # model_id = 'skku'
    code = code_generation(model_id, prompt)
    # vul_type, analysis = model_code_anaysis(code)
    analysis = codeql_code_analysis(code)
    # code_fixed = code_fix(code, analysis)
    
main()