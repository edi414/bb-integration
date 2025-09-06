FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

RUN yum update -y && yum install -y git gcc gcc-c++ make

# Install essential pre-compiled packages first
RUN pip install --upgrade pip && \
    pip install numpy==1.26.4 pandas==2.3.1 && \
    pip install pydantic pydantic-settings && \
    pip install psycopg2-binary sqlalchemy && \
    pip install python-dotenv && \
    pip install langchain_openai langchain && \
    pip install cryptography requests

COPY requirements.txt .
# Install requirements but skip problematic packages
RUN pip install -r requirements.txt --no-deps || \
    pip install -r requirements.txt

COPY . ${LAMBDA_TASK_ROOT}

# Definir permissões corretas para os arquivos
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
