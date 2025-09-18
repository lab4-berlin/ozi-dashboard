import os
import json
from datetime import datetime
from extract_from_ripe_api import save_api_response
from unittest.mock import patch
import builtins


def test_save_api_response_creates_file(tmp_path):
    url = "https://example.com/api"
    params = {"resource": "US", "query_time": datetime(2023, 1, 1, 0, 0)}
    response = {"status": "ok", "data": [1, 2, 3]}

    folder = tmp_path / "data"
    folder.mkdir(exist_ok=True)

    original_makedirs = os.makedirs
    original_open = builtins.open

    def mocked_makedirs(path, exist_ok=True):
        if "data" in path:
            path = str(folder)
        return original_makedirs(path, exist_ok=exist_ok)

    def mocked_open(path, mode="r", encoding=None):
        path_str = str(path)
        if "data/" in path_str:
            path = folder / os.path.basename(path_str)
        return original_open(path, mode, encoding=encoding)

    with patch("os.makedirs", side_effect=mocked_makedirs), patch(
        "builtins.open", side_effect=mocked_open
    ):

        save_api_response(url, params, response, save_mode="file")

        files = list(folder.glob("*.json"))
        assert len(files) == 1

        with open(files[0], "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data == response
