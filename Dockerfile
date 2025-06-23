FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

COPY prompt_template.txt .

RUN echo "Hello World" > /app/README.md

COPY -r sample-app/ .

CMD ["python", "main.py"]