from fastapi import FastAPI
from pydantic import BaseModel
from service import code_generation, code_anaysis, code_fix

app = FastAPI(title="Code Service API")

# 요청 모델 정의
class GenerationRequest(BaseModel):
    model_id: str
    prompt: str

class AnalysisRequest(BaseModel):
    code: str

class FixRequest(BaseModel):
    code: str
    analysis: str


# 1. 코드 생성 API
@app.post("/code/generation")
def generate_code(req: GenerationRequest):
    result = code_generation(req.model_id, req.prompt)
    return {"generated_code": result}


# 2. 코드 분석 API
@app.post("/code/analysis")
def analyze_code(req: AnalysisRequest):
    vul_type, analysis = code_anaysis(req.code)
    return {"vulnerability_type": vul_type, "analysis": analysis}


# 3. 코드 수정 API
@app.post("/code/fix")
def fix_code(req: FixRequest):
    result = code_fix(req.code, req.analysis)
    return {"fixed_code": result}
