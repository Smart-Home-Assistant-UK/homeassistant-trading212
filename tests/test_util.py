from unittest.mock import MagicMock
from custom_components.trading212.util import combined_config, get_enabled_sensor_list


def _entry(data, options=None):
    e = MagicMock()
    e.data = data
    e.options = options or {}
    return e


def test_combined_config_merges_data_and_options():
    entry = _entry({"a": 1, "b": 2}, {"b": 99, "c": 3})
    assert combined_config(entry) == {"a": 1, "b": 99, "c": 3}


def test_combined_config_options_override_data():
    entry = _entry({"key": "old"}, {"key": "new"})
    assert combined_config(entry)["key"] == "new"


def test_combined_config_no_options():
    entry = _entry({"key": "val"})
    assert combined_config(entry) == {"key": "val"}


def test_get_enabled_sensor_list_returns_from_options():
    entry = _entry({}, {"my_sensors": ["a", "b"]})
    assert get_enabled_sensor_list(entry, "my_sensors", ["x"]) == ["a", "b"]


def test_get_enabled_sensor_list_returns_fallback_when_absent():
    entry = _entry({})
    assert get_enabled_sensor_list(entry, "my_sensors", ["x", "y"]) == ["x", "y"]


def test_get_enabled_sensor_list_options_override_data():
    entry = _entry({"my_sensors": ["data"]}, {"my_sensors": ["options"]})
    assert get_enabled_sensor_list(entry, "my_sensors", []) == ["options"]
