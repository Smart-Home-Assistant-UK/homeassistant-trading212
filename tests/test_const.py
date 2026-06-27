from custom_components.trading212.const import (
    EVENT_DIVIDEND_RECEIVED,
    EVENT_PIE_CREATED,
    EVENT_PIE_DELETED,
    EVENT_POSITION_CLOSED,
    EVENT_POSITION_OPENED,
)


def test_event_constants_are_strings():
    assert isinstance(EVENT_POSITION_OPENED, str)
    assert isinstance(EVENT_POSITION_CLOSED, str)
    assert isinstance(EVENT_DIVIDEND_RECEIVED, str)
    assert isinstance(EVENT_PIE_CREATED, str)
    assert isinstance(EVENT_PIE_DELETED, str)


def test_event_constants_use_domain_prefix():
    assert EVENT_POSITION_OPENED == "trading212_position_opened"
    assert EVENT_POSITION_CLOSED == "trading212_position_closed"
    assert EVENT_DIVIDEND_RECEIVED == "trading212_dividend_received"
    assert EVENT_PIE_CREATED == "trading212_pie_created"
    assert EVENT_PIE_DELETED == "trading212_pie_deleted"
