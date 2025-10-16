# Use an official Python runtime as a parent image
FROM python:3.13-slim

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
