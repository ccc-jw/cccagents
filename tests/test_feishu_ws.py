"""Tests for the Feishu long-connection receiver.

These tests don't open a real WebSocket — they exercise the event-serialise
helpers and the handler registration so we know the payload shape matches
the webhook-side parser.
"""

import json
from unittest.mock import MagicMock

from cccagents.feishu_ws import _serialise_card_action, _serialise_message_event


def _make_sender(open_id="ou_test_user"):
    s = MagicMock()
    sid = MagicMock()
    sid.open_id = open_id
    sid.union_id = "on_test"
    sid.user_id = "u_test"
    s.sender_id = sid
    return s


def _make_message(content='{"text":"hello"}', message_type="text"):
    m = MagicMock()
    m.message_id = "om_test_001"
    m.chat_id = "oc_test_001"
    m.chat_type = "p2p"
    m.message_type = message_type
    m.content = content
    return m


def _make_event(sender=None, message=None, create_time="1700000000"):
    e = MagicMock()
    e.sender = sender
    e.message = message
    e.create_time = create_time
    return e


def test_serialise_message_event_produces_dispatchable_json():
    """The serialised payload must be parseable by our existing webhook path."""
    data = MagicMock()
    data.event = _make_event(
        sender=_make_sender("ou_real_user"),
        message=_make_message(content='{"text":"ping pm"}'),
    )

    payload = _serialise_message_event(data)
    parsed = json.loads(payload)

    assert parsed["schema"] == "2.0"
    assert parsed["header"]["event_type"] == "im.message.receive_v1"
    assert parsed["event"]["sender"]["sender_id"]["open_id"] == "ou_real_user"
    assert parsed["event"]["message"]["chat_id"] == "oc_test_001"
    assert parsed["event"]["message"]["content"] == '{"text":"ping pm"}'
    assert parsed["event"]["create_time"] == "1700000000"


def test_serialise_message_event_wraps_raw_text():
    """If content isn't valid JSON, wrap it as {"text": <raw>}."""
    data = MagicMock()
    data.event = _make_event(
        sender=_make_sender(),
        message=_make_message(content="plain text only"),
    )

    payload = _serialise_message_event(data)
    parsed = json.loads(payload)
    # The content is now a JSON envelope.
    assert json.loads(parsed["event"]["message"]["content"]) == {"text": "plain text only"}


def test_serialise_message_event_handles_none_sender():
    """A None sender must not crash; the serialised payload must still parse."""
    data = MagicMock()
    data.event = _make_event(sender=None, message=_make_message())

    payload = _serialise_message_event(data)
    parsed = json.loads(payload)
    assert parsed["event"]["sender"] == {"sender_id": {}}


def test_serialise_card_action_produces_dispatchable_json():
    """Card-action serialisation must also produce a parseable payload."""
    data = MagicMock()
    event = MagicMock()
    event.event_id = "evt_001"
    event.message_id = "om_001"
    event.create_time = 1700000000
    event.token = "sig_001"
    operator = MagicMock()
    operator.user_id = "u_001"
    event.operator = operator
    action = MagicMock()
    value = MagicMock()
    value.project_id = "p_001"
    value.action = "approve"
    value.comment = "lgtm"
    action.value = value
    event.action = action
    data.event = event

    payload = _serialise_card_action(data)
    parsed = json.loads(payload)

    assert parsed["event"]["type"] == "card_action"
    assert parsed["event"]["event_id"] == "evt_001"
    assert parsed["event"]["operator"]["user_id"] == "u_001"
    assert parsed["event"]["action"]["value"]["project_id"] == "p_001"
    assert parsed["event"]["action"]["value"]["action"] == "approve"
    assert parsed["event"]["action"]["value"]["comment"] == "lgtm"
    assert parsed["signature"] == "sig_001"


def test_serialise_handles_none_action():
    """A None action.value must yield an empty value dict, not crash."""
    data = MagicMock()
    event = MagicMock()
    event.event_id = "evt"
    event.message_id = "om"
    event.create_time = 1700000000
    event.token = "sig"
    operator = MagicMock()
    operator.user_id = "u"
    event.operator = operator
    action = MagicMock()
    action.value = None  # explicit None value
    event.action = action
    data.event = event

    payload = _serialise_card_action(data)
    parsed = json.loads(payload)
    # action.value is None → fall through to empty dict.
    assert parsed["event"]["action"]["value"] == {}