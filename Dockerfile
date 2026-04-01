ARG PYTHON_IMAGE_VERSION=python:3.9-alpine
FROM ${PYTHON_IMAGE_VERSION}

RUN pip3 install pip --upgrade

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT ["python3", "-u", "/app/main.py"]
