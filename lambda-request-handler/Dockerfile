FROM python:3.13-slim as builder

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /app/dependencies

FROM public.ecr.aws/lambda/python:3.13
COPY --from=builder /app/dependencies /opt/python
COPY src/ ${LAMBDA_TASK_ROOT}/src/
ENV PYTHONPATH ${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/src:/opt/python

CMD ["src.app.lambda_handler.lambda_handler"]