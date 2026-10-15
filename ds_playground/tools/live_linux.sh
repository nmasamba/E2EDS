#!/bin/sh
# Inside the verify-linux container, as the unprivileged user: build llama-server b11104 once from the
# read-only checkout at /llama into the /build volume (CPU only; the owner's 2026-10-15 approval), then
# run the live_model tests against the model mounted read-only at /models.
set -e
if [ ! -x /build/bin/llama-server ]; then
  cmake -S /llama -B /build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=OFF \
    -DGGML_CPU_ARM_ARCH=armv8.2-a+fp16+dotprod -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_TOOLS=ON -DLLAMA_BUILD_SERVER=ON -DGGML_METAL=OFF > /tmp/cmake.log 2>&1
  cmake --build /build --target llama-server -j "$(nproc)" > /tmp/build.log 2>&1
fi
/build/bin/llama-server --version 2>&1 | tail -2
DSP_LLAMA_SERVER=/build/bin/llama-server DSP_LIVE_MODEL_DIR=/models uv run pytest -m live_model
