import requests

#BASE_URL = "http://127.0.0.1:8000"
BASE_URL = "http://129.254.222.37:8001"

# 1. 코드 생성 테스트
def test_code_generation():
    url = f"{BASE_URL}/code/generation"
    payload = {
        "model_id": "skku", #"gpt4o",
        "prompt": "Generate a simple Python function that adds two numbers."
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 2. 모델 기반 코드 분석 테스트
def test_code_analysis_model():
    url = f"{BASE_URL}/code/analysis/model"
    payload = {
        "code": "int main() { char buf[10]; gets(buf); }"
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 3. CodeQL 기반 코드 분석 테스트 (추가)
def test_code_analysis_codeql():
    url = f"{BASE_URL}/code/analysis/codeql"
    payload = {
        "code": """#include <cstdio>
        int main() { 
        char buf[10]; 
        fgets(buf, sizeof(buf), stdin); 
        return 0;
        }
        """
    }
    # Failure case example
    # payload = {
    #     "code": "int main() { char buf[10]; gets(buf); }"
    # }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 4. 코드 수정 테스트
def test_code_fix():
    url = f"{BASE_URL}/code/fix"
    payload = {
        "code": "int main() { char buf[10]; gets(buf); }",
        "analysis": "Buffer overflow due to unsafe gets() usage (CWE-242)."
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    # 1. 코드 생성
    result = test_code_generation()
    code = result.get("generated_code", "")

    # 2. 모델 기반 분석
    result = test_code_analysis_model()
    vul_type = result.get("vulnerability_type", "")
    analysis = result.get("analysis", "")

    # 3. CodeQL 분석
    result = test_code_analysis_codeql()
    vul_type = result.get("vulnerability_type", "")
    codeql_report = result.get("analysis", "")

    # 4. 코드 수정
    result = test_code_fix()
    fixed_code = result.get("fixed_code", "")

    # 결과 출력
    print("\n=== Summary ===")
    print("=== Code Generation Response ===")
    print("Generated Code:\n", code)
    print("=== Code Analysis Response (Model) ===")
    print("Vulnerability Type:", vul_type)
    print("Analysis:\n", analysis)
    print("=== Code Analysis Response (CodeQL) ===")
    print("Vulnerability Type:", vul_type)
    print("CodeQL Report:\n", codeql_report)
    print("=== Code Fix Response ===")
    print("Fixed Code:\n", fixed_code)
