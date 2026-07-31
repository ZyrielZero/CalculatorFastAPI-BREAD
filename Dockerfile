# 3.12-slim matches the interpreter CI tests against; the image previously
# ran 3.11 while tests validated 3.12.
FROM python:3.12-slim

WORKDIR /app

# Dependencies first: this layer only rebuilds when requirements.txt changes,
# so code edits don't trigger a full reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 0.0.0.0 is required inside a container; binding to localhost would make
# the app unreachable through Docker's port mapping.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]