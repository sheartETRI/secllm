from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
from service import (code_generation, model_code_analysis, codeql_code_analysis, code_fix, pipeline)
from service import pipeline_stream
import json

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
    
class PipelineRequest(BaseModel):
    model_id: str
    prompt: str
    model_config = {
        "protected_namespaces": ()
    }

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


# 4. 파이프라인 API
@app.post("/code/pipeline")
async def run_pipeline(req: PipelineRequest):
    try:
        code, vul_type, analysis, code_fixed, vul_type_fixed, analysis_fixed = await run_in_thread(pipeline, req.model_id, req.prompt)
        return {"code": code, "vul_type": vul_type, "analysis": analysis, "code_fixed": code_fixed, "vul_type_fixed": vul_type_fixed, "analysis_fixed": analysis_fixed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# 5. 스트리밍 파이프라인 API
@app.post("/code/pipeline/stream")
async def run_pipeline_stream(req: PipelineRequest):
    async def event_generator():
        async for item in pipeline_stream(req.model_id, req.prompt):
            yield json.dumps(item) + "\n"   # 줄바꿈으로 chunk 구분
    return StreamingResponse(event_generator(), media_type="application/json")
