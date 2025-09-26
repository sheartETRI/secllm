# masker.py
from __future__ import annotations
from typing import Dict, Tuple, List
import re

from tree_sitter import Language, Parser
import tree_sitter_cpp as tscpp

# 간단 키워드 세트 (C/C++ 공용, 필요시 추가)
C_KEYWORDS = {
    "alignas","alignof","asm","auto","bool","break","case","catch","char","class","const","constexpr",
    "const_cast","continue","decltype","default","delete","do","double","dynamic_cast","else","enum",
    "explicit","export","extern","false","float","for","friend","goto","if","inline","int","long",
    "mutable","namespace","new","noexcept","operator","private","protected","public","register",
    "reinterpret_cast","return","short","signed","sizeof","static","static_assert","static_cast",
    "struct","switch","template","this","thread_local","throw","true","try","typedef","typeid",
    "typename","union","unsigned","using","virtual","void","volatile","wchar_t","while",
}

BUILTIN_FUNCS = {"printf", "scanf", "malloc", "free", "memcpy", "memset", "strlen", "strcpy"}
NAMESPACE_SKIP = {"std"}  # std::cout 같은 것 제외하고 싶을 때

STRING_NODE_TYPES = {
    # C/C++
    "string_literal", "char_literal",
    # JS/TS
    "string", "template_string", "template_substitution",
}
COMMENT_NODE_TYPES = {"comment"}
IDENT_NODE_TYPES = {"identifier"}

# ----- 공백 처리 유틸 -----
def _normalize_ws(text: str, mode: str) -> str:
    """
    mode:
      - 'all' : 모든 공백 제거(모델 입력용으로는 비추천)
      - 'newline_tab' : \n, \t -> ' ' 치환 후 다중 공백 1개로
      - 'normalize' : \n/\t -> ' ', 연속 공백 1개로 (권장)
    """
    if mode not in {"all", "newline_tab", "normalize"}:
        mode = "normalize"
    if mode == "all":
        return re.sub(r"\s+", "", text)
    t = text.replace("\n", " ").replace("\t", " ")
    t = re.sub(r"[ \r\f\v]+", " ", t)
    return t.strip()

# ----- 파서 준비 -----
def _load_language(lang: str):
    lang = lang.lower()
    if lang in ("c", "cpp", "c++"):
        return get_language("cpp")
    if lang in ("java",):
        return get_language("java")
    if lang in ("js","javascript","typescript","ts"):
        return get_language("javascript")
    return get_language("cpp")

def _collect_protected_spans(tree) -> List[Tuple[int,int]]:
    """문자열/문자 리터럴 구간(치환 금지) 수집"""
    spans = []
    cur = tree.walk().node
    stack = [cur]
    while stack:
        n = stack.pop()
        if n.type in STRING_NODE_TYPES:
            spans.append((n.start_byte, n.end_byte))
        for i in range(n.child_count-1, -1, -1):
            stack.append(n.children[i])
    return spans

def _is_within_protected(node, protected_spans: List[Tuple[int,int]]) -> bool:
    s, e = node.start_byte, node.end_byte
    for ps, pe in protected_spans:
        if not (e <= ps or pe <= s):
            return True
    return False

# ===== 식별자 분류 =====
def _is_function_callee(node) -> bool:
    # call_expression(function: ..., arguments: ...)
    p = node.parent
    if p and p.type == "call_expression":
        # field_name이 제공되면 확인
        fn = p.child_by_field_name("function")
        if fn is not None:
            return fn == node
        # 아니면 첫 자식이 callee인 경우가 대부분
        return (p.child_count > 0 and p.children[0] == node)
    return False

def _is_function_name_in_declarator(node) -> bool:
    """
    C/C++ 기준:
    - function_declarator(..., declarator: <여기>)
    - function_definition(declarator: <여기>)
    파라미터 식별자는 제외하고 declarator 체인 안의 최종 identifier만 함수명으로 인정
    """
    p = node.parent
    # pointer_declarator/parenthesized_declarator 등을 따라 위로
    cur = node
    while p and p.type not in ("function_declarator", "function_definition", "declaration"):
        cur = p
        p = p.parent

    if p and p.type == "function_declarator":
        decl = p.child_by_field_name("declarator")
        if not decl:
            return False
        return (decl.start_byte <= node.start_byte and node.end_byte <= decl.end_byte)

    if p and p.type == "function_definition":
        fd = p.child_by_field_name("declarator")
        if not fd:
            return False
        return (fd.start_byte <= node.start_byte and node.end_byte <= fd.end_byte)

    return False

def _classify_ident(node, text: str) -> str:
    """
    반환: "FUNC" | "VAR" | "SKIP"
    규칙:
      - 키워드/네임스페이스/빌트인 함수는 SKIP
      - 함수 정의/선언 이름 -> FUNC
      - 호출식 callee -> FUNC
      - 나머지 -> VAR
    """
    if text in C_KEYWORDS or text in BUILTIN_FUNCS or text in NAMESPACE_SKIP:
        return "SKIP"
    if _is_function_name_in_declarator(node):
        return "FUNC"
    if _is_function_callee(node):
        return "FUNC"
    return "VAR"

# ===== 소스 재구성 =====
def _rebuild_with_replacements(src_bytes: bytes,
                               drop_ranges: List[Tuple[int,int]],
                               replace_map: Dict[Tuple[int,int], bytes]) -> bytes:
    # drop_ranges: 삭제(주석) / replace_map: 치환(식별자)
    intervals: List[Tuple[int,int,bytes]] = []
    for s, e in drop_ranges:
        intervals.append((s, e, b""))
    for (s, e), rep in replace_map.items():
        intervals.append((s, e, rep))
    intervals.sort(key=lambda x: (x[0], x[1]))

    out = bytearray()
    cur = 0
    for s, e, rep in intervals:
        if s < cur:
            continue
        out.extend(src_bytes[cur:s])
        out.extend(rep)
        cur = e
    out.extend(src_bytes[cur:])
    return bytes(out)


def preprocess_and_mask(source_code: str,
                        language: str = "cpp",
                        remove_whitespace: str = "normalize"
                        ) -> Tuple[str, Dict[str,str]]:
    """
    1) 주석 제거
    2) Tree-sitter로 변수/함수명 마스킹(FUNC_k/VAR_k)
    3) 공백 처리(remove_whitespace)
    반환: (가공된 코드 문자열, 매핑 딕셔너리)
    """
    CPP_LANGUAGE = Language(tscpp.language())
    parser = Parser(CPP_LANGUAGE)

    src_bytes = source_code.encode("utf-8")
    tree = parser.parse(src_bytes)

    protected_spans = _collect_protected_spans(tree)

    drop_ranges: List[Tuple[int,int]] = []           # 주석 삭제 범위
    replace_map: Dict[Tuple[int,int], bytes] = {}   # (start,end) -> 대체 바이트
    id_map: Dict[str, str] = {}
    var_idx = 0
    func_idx = 0

    # DFS
    cursor = tree.walk()
    stack = [cursor.node]
    while stack:
        n = stack.pop()

        # 1) 주석 제거
        if n.type in COMMENT_NODE_TYPES:
            drop_ranges.append((n.start_byte, n.end_byte))
            continue

        # 2) 식별자 마스킹
        if n.type in IDENT_NODE_TYPES and not _is_within_protected(n, protected_spans):
            ident = src_bytes[n.start_byte:n.end_byte].decode("utf-8")

            cls = _classify_ident(n, ident)
            if cls == "SKIP":
                pass
            elif cls == "FUNC":
                if ident not in id_map:
                    id_map[ident] = f"FUNC_{func_idx}"
                    func_idx += 1
                replace_map[(n.start_byte, n.end_byte)] = id_map[ident].encode("utf-8")
            else:  # VAR
                if ident not in id_map:
                    id_map[ident] = f"VAR_{var_idx}"
                    var_idx += 1
                replace_map[(n.start_byte, n.end_byte)] = id_map[ident].encode("utf-8")

        # 자식 순회
        for i in range(n.child_count - 1, -1, -1):
            stack.append(n.children[i])

    # 3) 주석 삭제 + 식별자 치환 적용
    rebuilt = _rebuild_with_replacements(src_bytes, drop_ranges, replace_map).decode("utf-8")

    # 4) 공백 처리
    rebuilt = _normalize_ws(rebuilt, remove_whitespace)

    return rebuilt, id_map
