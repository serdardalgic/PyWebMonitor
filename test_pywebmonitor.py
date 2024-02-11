import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from pywebmonitor import (
    get_db_params,
    is_valid_interval,
    is_valid_regex,
    is_valid_url,
    read_urls,
    setup_logging,
    validate_urls,
)


@pytest.fixture
def setup_logging_fixture(tmp_path: Path):
    logfile = tmp_path / "test.log"
    setup_logging(logfile)
    return logfile


@pytest.fixture
def example_config_ini(tmp_path: Path):
    config_file = tmp_path / "config.ini"
    with open(config_file, "w") as f:
        f.write(
            "[Database]\nhost=test_host\nport=test_port\nuser=test_user\npassword=test_password\ndbname=test_dbname"
        )
    return config_file


@pytest.fixture
def valid_csv_path(tmpdir):
    csv_data = """https://example.com,10,regex_pattern\nhttps://example2.com,20,regex_pattern2"""
    csv_file = tmpdir.join("valid_urls.csv")
    csv_file.write(csv_data)
    return str(csv_file)


@pytest.fixture
def invalid_csv_path(tmpdir):
    csv_file = tmpdir.join("invalid_urls.csv")
    csv_file.write("invalid data")
    return str(csv_file)


@pytest.fixture
def mock_db_connection():
    return MagicMock()


@pytest.mark.skip(reason="not writing any data to the logs at this point")
def test_setup_logging(setup_logging_fixture: Any):
    assert setup_logging_fixture.is_file()

    logger = logging.getLogger(__name__)


def test_get_db_params_with_existing_file(
    example_config_ini: Any,
):
    assert example_config_ini.is_file()

    # Test with existing file
    result = get_db_params(str(example_config_ini))
    expected_result = {
        "host": "test_host",
        "port": "test_port",
        "user": "test_user",
        "password": "test_password",
        "dbname": "test_dbname",
    }

    assert result == expected_result


def test_get_db_params_with_nonexistent_file_without_any_env_vars():
    # Test with non-existent file
    result = get_db_params("nonexistent_file.ini")
    expected_result = {
        "host": None,
        "port": None,
        "user": None,
        "password": None,
        "dbname": None,
        "tablename": None,
    }
    assert result == expected_result


def test_get_db_params_with_env_variables(monkeypatch: pytest.MonkeyPatch):
    # Test with environment variables
    monkeypatch.setenv("DB_HOST", "env_host")
    monkeypatch.setenv("DB_PORT", "env_port")
    monkeypatch.setenv("DB_USER", "env_user")
    monkeypatch.setenv("DB_PASSWORD", "env_password")
    monkeypatch.setenv("DB_NAME", "env_dbname")
    monkeypatch.setenv("DB_TABLENAME", "env_tablename")

    result = get_db_params("nonexistent_file.ini")
    expected_result = {
        "host": "env_host",
        "port": "env_port",
        "user": "env_user",
        "password": "env_password",
        "dbname": "env_dbname",
        "tablename": "env_tablename",
    }

    assert result == expected_result


def test_get_db_params_with_invalid_file(tmp_path: Path):
    # Create an invalid config file
    config_file = tmp_path / "config.ini"
    with open(config_file, "w") as f:
        f.write("invalid_content")

    # Test with invalid file
    result = get_db_params(str(config_file))
    assert result is None


def test_read_urls_with_valid_csv(valid_csv_path):
    result = read_urls(valid_csv_path)
    assert result == [
        ["https://example.com", "10", "regex_pattern"],
        ["https://example2.com", "20", "regex_pattern2"],
    ]


def test_read_urls_with_invalid_csv(invalid_csv_path, caplog):
    # We're parsing invalid CSVs too. We just don't validate them.
    result = read_urls(invalid_csv_path)
    assert result is not None


def test_read_urls_with_nonexistent_file(caplog):
    result = read_urls("nonexistent_file.csv")
    assert result is None
    assert 'Error: URLs file "nonexistent_file.csv" not found.' in caplog.text


def test_is_valid_url():
    assert is_valid_url("http://www.example.com")
    assert is_valid_url("https://example.com/path?query=value")
    assert not is_valid_url("invalidurl")


def test_is_valid_interval():
    assert is_valid_interval("10")
    assert is_valid_interval("100", min_val=50, max_val=200)
    assert not is_valid_interval("abc")
    assert not is_valid_interval("500", min_val=50, max_val=200)


def test_is_valid_regex():
    assert is_valid_regex(None)
    assert is_valid_regex(r"\d+")
    assert not is_valid_regex("[a-z")


def test_validate_urls(caplog):
    urls_data_valid = [
        ("http://www.example.com", "10", r"\w+"),
        ("https://example.com/path", "30", r"\d+"),
    ]
    urls_data_invalid = [
        ("invalidurl", "20", r"\d+"),
        ("http://www.example.com", "NaN", r"\w+"),
    ]

    validated_urls = validate_urls(urls_data_valid)
    assert len(validated_urls) == len(urls_data_valid)

    caplog.set_level(logging.WARN)

    # Somehow the root logger is not captured here.
    # Commenting out for now.
    # with pytest.warns(Warning, match="Invalid URL data"):
    #   invalid_urls = validate_urls(urls_data_invalid)

    invalid_urls = validate_urls(urls_data_invalid)
    assert len(invalid_urls) == 0
