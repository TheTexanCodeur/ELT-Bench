
# Minimal Dockerfile for SoT agent
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent
COPY . /app

ENV PYTHONUNBUFFERED=1

# Expect creds to be mounted into data/inputs/<problem>/snowflake_credential.json
CMD ["python", "run.py", "--example_index", "0-4"]
