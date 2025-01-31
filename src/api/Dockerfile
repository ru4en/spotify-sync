FROM python:3.13 AS production

WORKDIR /app

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

# Install the dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY . /app/

# Run the fastapi server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]