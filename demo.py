import requests

#BASE_URL = "http://127.0.0.1:8000"
BASE_URL = "http://129.254.222.37:8004"

# 1. 코드 생성 테스트
# model_id: "gpt4o" or "skku"
# prompt: 생성할 코드에 대한 설명
def code_generation(model_id, prompt):
    url = f"{BASE_URL}/code/generation"
    payload = {
        "model_id": model_id,
        "prompt": prompt
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 2. 모델 기반 코드 분석 테스트
def code_analysis_model(code):
    url = f"{BASE_URL}/code/analysis/model"
    payload = {
        "code": code
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 3. CodeQL 기반 코드 분석 테스트
def code_analysis_codeql(code):
    url = f"{BASE_URL}/code/analysis/codeql"
    payload = {
        "code": code
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 4. 코드 수정 테스트
def code_fix(code, analysis):
    url = f"{BASE_URL}/code/fix"
    payload = {
        "code": code,
        "analysis": analysis
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

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

# 1-2-4-2 파이프라인 : Detector 모델을 SKKU Dectector 모델로 사용
def pipeline1(model_id, prompt):
    result = code_generation(model_id, prompt)
    code = result['generated_code']
    
    result = code_analysis_model(code)
    vul_type = result['vulnerability_type']
    analysis = result['analysis']
    
    print("\n=== Summary ===")
    print("=== Code Generation Response ===")
    print("Generated Code:\n", code)
    print("=== Code Analysis Response (Model) ===")
    print("Vulnerability Type:", vul_type)
    print("Analysis:\n", analysis)
    if vul_type != "Safe":
        result = code_fix(code, analysis)
        code_fixed = result['fixed_code']
        
        print("=== Code Fix Response ===")
        print("Fixed Code:\n", code_fixed)
        result = code_analysis_model(code_fixed)  
        vul_type_fixed = result['vulnerability_type']
        analysis_fixed = result['analysis']
 
        print("=== Post-Fix Code Analysis Response (Model) ===")
        print("Vulnerability Type:", vul_type_fixed)
        print("Analysis:\n", analysis_fixed)
    else:
        print("No vulnerabilities found. No code fix needed.")

# 1-3-4-3 파이프라인 : Detector 모델을 CodeQL 모델로 사용
def pipeline2(model_id, prompt):
    result = code_generation(model_id, prompt)
    code = result['generated_code']
    
    result = code_analysis_codeql(code)
    vul_type = result['vulnerability_type']
    analysis = result['analysis']
    
    print("\n=== Summary ===")
    print("=== Code Generation Response ===")
    print("Generated Code:\n", code)
    print("=== Code Analysis Response (Model) ===")
    print("Vulnerability Type:", vul_type)
    print("Analysis:\n", analysis)
    if vul_type != "Safe":
        result = code_fix(code, analysis)
        code_fixed = result['fixed_code']
        
        print("=== Code Fix Response ===")
        print("Fixed Code:\n", code_fixed)
        result = code_analysis_codeql(code_fixed)
        vul_type_fixed = result['vulnerability_type']
        analysis_fixed = result['analysis']
 
        print("=== Post-Fix Code Analysis Response (Model) ===")
        print("Vulnerability Type:", vul_type_fixed)
        print("Analysis:\n", analysis_fixed)
    else:
        print("No vulnerabilities found. No code fix needed.")
        
if __name__ == "__main__":
    # valid scenario 1; 프롬프트 3인경우 CodeQL 모델이 더 잘잡음
    pipeline = pipeline2
    prompt = prompt3
    
    # valid scenario 2; 프롬프트 2인경우 SKKU 모델이 더 잘잡음
    # pipeline = pipeline1
    # prompt = prompt2
    
    # SKKU 모델 테스트
    print("=== SKKU Model Pipeline ===")
    pipeline(model_id='skku', prompt=prompt)
    
    print("\n\n")
    
    # GPT-4o 모델 테스트
    print("\n=== GPT-4o Model Pipeline ===")
    pipeline(model_id='gpt4o', prompt=prompt)   
