FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dash_app.py .
COPY generate_static_graph.py .
CMD ["python", "dash_app.py"]
