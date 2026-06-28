FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Create artifacts dir
RUN mkdir -p artifacts

# Default command: run the CLI ranker
CMD ["python", "rank.py", \
     "--candidates", "/app/data/candidates.jsonl.gz", \
     "--job", "/app/data/job_description.docx", \
     "--out", "/app/data/submission.csv"]
