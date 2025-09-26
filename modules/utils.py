import re
from pathlib import Path

def save_file(code: str, filename: str):
    path = Path(filename)
    path.write_text(code + "\n", encoding="utf-8", newline="\n")
    print(f"saved to {filename}")

def read_code(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()
    return code
    
# 앞뒤의 ```cpp 또는 ``` 제거
def remove_cpp_codeblock(text: str) -> str:
    cleaned = re.sub(r"```cpp\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned)
    return cleaned.strip()

# 주어진 문자열에서 CWE 식별자(CWE-숫자)들을 찾아
# 'CWE-<정수>' 표준형으로 정규화하여 중복 없이 반환함.
# - 변형 허용: 'CWE-79', 'CWE 079', 'CWE-0079' 등    
def extract_cwe_ids(text: str) -> list[str]:    
    # CWE 다음에 하이픈 또는 공백, 이어서 1~5자리 숫자(선행 0 허용)
    pattern = re.compile(r'\bCWE[-\s]?0*(\d{1,5})\b', re.IGNORECASE)
    ids = [f"CWE-{m.group(1)}" for m in pattern.finditer(text)]
    # 입력 내 등장 순서를 유지하며 중복 제거
    seen = set()
    unique = []
    for cwe in ids:
        if cwe not in seen:
            seen.add(cwe)
            unique.append(cwe)
    return "\n".join(unique)

# def extract_cpp_code(text: str) -> str:
#     """
#     입력 문자열에서 C++/C 코드 블록만 추출하는 함수.
#     - Markdown 코드 블록 형식(````cpp ... `````)을 찾아 반환
#     """
#     m = re.findall(r"```(?:cpp|c\+\+)\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
#     if m:
#         return m[0].strip()
#     m = re.findall(r"```c\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
#     if m:
#         return m[0].strip()
#     return text.strip()