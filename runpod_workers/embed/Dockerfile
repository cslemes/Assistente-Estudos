FROM runpod/base:0.6.2-cuda12.1.0
WORKDIR /app
RUN pip install --no-cache-dir \
    "runpod>=1.7.0" \
    "fastembed-gpu>=0.8.0" \
    "onnxruntime-gpu>=1.25.0"
COPY handler.py .
CMD ["python", "handler.py"]
