from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from service import (code_generation, model_code_analysis, codeql_code_analysis, code_fix)

app = FastAPI(title="Code Service API")
    
# 요청 모델 정의
class GenerationRequest(BaseModel):
    model_id: str
    prompt: str
    model_config = {
        "protected_namespaces": ()
    }

class AnalysisRequest(BaseModel):
    code: str

class FixRequest(BaseModel):
    code: str
    analysis: str

# 블로킹 함수 비동기 실행 helper
async def run_in_thread(func, *args):
    return await asyncio.to_thread(func, *args)

# 1. 코드 생성 API
@app.post("/code/generation")
async def generate_code(req: GenerationRequest):
    try:
        result = await run_in_thread(code_generation, req.model_id, req.prompt)
        return {"generated_code": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2.1 모델 코드 분석 API
@app.post("/code/analysis/model")
async def analyze_code_model(req: AnalysisRequest):
    try:
        vul_type, analysis = await run_in_thread(model_code_analysis, req.code)
        return {"vulnerability_type": vul_type, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2.2 CodeQL 코드 분석 API
@app.post("/code/analysis/codeql")
async def analyze_code_codeql(req: AnalysisRequest):
    try:
        vul_type, report = await run_in_thread(codeql_code_analysis, req.code)
        return {"vulnerability_type": vul_type, "analysis": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 코드 수정 API
@app.post("/code/fix")
async def fix_code(req: FixRequest):
    try:
        result = await run_in_thread(code_fix, req.code, req.analysis)
        return {"fixed_code": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
