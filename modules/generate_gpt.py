import os
from openai import OpenAI
from modules.utils import *

# 추가: 토큰 스트리밍용 비동기 제너레이터
import asyncio
from typing import AsyncGenerator

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
    
    async def infer_model_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        prompt_template = f"""
            You are a helpful coding assistant. 
            Task:
            {prompt}
            Requirements:
            Please provide only the code without any additional explanations, text, and code block.
        """

        # OpenAI Python SDK (chat.completions) 스트리밍
        # SDK 버전에 따라 사용법이 약간 다릅니다. 아래 패턴은 호환성이 높은 예시입니다.
        stream = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful coding assistant."},
                {"role": "user", "content": prompt_template},
            ],
            stream=True,
            max_tokens=16384,
            temperature=0.0,
        )

        # SDK가 동기 이터레이터를 반환하는 경우, 스레드 풀로 감싸 비동기화
        loop = asyncio.get_event_loop()
        for chunk in await loop.run_in_executor(None, lambda: list(stream)):
            delta = getattr(chunk.choices[0], "delta", None) or getattr(chunk.choices[0], "message", None)
            content = getattr(delta, "content", None)
            if content:
                # 코드 블록 마커 제거는 마지막에 일괄 처리해도 되지만,
                # 토큰 단위에서는 그대로 흘려보내고 최종 조합 시 후처리 권장
                yield content

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
