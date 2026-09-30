"""Tests for the Kinderpedia sensor platform."""

from unittest.mock import MagicMock

import pytest

from custom_components.kinderpedia.coordinator import _parse_timeline
from custom_components.kinderpedia.sensor import (
    KinderpediaChildInfoSensor,
    KinderpediaWeekSensor,
)
from tests.conftest import MOCK_CHILD, MOCK_TIMELINE_RAW


@pytest.fixture
def coordinator():
    """Return a mock coordinator holding the fixture week."""
    mock = MagicMock()
    mock.data = {
        "last_updated": "2026-02-09 12:00:00",
        "children": {
            "111_222": {
                "child": dict(MOCK_CHILD),
                "days": _parse_timeline(MOCK_TIMELINE_RAW),
                "newsfeed": [],
            }
        },
    }
    return mock


def _week_sensor(coordinator, sensor_type="breakfast_week", field="breakfast_percent", items_field=None):
    return KinderpediaWeekSensor(
        coordinator,
        111,
        222,
        "Alice Smith",
        "Alice",
        sensor_type=sensor_type,
        field=field,
        items_field=items_field,
    )


class TestChildInfoSensor:
    def test_native_value_is_full_name(self, coordinator):
        sensor = KinderpediaChildInfoSensor(coordinator, 111, 222, "Alice Smith", "Alice")
        assert sensor.native_value == "Alice Smith"
        assert sensor.unique_id == "kinderpedia_child_info_111_222"
        assert sensor.name == "alice"

    def test_attributes(self, coordinator):
        attrs = KinderpediaChildInfoSensor(
            coordinator, 111, 222, "Alice Smith", "Alice"
        ).extra_state_attributes
        assert attrs["birth_date"] == "2020-06-15"
        assert attrs["gender"] == "female"
        assert attrs["kindergarten"] == "Happy Kids"

    def test_no_data(self):
        empty = MagicMock()
        empty.data = None
        sensor = KinderpediaChildInfoSensor(empty, 111, 222, "Alice Smith", "Alice")
        assert sensor.native_value is None
        assert sensor.extra_state_attributes == {}


class TestWeekSensor:
    def test_naming_scheme(self, coordinator):
        sensor = _week_sensor(coordinator)
        assert sensor.name == "alice breakfast week"
        assert sensor.unique_id == "kinderpedia_breakfast_week_111_222"

    def test_state_is_the_update_date(self, coordinator):
        assert _week_sensor(coordinator).native_value == "2026-02-09"

    def test_week_attributes_keyed_by_weekday(self, coordinator, freezer):
        freezer.move_to("2026-02-11T12:00:00+00:00")
        attrs = _week_sensor(coordinator).extra_state_attributes

        assert attrs["monday"] == 80
        # Days the school reported nothing for stay at 0, as the charts expect.
        assert attrs["tuesday"] == 0
        assert set(attrs) == {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "last_updated",
        }

    def test_week_attributes_outside_fetched_week(self, coordinator, freezer):
        freezer.move_to("2026-03-02T12:00:00+00:00")
        attrs = _week_sensor(coordinator).extra_state_attributes
        assert attrs["monday"] == 0

    def test_nap_week_reports_minutes(self, coordinator, freezer):
        freezer.move_to("2026-02-11T12:00:00+00:00")
        attrs = _week_sensor(
            coordinator, sensor_type="nap_week", field="nap_duration"
        ).extra_state_attributes
        assert attrs["monday"] == 90

    def test_lunch_dish_week_reports_percent_and_items(self, coordinator, freezer):
        freezer.move_to("2026-02-11T12:00:00+00:00")
        sensor = _week_sensor(
            coordinator,
            sensor_type="lunch_dish_1_week",
            field="lunch_dish_1_percent",
            items_field="lunch_dish_1_items",
        )
        assert sensor.name == "alice lunch dish 1 week"
        attrs = sensor.extra_state_attributes
        assert attrs["monday"] == 90
        assert attrs["monday_items"] == "Chicken soup"
        assert attrs["tuesday"] == 0
        assert attrs["tuesday_items"] == ""
