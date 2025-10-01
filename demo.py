import requests
import json

#BASE_URL = "http://127.0.0.1:8000" # Local server
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

# 5. 파이프라인 테스트
# model_id: "gpt4o" or "skku"
# prompt: 생성할 코드에 대한 설명
def pipeline(model_id, prompt):
    url = f"{BASE_URL}/code/pipeline"
    payload = {
        "model_id": model_id,
        "prompt": prompt
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

# # 1-2-4-2 파이프라인 : Detector 모델을 SKKU Dectector 모델로 사용
# def pipeline1(model_id, prompt):
#     result = code_generation(model_id, prompt)
#     code = result['generated_code']
    
#     result = code_analysis_model(code)
#     vul_type = result['vulnerability_type']
#     analysis = result['analysis']
    
#     print("\n=== Summary ===")
#     print("=== Code Generation Response ===")
#     print("Generated Code:\n", code)
#     print("=== Code Analysis Response (Model) ===")
#     print("Vulnerability Type:", vul_type)
#     print("Analysis:\n", analysis)
#     if vul_type != "Safe":
#         result = code_fix(code, analysis)
#         code_fixed = result['fixed_code']
        
#         print("=== Code Fix Response ===")
#         print("Fixed Code:\n", code_fixed)
#         result = code_analysis_model(code_fixed)  
#         vul_type_fixed = result['vulnerability_type']
#         analysis_fixed = result['analysis']
 
#         print("=== Post-Fix Code Analysis Response (Model) ===")
#         print("Vulnerability Type:", vul_type_fixed)
#         print("Analysis:\n", analysis_fixed)
#     else:
#         print("No vulnerabilities found. No code fix needed.")

# # 1-3-4-3 파이프라인 : Detector 모델을 CodeQL 모델로 사용
# def pipeline2(model_id, prompt):
#     result = code_generation(model_id, prompt)
#     code = result['generated_code']
    
#     result = code_analysis_codeql(code)
#     vul_type = result['vulnerability_type']
#     analysis = result['analysis']
    
#     print("\n=== Summary ===")
#     print("=== Code Generation Response ===")
#     print("Generated Code:\n", code)
#     print("=== Code Analysis Response (Model) ===")
#     print("Vulnerability Type:", vul_type)
#     print("Analysis:\n", analysis)
#     if vul_type != "Safe":
#         result = code_fix(code, analysis)
#         code_fixed = result['fixed_code']
        
#         print("=== Code Fix Response ===")
#         print("Fixed Code:\n", code_fixed)
#         result = code_analysis_codeql(code_fixed)
#         vul_type_fixed = result['vulnerability_type']
#         analysis_fixed = result['analysis']
 
#         print("=== Post-Fix Code Analysis Response (Model) ===")
#         print("Vulnerability Type:", vul_type_fixed)
#         print("Analysis:\n", analysis_fixed)
#     else:
#         print("No vulnerabilities found. No code fix needed.")

def pipeline_func(model_id, prompt):
    result = pipeline(model_id, prompt)
    code = result['code']
    vul_type = result['vul_type']
    analysis = result['analysis']
    code_fixed = result['code_fixed']
    vul_type_fixed = result['vul_type_fixed']
    analysis_fixed = result['analysis_fixed']
    print("\n=== Summary ===")
    print("=== Code Generation Response ===")
    print("Generated Code:\n", code)
    print("=== Code Analysis Response (Model) ===")
    print("Vulnerability Type:", vul_type)
    print("Analysis:\n", analysis)
    if vul_type != "Safe":
        print("=== Code Fix Response ===")
        print("Fixed Code:\n", code_fixed)
        print("=== Post-Fix Code Analysis Response (Model) ===")
        print("Vulnerability Type:", vul_type_fixed)
        print("Analysis:\n", analysis_fixed)
        
def pipeline_stream_func(model_id, prompt):
    url = f"{BASE_URL}/code/pipeline/stream"
    payload = {
        "model_id": model_id,
        "prompt": prompt
    }
    response = requests.post(url, json=payload, stream=True)
    response.raise_for_status()
    
    print("\n=== Streaming Pipeline Response ===")
    for line in response.iter_lines():
        if line:
            item = json.loads(line)
            stage = item.get("stage")
            if stage == "generation":
                print("\n[Stage: Code Generation]")
                print("Generated Code:\n", item.get("code"))
            elif stage == "analysis":
                print("\n[Stage: Code Analysis]")
                print("Vulnerability Type:", item.get("vul_type"))
                print("Analysis:\n", item.get("analysis"))
            elif stage == "fix":
                print("\n[Stage: Code Fix]")
                print("Fixed Code:\n", item.get("code_fixed"))
            elif stage == "postfix_analysis":
                print("\n[Stage: Post-Fix Code Analysis]")
                print("Vulnerability Type:", item.get("vul_type_fixed"))
                print("Analysis:\n", item.get("analysis_fixed"))
            elif stage == "done":
                print("\n[Stage: Done]")
                print(item.get("message"))

def pipeline_generation_stream_func(model_id, prompt):
    url = f"{BASE_URL}/code/pipeline/generation_stream"
    payload = {
        "model_id": model_id,
        "prompt": prompt
    }
    response = requests.post(url, json=payload, stream=True)
    response.raise_for_status()
    
    code_value, vul_type_value, analysis_value = None, None, None
    
    print("\n=== Streaming Code Generation Pipeline Response ===")
    for line in response.iter_lines():
        if line:
            item = json.loads(line)
            stage = item.get("stage")
            if stage == "generation":
                code_value = item.get("code")
                print("\n[Stage: Code Generation]")
                print("Generated Code:\n", item.get("code"))
            elif stage == "analysis":
                vul_type_value = item.get("vul_type")
                analysis_value = item.get("analysis")
                print("\n[Stage: Code Analysis]")
                print("Vulnerability Type:", item.get("vul_type"))
                print("Analysis:\n", item.get("analysis"))
            elif stage == "done":
                print("\n[Stage: Done]")
                print(item.get("message"))
    return code_value, vul_type_value, analysis_value
                
def pipeline_fix_stream_func(code, analysis):
    url = f"{BASE_URL}/code/pipeline/fix_stream"
    payload = {
        "code": code,
        "analysis": analysis
    }
    response = requests.post(url, json=payload, stream=True)
    response.raise_for_status()
    
    code_fixed_value, vul_type_fixed_value, analysis_fixed_value = None, None, None
    
    print("\n=== Streaming Code Fix Pipeline Response ===")
    for line in response.iter_lines():
        if line:
            item = json.loads(line)
            stage = item.get("stage")
            if stage == "fix":
                code_fixed_value = item.get("code_fixed")
                print("\n[Stage: Code Fix]")
                print("Fixed Code:\n", item.get("code_fixed"))
            elif stage == "postfix_analysis":
                vul_type_fixed_value = item.get("vul_type_fixed")
                analysis_fixed_value = item.get("analysis_fixed")
                print("\n[Stage: Post-Fix Code Analysis]")
                print("Vulnerability Type:", item.get("vul_type_fixed"))
                print("Analysis:\n", item.get("analysis_fixed"))
            elif stage == "done":
                print("\n[Stage: Done]")
                print(item.get("message"))
    return code_fixed_value, vul_type_fixed_value, analysis_fixed_value

if __name__ == "__main__":   
    # valid scenario 1; 프롬프트 3인경우 CodeQL 모델이 더 잘잡음    
    prompt = prompt3
    
    # # SKKU 모델 테스트
    print("=== SKKU Model Pipeline ===")
    # pipeline_generation_stream_func(model_id='skku', prompt=prompt)
    
    print("\n\n")    
    # GPT-4o 모델 테스트
    print("\n=== GPT-4o Model Pipeline ===")
    code, vul_type, analysis = pipeline_generation_stream_func(model_id='gpt4o', prompt=prompt)
    # import pdb; pdb.set_trace()
    fixed_code, fixed_vul_type, fixed_analysis = pipeline_fix_stream_func(code, analysis)
