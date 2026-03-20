import subprocess
import sys
import re
import os
from datetime import datetime, timedelta

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
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date()
    yesterday = today - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    date_args = ["--date-from", date_str, "--date-to", date_str]

    # Step 1: Run STATS_1D for all countries (incremental from last DB date)
    print("Running STATS_1D ETL job...")
    stats_output, stderr, returncode = run_command(
        ["python3", "etl/get_stats_1d_date_range.py"]
    )
    if returncode == 0 and "Nothing to do" not in stats_output:
        match = re.search(r"--date-from \S+ --date-to \S+", stats_output)
        if match:
            stats_date_args = match.group(0).split()
            etl_command = ["python3", "etl/main.py", "-t", "STATS_1D", "-c", "all"] + stats_date_args + ["-dr", "D"]
            print(f"Executing: {' '.join(etl_command)}")
            stdout, stderr, returncode = run_command(etl_command)
            print(stdout)
            if returncode != 0:
                print("STATS_1D ETL job failed.", file=sys.stderr)
                sys.exit(1)
    else:
        print("No new STATS_1D data to process (or error).")

    # Step 2: Run ASN_NEIGHBOURS for all countries (daily, yesterday's date)
    print("Running ASN_NEIGHBOURS ETL job for all countries...")
    etl_command = ["python3", "etl/main.py", "-t", "ASN_NEIGHBOURS", "-c", "all"] + date_args + ["-dr", "D"]
    print(f"Executing: {' '.join(etl_command)}")
    stdout, stderr, returncode = run_command(etl_command)
    print(stdout)
    if returncode != 0:
        print("ASN_NEIGHBOURS ETL job failed.", file=sys.stderr)
        sys.exit(1)

    print("ETL jobs completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
