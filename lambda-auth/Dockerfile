FROM public.ecr.aws/lambda/python:3.13 as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /opt/python

FROM public.ecr.aws/lambda/python:3.13
COPY --from=builder /opt/python /opt/python
COPY src/ ${LAMBDA_TASK_ROOT}/src/
ENV PYTHONPATH ${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/src:/opt/python

CMD ["src.app.lambda_handler.lambda_handler"]