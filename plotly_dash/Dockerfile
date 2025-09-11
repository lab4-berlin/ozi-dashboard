FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dash_app.py .
COPY generate_static_graph.py .
CMD ["gunicorn", "dash_app:app", "-b", "0.0.0.0:8050", "--workers", "2"]
