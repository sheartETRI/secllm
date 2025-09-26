from modules.utils import *
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download
import os

def apply_template(tokenizer, prompt_text: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt_text}],
        tokenize=False,
        add_generation_prompt=True,
    )

@torch.inference_mode()
def generate_one(model, tokenizer, prompt_text: str, max_input_len=1536, max_new_tokens=512) -> str:
    """
    입력 받은 프롬프트에 대해 코드 생성하는 함수
    """
    templated = apply_template(tokenizer, prompt_text)

    inputs = tokenizer(
        templated,
        return_tensors="pt",
        padding=False,
        truncation=True,
        max_length=max_input_len,
    )

    for k in inputs:
        inputs[k] = inputs[k].to(model.device)

    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,

        do_sample=False,
        num_beams=1,
        temperature=0.0,
        top_p=1.0,
        top_k=0,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,

        use_cache=True,
        return_dict_in_generate=True,
    )

    input_len = inputs["input_ids"].shape[1]
    gen_ids = out.sequences[0][input_len:]
    return tokenizer.decode(gen_ids, skip_special_tokens=True)

def download_hfmodel1():
    REPO_ID   = "ChaeSJ/llama-3.1-8b-finetuned"
    SUBFOLDER = "llama_3_1_8b_finetuned"    
    # 로컬에 저장할 경로
    SAVE_DIR = "models/llama-3.1-8b-finetuned"
    os.makedirs(SAVE_DIR, exist_ok=True)
    # 1) 허깅페이스에서 토크나이저/모델 로드
    tokenizer = AutoTokenizer.from_pretrained(
        REPO_ID,
        subfolder=SUBFOLDER,
        use_fast=True,
        padding_side="right",
    )
    model = AutoModelForCausalLM.from_pretrained(
        REPO_ID,
        subfolder=SUBFOLDER,
        torch_dtype="auto",   # GPU 있으면 bfloat16 또는 float16 추천
    )
    # 2) pad_token 보정 (필요 시)
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({"pad_token": tokenizer.eos_token})
    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.pad_token_id
    # 3) 로컬 저장
    tokenizer.save_pretrained(SAVE_DIR)
    model.save_pretrained(SAVE_DIR)
    print(f">> 모델과 토크나이저가 {SAVE_DIR} 에 저장되었습니다.")

def download_hfmodel2():
    REPO_ID   = "ChaeSJ/llama-3.1-8b-finetuned"
    SUBFOLDER = "llama_3_1_8b_finetuned"    
    # 로컬에 저장할 경로
    SAVE_DIR = "models/llama-3.1-8b-finetuned"
    os.makedirs(SAVE_DIR, exist_ok=True)
    # 1) 허깅페이스에서 토크나이저/모델 로드
    snapshot_download(
        repo_id=REPO_ID,
        subfolder=SUBFOLDER,
        local_dir=SAVE_DIR,
        local_dir_use_symlinks=False,  # 심볼릭 링크 대신 실제 파일 복사
        ignore_patterns=["*.lock", "*.json.*", "README.md", "config.json", "generation_config.json"]
    )
    print(f">> 모델과 토크나이저가 {SAVE_DIR} 에 저장되었습니다.")
    
class SKKU_Model:
    def __init__(self, local_dir: str = None):
        self.model = None
        self.tokenizer = None
        self.local_dir = local_dir
        self.load_model()
            
    def load_model(self):
        self.model = AutoModelForCausalLM.from_pretrained(
			self.local_dir,
			torch_dtype=torch.bfloat16,
			device_map="auto",
			low_cpu_mem_usage=True,
		)
        self.tokenizer = AutoTokenizer.from_pretrained(
			self.local_dir,              # 로컬 절대경로
			use_fast=True,
			padding_side="right",
		)
        return self.model, self.tokenizer
    
    def infer_model(self, prompt: str):
        code = generate_one(self.model, self.tokenizer, prompt, max_input_len=1536, max_new_tokens=512)
        # print(code)
        return code
        
def main():
	prompt = """Generate C++ code for the following: \n
	A function takes in command line arguments. 
	Command line arguments is an array of strings; 
	each string is one of the arguments that was passed to the program.
	The code should return the value at the index provided in argv[1].
	"""  
	# # 실제 로드할 디렉터리(서브폴더까지 포함)
	local_dir = "./models/llama-3.1-8b-finetuned"
	skku_model = SKKU_Model(local_dir)
	skku_model.load_model()
	code = skku_model.infer_model(prompt)
	save_file(code, "outputs/skku_generated_example.cpp")


