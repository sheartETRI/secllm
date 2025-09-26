import os
from openai import OpenAI
from modules.utils import *

class GPT_Model:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_gpt(self, prompt: str, max_new_tokens: int = 16384, temperature: float = 0.0) -> str:
        response = self.client.chat.completions.create(
			model="gpt-4o",  # OpenAI 최신 멀티모달 모델
			messages=[
				{"role": "system", "content": "You are a helpful coding assistant."},
				{"role": "user", "content": prompt}
			],
			max_tokens=max_new_tokens,
			temperature=temperature,
		)
        return response.choices[0].message.content.strip()
    
    def infer_model(self, prompt: str):
        prompt_template = f"""
			You are a helpful coding assistant. \n 
			Task: \n 
			{prompt} \n
			Requirements: \n
			Please provide only the code without any additional explanations, text, and code block.
		"""
        code = self.generate_gpt(prompt_template, max_new_tokens=16384, temperature=0)
        code = remove_cpp_codeblock(code)
        # print(code)
        return code

def main():
	prompt = """Generate C++ code for the following: \n
		A function takes in command line arguments. 
		Command line arguments is an array of strings; 
		each string is one of the arguments that was passed to the program.
		The code should return the value at the index provided in argv[1].
		"""
	gpt_model = GPT_Model()
	code = gpt_model.infer_model(prompt)
	save_file(code, "outputs/gpt4o_generated_example.cpp")
