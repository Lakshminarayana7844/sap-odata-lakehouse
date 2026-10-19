FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Run the mock service, ingest all entity sets into ./lakehouse, then show the silver tables.
CMD ["sh", "scripts/run_demo.sh"]
