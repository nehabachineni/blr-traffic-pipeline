#Dockerfile is inside the producer folder, Docker copies everything inside that folder into the container's /app


FROM python:3.10-slim

WORKDIR /app

# only requirements first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of code
COPY . ./producer/ 

CMD ["python", "-m", "producer.main"]
