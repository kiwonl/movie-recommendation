FROM python:3.12-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
COPY . ./
CMD ["python", "main.py"]
