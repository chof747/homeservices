FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
RUN mkdir -p /data/models

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]