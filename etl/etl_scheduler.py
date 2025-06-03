import subprocess
import threading
import queue
import time
from datetime import datetime
import yaml
import os
import sys

MAX_PARALLEL_JOBS = 250
LOGS_DIR = "logs"
SCHEDULER_LOG = "etl_scheduler.log"


class Logger:
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log_file = log_file

    def write(self, message):
        self.terminal.write(message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(message)

    def flush(self):
        self.terminal.flush()


def setup_logging():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    log_path = os.path.join(LOGS_DIR, SCHEDULER_LOG)
    sys.stdout = Logger(log_path)


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}\n")


def ensure_logs_dir():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)


def load_config(config_file):
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def save_config(config_file, config):
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def build_command(task):
    cmd_parts = ["python3 main.py"]
    # New structure doesn't have params wrapper
    for name, value in task.items():
        if name == "task":
            cmd_parts.append(f"--{name} {value}")
        elif isinstance(value, list):
            cmd_parts.append(f"--{name} {' '.join(value)}")
        else:
            cmd_parts.append(f"--{name} {value}")
    return " ".join(cmd_parts)


def worker(job_id, task_queue, config, config_file):
    while True:
        try:
            task = task_queue.get(block=False)
        except queue.Empty:
            break

        # Get process ID
        process_id = os.getpid()

        # Extract task parameters
        task_code = task.get("task", "unknown")
        countries = "-".join(task.get("countries", []))
        date_from = task.get("date-from", "").replace("-", "")
        date_to = task.get("date-to", "").replace("-", "")
        resolution = task.get("date-resolution", "")

        # Create log filename with the new pattern
        log_filename = f"{process_id}_{task_code}_{countries}_{date_from}_{date_to}_{resolution}.log"
        log_file = os.path.join(LOGS_DIR, log_filename)

        command = build_command(task)
        task_name = task_code
        log_message(f"Process {job_id} starting task: {task_name}")

        done_task = task.copy()
        done_task.update({"started": datetime.now().isoformat(), "command": command})

        try:
            with open(log_file, "w") as out:
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                )

            done_task["finished"] = datetime.now().isoformat()
            done_task["status"] = "completed" if result.returncode == 0 else "failed"
            status_msg = (
                "✓ completed"
                if result.returncode == 0
                else f"✗ failed (code {result.returncode})"
            )
            log_message(f"Process {job_id} finished task: {task_name} - {status_msg}")

            if "TASKS_QUEUE" in config and task in config["TASKS_QUEUE"]:
                config["TASKS_QUEUE"].remove(task)
                if "TASKS_DONE" not in config:
                    config["TASKS_DONE"] = []
                config["TASKS_DONE"].append(done_task)
                save_config(config_file, config)

        except Exception as e:
            done_task["finished"] = datetime.now().isoformat()
            done_task["status"] = "failed"
            done_task["error"] = str(e)
            log_message(f"Process {job_id} error in task {task_name}: {str(e)}")

            if "TASKS_QUEUE" in config and task in config["TASKS_QUEUE"]:
                config["TASKS_QUEUE"].remove(task)
                if "TASKS_DONE" not in config:
                    config["TASKS_DONE"] = []
                config["TASKS_DONE"].append(done_task)
                save_config(config_file, config)

        finally:
            task_queue.task_done()


def main():
    if len(sys.argv) != 2:
        print("Usage: python etl_scheduler.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit(1)

    setup_logging()
    log_message(f"Starting ETL task scheduler using config: {config_file}")
    ensure_logs_dir()
    config = load_config(config_file)

    if "TASKS_QUEUE" not in config or not config["TASKS_QUEUE"]:
        log_message("No tasks found in the TASKS_QUEUE section")
        return

    total_tasks = len(config["TASKS_QUEUE"])
    log_message(f"Found {total_tasks} tasks to process")

    task_queue = queue.Queue()
    for task in config["TASKS_QUEUE"]:
        task_queue.put(task)

    threads = []
    thread_count = min(MAX_PARALLEL_JOBS, task_queue.qsize())
    log_message(f"Starting {thread_count} worker threads")

    for i in range(thread_count):
        t = threading.Thread(
            target=worker, args=(i + 1, task_queue, config, config_file)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    log_message("All tasks completed.")


if __name__ == "__main__":
    main()
