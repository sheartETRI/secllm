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

# 제어문자(탭/개행/CR 제외) 제거용
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

def _sanitize_cpp_text(s: str) -> str:
    # 1) 개행 정규화
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # 2) 제어문자 제거
    s = _CONTROL_CHARS_RE.sub("", s)
    # 3) 혹시 남은 백틱 라인 제거
    s = "\n".join(line for line in s.splitlines() if not line.strip().startswith("```"))
    # 4) 양끝 공백 정리 + 마지막 개행 보장
    return (s.strip() + "\n") if s.strip() else ""

def extract_fenced_code(text: str, preferred_langs=("cpp", "c++", "cc", "cxx", "c")) -> str:
    """
    마크다운 펜스 코드블록에서 코드만 추출하여 반환.
    `preferred_langs`에 해당하는 언어 태그가 있으면 그 블록을 우선 선택.
    없으면 첫 번째 블록을 선택. 블록이 없으면 원문 전체를 반환.
    """
    # ```lang\n ... \n```
    fence_re = re.compile(r"```(?P<lang>[A-Za-z0-9_+\-]*)[ \t]*\n(?P<code>.*?)(?:\n```|```$)", re.S)
    matches = list(fence_re.finditer(text))

    if matches:
        # 선호 언어 우선 선택
        pick = None
        for m in matches:
            lang = (m.group("lang") or "").lower()
            if lang in preferred_langs:
                pick = m
                break
        if pick is None:
            pick = matches[0]
        return _sanitize_cpp_text(pick.group("code"))

    # 펜스가 없으면, 혹시 섞인 백틱을 제거하고 정제
    return _sanitize_cpp_text(text)

def remove_cpp_codeblock(text: str) -> str:
    """
    하위호환용: 기존 함수명을 유지하되, 내부는 견고한 추출기로 대체.
    """
    return extract_fenced_code(text)

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