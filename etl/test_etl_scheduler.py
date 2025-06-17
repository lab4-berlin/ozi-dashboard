import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import io
from datetime import datetime

# Functions, classes, and constants to test
from etl.etl_scheduler import (
    build_command,
    Logger,
    setup_logging,
    log_message,
    LOGS_DIR,  # For verifying paths
    SCHEDULER_LOG,  # For verifying paths
)


class TestLogger(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_logger_writes_to_stdout_and_file(self, mock_stdout, mock_file_open):
        log_file_path = "test_specific_log.log"
        logger = Logger(log_file_path)

        test_message = "Hello, Logger!"
        logger.write(test_message)
        logger.flush()  # Ensure terminal output is flushed if necessary

        # Check stdout (StringIO)
        self.assertEqual(mock_stdout.getvalue(), test_message)

        # Check file interactions
        mock_file_open.assert_called_once_with(log_file_path, "a", encoding="utf-8")
        mock_file_open().write.assert_called_once_with(test_message)


class TestSetupLoggingAndLogMessage(unittest.TestCase):

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("etl.etl_scheduler.Logger")  # Mock the Logger class itself
    def test_setup_logging_creates_dir_and_replaces_stdout(
        self, MockLoggerClass, mock_os_makedirs, mock_os_path_exists
    ):
        # Simulate LOGS_DIR does not exist initially, then does (for other calls if any)
        mock_os_path_exists.side_effect = [False, True]

        # Store original stdout
        original_stdout = sys.stdout

        # Mock Logger instance that will be created
        mock_logger_instance = MagicMock()
        MockLoggerClass.return_value = mock_logger_instance

        try:
            setup_logging()

            # Assert directory creation
            mock_os_path_exists.assert_any_call(
                LOGS_DIR
            )  # Called to check if LOGS_DIR exists
            mock_os_makedirs.assert_called_once_with(LOGS_DIR)

            # Assert Logger instantiation
            expected_log_path = os.path.join(LOGS_DIR, SCHEDULER_LOG)
            MockLoggerClass.assert_called_once_with(expected_log_path)

            # Assert sys.stdout replacement
            self.assertIs(sys.stdout, mock_logger_instance)
        finally:
            # Restore original stdout
            sys.stdout = original_stdout

    @patch(
        "sys.stdout", new_callable=io.StringIO
    )  # To capture print output from log_message
    @patch(
        "etl.etl_scheduler.datetime"
    )  # Mock datetime object within etl_scheduler module
    def test_log_message_format(self, mock_datetime, mock_stdout):
        # Configure mock datetime.now()
        fixed_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_now

        test_msg = "A test log message"
        log_message(test_msg)

        expected_output = f"[{fixed_now.strftime('%Y-%m-%d %H:%M:%S')}] {test_msg}\n\n"  # log_message adds two newlines
        # The actual log_message adds \n at the end of the f-string, and print adds another.
        # Let's check the source: print(f"[{timestamp}] {message}\n")
        # This means one \n from f-string, one from print(). So two \n.

        self.assertEqual(mock_stdout.getvalue(), expected_output)


class TestBuildCommand(unittest.TestCase):

    def test_build_command_constructs_correctly(self):
        sample_task = {
            "task": "ASNS",
            "countries": ["US", "CA"],
            "date-from": "2023-01-01",
        }
        expected_command = (
            "python3 main.py --task ASNS --countries US CA --date-from 2023-01-01"
        )
        self.assertEqual(build_command(sample_task), expected_command)

    def test_build_command_handles_single_value_list(self):
        sample_task = {"task": "STATS", "countries": ["US"], "date-resolution": "D"}
        expected_command = (
            "python3 main.py --task STATS --countries US --date-resolution D"
        )
        self.assertEqual(build_command(sample_task), expected_command)

    def test_build_command_no_extra_params(self):
        sample_task = {"task": "CLEANUP"}
        expected_command = "python3 main.py --task CLEANUP"
        self.assertEqual(build_command(sample_task), expected_command)

    def test_build_command_other_scalar_params(self):
        sample_task = {"task": "PROCESS", "some-param": "value1", "another-param": 123}
        # Note: The build_command logic prepends '--' to all keys except 'task' if not handled specially.
        # The current logic prepends '--' to 'task' as well, which is fine if main.py expects --task <TASK_NAME>
        # The build_command code:
        # if name == 'task': cmd_parts.append(f"--{name} {value}")
        # This is correct.
        expected_command = (
            "python3 main.py --task PROCESS --some-param value1 --another-param 123"
        )
        self.assertEqual(build_command(sample_task), expected_command)


if __name__ == "__main__":
    unittest.main()
