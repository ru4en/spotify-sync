FROM python:3.13

WORKDIR /app

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/
COPY ui /app/ui/

EXPOSE 8080

CMD ["python", "main.py", "api"]

