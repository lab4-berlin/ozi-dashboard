# Use an official Python runtime as a parent image
FROM python:3-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce layer size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the etl directory content into the container at /app/etl
COPY . /app/etl/

RUN mkdir -p /app/etl/logs

# Ensure the run script within etl is executable (if it's used by the python code)
# Although our primary CMD is different, this maintains its executable state if needed.
RUN chmod +x /app/etl/run.sh

# The main command to run the application
# The specific job YAML file (e.g., etl/jobs/load_asns_report_May25.yaml)
# will need to be appended as an argument when running the container.
ENTRYPOINT ["python3", "./etl/main.py", "-t", "ASNS", "-c", "LT", "-df", "2023-01-01", "-dt", "2023-02-01", "-dr", "D"]
