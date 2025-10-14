#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# 실행 명령어 (API Key 정보(Default Key 값은 사용 가능한 저의 API 키 값입니다.) + 코드 실행)
  python3 secure_rewriter_cpp.py --code test_code.cpp --cwe test_CWE.txt --out test_code_fixed.cpp
"""

import asyncio
import argparse
import os
import re
import sys
import json
import time
from difflib import unified_diff
from modules.utils import remove_cpp_codeblock

PREFERRED_LANGS = {"cpp", "c++", "cc", "cxx", "c"}

try:
    import openai
except ImportError:
    print("Please install openai: pip install openai", file=sys.stderr)
    raise

DEFAULT_MODEL = "gpt-4o"  # 모델 변경 가능
TEMPERATURE = 0
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  
MAX_TOKENS = 10000

API_KEY = ""  # export 과정이 불편할 경우, API Key를 코드 내부에 작성하여도 됩니다. (보안상 비추천)

env_key = os.getenv("OPENAI_API_KEY")
if env_key:
    openai.api_key = env_key
else:
    if API_KEY:
        openai.api_key = API_KEY

client = None
try:
    OpenAIClass = getattr(openai, "OpenAI", None)
    if OpenAIClass is not None:
        client_api_key = os.getenv("OPENAI_API_KEY") or (API_KEY if API_KEY else None)
        if client_api_key:
            client = OpenAIClass(api_key=client_api_key)
        else:
            client = OpenAIClass()
except Exception:
    client = None

def load_code(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def load_cwe_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

CWE_PATTERN = re.compile(
    r"(CWE[-\s]?(?P<id>\d{1,4}))"
    r"(?:[:\)\-\s]*"
    r"(?P<desc>[^@#\n\r\(]*?))?"
    r"(?:\(?line[s]?\s*(?P<line>\d{1,6})\)?)?",
    flags=re.IGNORECASE
)

def parse_cwe_text(txt: str):
    findings = []
    for m in CWE_PATTERN.finditer(txt):
        cwe_raw = m.group("id")
        if not cwe_raw:
            continue
        cwe_id = f"CWE-{cwe_raw.zfill(3)}" if len(cwe_raw) < 3 else f"CWE-{cwe_raw}"
        desc = (m.group("desc") or "").strip()
        line = m.group("line")
        try:
            line_num = int(line) if line else None
        except Exception:
            line_num = None
        entry = {"cwe_id": cwe_id, "description": desc or None, "line": line_num}
        if entry not in findings:
            findings.append(entry)
    return findings

def build_prompt(code: str, cwe_findings):
    if cwe_findings:
        cwe_summary_lines = []
        for f in cwe_findings:
            linepart = f" (line {f['line']})" if f.get("line") else ""
            descpart = f": {f['description']}" if f.get("description") else ""
            cwe_summary_lines.append(f"- {f['cwe_id']}{linepart}{descpart}")
        cwe_summary = "\n".join(cwe_summary_lines)
    else:
        cwe_summary = "No CWE entries detected in the provided CWE report file."

    system_prompt = (
        "You are a security-focused C/C++ developer assistant. "
        "Your job: given an original C++ source file and a list of CWE findings from a static analysis tool, "
        "produce a corrected, secure version of the code that preserves original functionality as much as possible. "
        "Fix the reported CWEs (e.g., add bounds checks, null checks, use safer library functions, check return values, "
        "avoid integer overflows, properly free resources, prevent format-string and buffer overflow issues, etc.). "
        "Be conservative: do not remove intended functionality. Keep the code style roughly similar. "
        "Return **only** the corrected code inside a single fenced code block with language tag, e.g. ```cpp ... ```."
    )

    user_prompt = (
        "Original code (start):\n\n"
        "```cpp\n"
        f"{code}\n"
        "```\n\n"
        "Static analysis CWE findings (start):\n\n"
        f"{cwe_summary}\n\n"
        "Instructions:\n"
        "1) Produce a corrected C++ source file that addresses the listed CWEs.\n"
        "2) Preserve original behavior and function names/ signatures unless a small change is required for safety — "
        "if you change a signature, keep the change minimal and mention why (but do not produce free text; only code allowed). \n"
        "3) Use defensive programming: check return values, validate sizes before memcpy/strcpy-like ops, add safe allocation checks, "
        "and free/close resources.\n"
        "4) Return only the fixed code inside one ```cpp ... ``` block with no extra commentary.\n"
    )
    return system_prompt, user_prompt

def call_gpt(system_prompt: str, user_prompt: str, model=DEFAULT_MODEL, temperature=TEMPERATURE):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if client is not None:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=MAX_TOKENS,
                )
                return resp
            else:
                resp = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=MAX_TOKENS,
                )
                return resp
        except Exception as e:
            wait = RETRY_BACKOFF ** attempt
            print(f"[WARN] GPT call failed (attempt {attempt}/{MAX_RETRIES}): {e}", file=sys.stderr)
            if attempt == MAX_RETRIES:
                raise
            print(f"[INFO] retrying in {wait:.1f}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("Exceeded max retries for GPT call")

def extract_code_from_response(resp_text: str):
    m = re.search(r"```(?:cpp|c\+\+)?\s*\n(.*?)```", resp_text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        code = m.group(1).rstrip() + "\n"
        return code
    if "int main" in resp_text or "#include" in resp_text:
        return resp_text
    return None

def simple_line_diff(original: str, fixed: str, original_path: str, fixed_path: str):
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    diff = list(unified_diff(orig_lines, fixed_lines, fromfile=original_path, tofile=fixed_path, lineterm=""))
    return diff

def secure_rewriter(code, cwe, model=DEFAULT_MODEL, temperature=TEMPERATURE):
    system_prompt, user_prompt = build_prompt(code, cwe)
    print("[INFO] Calling GPT model to rewrite code...")
    resp = call_gpt(system_prompt, user_prompt, model=model, temperature=temperature)
    text = None
    try:
        text = resp["choices"][0]["message"]["content"]
    except Exception:
        try:
            text = resp.choices[0].message.content
        except Exception:
            text = str(resp)

    fixed_code = extract_code_from_response(text)
    return fixed_code

def build_prompt_for_stream(code: str, cwe_findings):
    """
    build_prompt(...)와 동일한 시스템/유저 프롬프트를 반환.
    서비스 레이어에서 스트리밍 호출 시 이 함수를 사용.
    """
    # 이미 존재하는 빌더를 그대로 재사용합니다.
    return build_prompt(code, cwe_findings)  # 

async def stream_fixed_code_tokens(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = TEMPERATURE,
    debug_delay_sec: float = 0.0,
):
    """
    OpenAI 스트리밍 응답에서 ```cpp ... ``` 코드블록 내부 텍스트만 토큰 단위로 yield.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    # 1) 스트림 핸들 확보 (v1 클라이언트 또는 레거시)
    def _start_stream_sync():
        if client is not None:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=MAX_TOKENS,
                stream=True,
            )
        else:
            # 구버전 OpenAI SDK 대응
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=MAX_TOKENS,
                stream=True,
            )

    # 2) fence(코드블록) 상태 관리하면서 동기 이터레이터 소비
    fence_pattern = re.compile(r"```(?:cpp|c\+\+)?\s*$", re.IGNORECASE)

    # def _iter_code_tokens_sync():
    #     in_code_block = False
    #     fence_open_seen = False
    #     stream = _start_stream_sync()

    #     for ch in stream:
    #         # v1: ch.choices[0].delta.content, 구버전: ch["choices"][0]["delta"]["content"]
    #         content = None
    #         try:
    #             content = getattr(ch.choices[0].delta, "content", None)
    #         except Exception:
    #             try:
    #                 content = ch["choices"][0]["delta"].get("content")
    #             except Exception:
    #                 content = None

    #         if not content:
    #             continue

    #         lines = content.splitlines(keepends=True)
    #         out_buf = []
    #         for ln in lines:
    #             if not fence_open_seen:
    #                 if fence_pattern.match(ln.strip()):
    #                     fence_open_seen = True
    #                     in_code_block = True
    #                     # fence 라인은 방출하지 않음
    #                 # fence 전 텍스트는 무시
    #             else:
    #                 if fence_pattern.match(ln.strip()):
    #                     # 닫는 fence
    #                     in_code_block = False
    #                     # fence 라인은 방출하지 않음
    #                 else:
    #                     if in_code_block:
    #                         out_buf.append(ln)

    #         if out_buf:
    #             yield "".join(out_buf)

    #         # 닫는 fence까지 본 경우 종료
    #         if fence_open_seen and not in_code_block:
    #             break
    
    def _iter_code_tokens_sync():
        in_code_block = False
        fence_open_seen = False
        first_line_after_open = False  # ★ 추가: 여는 펜스 직후 첫 줄 여부
        stream = _start_stream_sync()

        for ch in stream:
            # v1 / legacy 호환 content 추출 (기존 그대로)
            content = None
            try:
                content = getattr(ch.choices[0].delta, "content", None)
            except Exception:
                try:
                    content = ch["choices"][0]["delta"].get("content")
                except Exception:
                    content = None
            if not content:
                continue

            lines = content.splitlines(keepends=True)
            out_buf = []
            for ln in lines:
                s = ln.strip()

                # 1) 아직 펜스를 못 봤을 때: 여는 펜스 라인 찾기
                if not fence_open_seen:
                    # 여는 펜스(`````, "```cpp") 모두 감지
                    if fence_pattern.match(s):           # ```  또는  ```cpp
                        fence_open_seen = True
                        in_code_block = True
                        first_line_after_open = True     # ★ 다음 줄만 언어 태그일 수 있음
                    # 펜스 전의 다른 텍스트는 무시
                    continue

                # 2) 펜스를 이미 본 상태
                # 2-1) 닫는 펜스면 종료
                if fence_pattern.match(s):               # ```  또는  ```cpp (닫힘)
                    in_code_block = False
                    # fence 라인은 방출하지 않음
                    continue

                # 2-2) 코드 본문 처리
                if in_code_block:
                    if first_line_after_open:
                        # ★ 여는 펜스 직후 한 줄이 'cpp', 'c++' 등 언어 태그로 따로 떨어져 온 경우 무시
                        if s.lower() in PREFERRED_LANGS:
                            first_line_after_open = False
                            continue
                        # 언어 태그가 아니면 정상 코드 → 그대로 진행
                        first_line_after_open = False

                    out_buf.append(ln)

            if out_buf:
                yield "".join(out_buf)

            # 닫는 펜스까지 보였다면 종료
            if fence_open_seen and not in_code_block:
                break

    # 3) 동기 이터레이터를 비동기 제너레이터로 래핑
    loop = asyncio.get_event_loop()
    for token_text in await loop.run_in_executor(None, lambda: list(_iter_code_tokens_sync())):
        if debug_delay_sec > 0:
            await asyncio.sleep(debug_delay_sec)
        yield token_text

async def secure_rewriter_stream(
    code: str,
    cwe_findings,
    model: str = DEFAULT_MODEL,
    temperature: float = TEMPERATURE,
    debug_delay_sec: float = 0.0,):
    """
    1) build_prompt_for_stream → 2) 토큰 스트리밍 → 3) 최종 고정 코드 반환
    사용법:
        assembled = []
        async for t in secure_rewriter_stream(...):
            if isinstance(t, dict) and t.get("stage") == "done":
                fixed_code = t["code"]
            else:
                token = t   # str
    """
    system_prompt, user_prompt = build_prompt_for_stream(code, cwe_findings)  # 

    assembled = []
    async for token in stream_fixed_code_tokens(
        system_prompt,
        user_prompt,
        model=model,
        temperature=temperature,
        debug_delay_sec=debug_delay_sec,
    ):
        assembled.append(token)
        # 서비스에서 바로 쓸 수 있도록 토큰을 그대로 yield
        yield token

    # fixed_code = "".join(assembled).rstrip() + "\n"
    fixed_code = remove_cpp_codeblock("".join(assembled))
    
    # 최종 한 번은 메타정보와 함께 전달
    yield {"stage": "done", "code": fixed_code}

def main_cli():
    parser = argparse.ArgumentParser(description="Rewrite C++ code securely using GPT (based on CWE report).")
    parser.add_argument("--code", "-c", required=True, help="Path to original .cpp file")
    parser.add_argument("--cwe", required=True, help="Path to CWE text file (.txt)")
    parser.add_argument("--out", "-o", default=None, help="Output fixed .cpp path (default: <orig>_fixed.cpp)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default {DEFAULT_MODEL})")
    parser.add_argument("--temp", type=float, default=TEMPERATURE, help="Sampling temperature (default 0.2)")
    args = parser.parse_args()

    effective_key = os.getenv("OPENAI_API_KEY") or (API_KEY if API_KEY else None) or getattr(openai, "api_key", None)
    if not effective_key:
        print("[ERROR] OpenAI API key not set. Set OPENAI_API_KEY env var or edit API_KEY in the script.", file=sys.stderr)
        sys.exit(1)

    code_path = args.code
    cwe_path = args.cwe
    model = args.model
    temperature = args.temp

    if not os.path.isfile(code_path):
        print(f"[ERROR] code file not found: {code_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(cwe_path):
        print(f"[ERROR] cwe file not found: {cwe_path}", file=sys.stderr)
        sys.exit(1)

    # import pdb; pdb.set_trace()
    original_code = load_code(code_path)
    cwe_txt = load_cwe_txt(cwe_path)
    cwe_findings = parse_cwe_text(cwe_txt)

    print(f"[INFO] Parsed {len(cwe_findings)} CWE finding(s) from {cwe_path}")
    for f in cwe_findings:
        print(f"  - {f['cwe_id']}" + (f" (line {f['line']})" if f['line'] else "") + (f": {f['description']}" if f['description'] else ""))

    system_prompt, user_prompt = build_prompt(original_code, cwe_findings)

    print("[INFO] Calling GPT model to rewrite code...")
    resp = call_gpt(system_prompt, user_prompt, model=model, temperature=temperature)

    text = None
    try:
        text = resp["choices"][0]["message"]["content"]
    except Exception:
        try:
            text = resp.choices[0].message.content
        except Exception:
            text = str(resp)

    fixed_code = extract_code_from_response(text)
    if fixed_code is None:
        print("[WARN] Couldn't extract code block from model response. Saving full response to file with .resp.txt suffix.", file=sys.stderr)
        resp_out_path = (args.out or (os.path.splitext(code_path)[0] + "_fixed.cpp")) + ".resp.txt"
        with open(resp_out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[INFO] Full response saved to {resp_out_path}", file=sys.stderr)
        sys.exit(2)

    out_path = args.out or (os.path.splitext(code_path)[0] + "_fixed.cpp")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fixed_code)

    print(f"[INFO] Fixed code written to {out_path}")

    diff = simple_line_diff(original_code, fixed_code, code_path, out_path)
    if not diff:
        print("[INFO] No textual differences detected between original and fixed (odd).")
    else:
        max_lines = 200
        print("\n".join(diff[:max_lines]))
        if len(diff) > max_lines:
            print(f"... (diff truncated, {len(diff)-max_lines} more lines) ...")

if __name__ == "__main__":
    main_cli()