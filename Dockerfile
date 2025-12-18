FROM public.ecr.aws/lambda/python:3.11

RUN yum update -y && yum install -y git gcc gcc-c++ make && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    yum clean all

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.26.4 pandas==2.3.1 && \
    pip install --no-cache-dir -r requirements.txt

COPY lambda_function.py ./
COPY main.py ./
COPY handlers/ ./handlers/
COPY services/ ./services/
COPY utils/ ./utils/
COPY data/ ./data/

RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
