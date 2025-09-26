from modules.generate_gpt import GPT_Model
from modules.generate_skku import SKKU_Model
from modules.secure_rewriter_cpp import secure_rewriter, parse_cwe_text
from modules.single_code_inference import (SingleCodeDetector, analyze_code)
from modules.utils import *

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

# 2. 코드 분석
def code_anaysis(code: str):
    vul_type, analysis = analyze_code(detector, code)
    print(analysis)
    return vul_type, analysis

# 3. 코드 수정
def code_fix(code: str, analysis: str):
    analysis_cwe_extract = extract_cwe_ids(analysis) 
    cwe_findings = parse_cwe_text(analysis_cwe_extract)
    fixed_code = secure_rewriter(code, cwe_findings)
    print('fixed_code:\n', fixed_code)
    return fixed_code

# prompt = """Generate C++ code for the following: \n
# 	The code calls the getMonthlySales function 12 times; once for each month of the year.
# 	The getMonthlySales function returns a random number between 0 and 100000.
# 	The code adds up the sales for each quarter and prints the results.
# 	"""

# model_id = 'gpt4o'
# # model_id = 'skku'
# code = code_generation(model_id, prompt)
# vul_type, analysis = code_anaysis(code)
# code_fixed = code_fix(code, analysis)