FROM runpod/base:0.6.2-cuda12.1.0
WORKDIR /app
RUN pip install --no-cache-dir \
    "runpod>=1.7.0" \
    "torch>=2.2.0" \
    "transformers>=4.40.0"
COPY handler.py .
CMD ["python", "handler.py"]
