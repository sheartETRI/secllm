import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. 코드 생성 테스트
def test_code_generation():
    url = f"{BASE_URL}/code/generation"
    payload = {
        "model_id": "gpt4o",
        "prompt": "Generate a simple Python function that adds two numbers."
    }
    response = requests.post(url, json=payload)
 
    # print(response.json())
    return response.json()


# 2. 코드 분석 테스트
def test_code_analysis():
    url = f"{BASE_URL}/code/analysis"
    payload = {
        "code": "int main() { char buf[10]; gets(buf); }"
    }
    response = requests.post(url, json=payload)

    # print(response.json())
    return response.json()


# 3. 코드 수정 테스트
def test_code_fix():
    url = f"{BASE_URL}/code/fix"
    payload = {
        "code": "int main() { char buf[10]; gets(buf); }",
        "analysis": "Buffer overflow due to unsafe gets() usage (CWE-242)."
    }
    response = requests.post(url, json=payload)

    # print(response.json())
    return response.json()


if __name__ == "__main__":
    result = test_code_generation()
    code = result.get("generated_code", "")
    
    result = test_code_analysis()
    vul_type = result.get("vulnerability_type", "")
    analysis = result.get("analysis", "")
    
    result = test_code_fix()
    fixed_code = result.get("fixed_code", "")
    
    print("\n=== Summary ===")
    print("=== Code Generation Response ===")
    print("Generated Code:\n", code)
    print("=== Code Analysis Response ===")
    print("Vulnerability Type:", vul_type)
    print("Analysis:\n", analysis)
    print("=== Code Fix Response ===")
    print("Fixed Code:\n", fixed_code)
