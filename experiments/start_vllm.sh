#!/bin/bash
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DIR/logs"
PY=${VLLM_PYTHON:?Set VLLM_PYTHON to the Python interpreter that has vLLM}
MODEL=${VLLM_MODEL:?Set VLLM_MODEL to the Qwen3-4B-Thinking-2507 checkpoint}
for i in 0 1 2 3 4 5 6 7; do
  CUDA_VISIBLE_DEVICES=$i nohup "$PY" -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --served-model-name qwen3-4b \
    --tensor-parallel-size 1 \
    --max-model-len 90112 \
    --max-num-batched-tokens 8192 \
    --gpu-memory-utilization 0.90 \
    --host 127.0.0.1 \
    --port $((8000 + i)) \
    --reasoning-parser qwen3 \
    --trust-remote-code \
    > "$DIR/logs/vllm-$i.log" 2>&1 &
  echo "gpu $i pid $! port $((8000 + i))"
done
