import subprocess
import sys
import re
import os

def run_command(command_args):
    """Helper to run shell commands and return output."""
    process = subprocess.run(
        command_args,
        capture_output=True,
        text=True,
        check=False
    )
    if process.returncode != 0:
        print(f"Command failed: {' '.join(command_args)}", file=sys.stderr)
        print(f"Stdout: {process.stdout}", file=sys.stderr)
        print(f"Stderr: {process.stderr}", file=sys.stderr)
    return process.stdout, process.stderr, process.returncode

def main():
    # Step 1: Get date range from get_stats_1d_date_range.py
    print("Running etl/get_stats_1d_date_range.py to determine date range...")
    date_range_output, stderr, returncode = run_command(["python3", "etl/get_stats_1d_date_range.py"])

    if returncode != 0:
        print("Error getting date range. Exiting.", file=sys.stderr)
        sys.exit(1)

    if "Nothing to do" in date_range_output:
        print("No new data to process. Exiting ETL.")
        sys.exit(0)

    # Step 2: Extract date arguments
    match = re.search(r"--date-from \S+ --date-to \S+", date_range_output)
    if not match:
        print("Could not extract date arguments from get_stats_1d_date_range.py output. Exiting.", file=sys.stderr)
        sys.exit(1)

    date_args_str = match.group(0)
    date_args = date_args_str.split()
    print(f"Running ETL job with parameters: {date_args_str}")

    # Step 3: Run the main ETL job
    etl_command_args = ["python3", "etl/main.py", "-t", "STATS_1D", "-c", "all"] + date_args + ["-dr", "D"]
    print(f"Executing: {' '.join(etl_command_args)}")
    stdout, stderr, returncode = run_command(etl_command_args)

    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    if returncode != 0:
        print("ETL job failed. Exiting.", file=sys.stderr)
        sys.exit(1)
    else:
        print("ETL job completed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
