#!/bin/bash
# restore_checkpoint.sh
# 분할된 checkpoint 파일을 합치고 압축을 해제하는 스크립트

# 1. 분할된 파일을 합쳐서 checkpoint.tar.gz 생성
echo "[INFO] 분할된 파일을 합치는 중..."
cat checkpoints.tgz.part.* > checkpoints.tgz

# 2. 압축 해제
echo "[INFO] 압축을 해제하는 중..."
tar -xzvf checkpoints.tgz

# 3. 기존 분할된 파일 및 압축 파일 삭제
rm -f checkpoints.tgz*

# 4. 완료 메시지
echo "[INFO] 복원이 완료되었습니다!"
