## download SKKU LLM model
python download_model.py

## extract SKKU Detector model
cd models
sh restore.sh

## execute uvicorn
uvicorn main:app --reload

## execute demo
python demo.py
