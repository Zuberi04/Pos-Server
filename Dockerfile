FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt . 

RUN pip install --upgrade pip

RUN --mount=type=cache,target=/root/.cache/pip \
pip install --default-timeout=1000 -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]