FROM public.ecr.aws/lambda/python:3.9

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir google-api-python-client

COPY lambda_function.py ${LAMBDA_TASK_ROOT}
CMD [ "lambda_function.lambda_handler" ]
