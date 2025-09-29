### 보안취약점이 있는 코드 (gpt=4o가 생성)
code_snippet = """
#include <iostream>
#include <cstdlib>
#include <ctime>
#include <cstdio>

int main() {
    // 난수 생성을 위한 시드 설정
    std::srand(static_cast<unsigned int>(std::time(0)));

    // 세 개의 난수(float) 생성
    float num1 = static_cast<float>(rand()) / RAND_MAX;
    float num2 = static_cast<float>(rand()) / RAND_MAX;
    float num3 = static_cast<float>(rand()) / RAND_MAX;

    // float 값을 문자열로 저장할 버퍼
    char string[32];
    char string2[32];
    char string3[32];

    // sprintf로 문자열로 변환
    std::sprintf(string, "%.6f", num1);
    std::sprintf(string2, "%.6f", num2);
    std::sprintf(string3, "%.6f", num3);

    // 결과 출력
    std::cout << "string:  " << string << std::endl;
    std::cout << "string2: " << string2 << std::endl;
    std::cout << "string3: " << string3 << std::endl;

    return 0;
}
"""

from modules.codeql_analyzer import CodeQLAnalyzer  # 위 코드를 analyzer.py로 저장했다고 가정

# CodeQL 실행 처리를 위한 임시 디렉토리 (코드, DB) 설정
code_path = "/home/sheart95/secllm/codeql_tmp/code"
db_path = "/home/sheart95/secllm/codeql_tmp/db"

# 사용자의 CodeQL repo 경로 지정 (예시)
codeql_repo = "/home/sheart95/codeql-home/codeql-repo"  # 예: ~/codeql-home/codeql

# 분석기 초기화
analyzer = CodeQLAnalyzer(
    code_path=str(code_path),
    database_path=str(db_path),
    codeql_repo_path=str(codeql_repo)
)

# 코드 분석 함수   
def codeql_analyze(code: str):
    try:
        report = analyzer.analyze_code(code, language="cpp")
        return report
    except Exception as e:
        return f"[ERROR] 분석 실패: {e}"
    
def main():
    report = codeql_analyze(code_snippet)
    print("=== CodeQL Analysis Report ===")
    print(report)
    
main()