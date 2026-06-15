from __future__ import annotations

import json

from .topics import assert_vision_topic_safe


class VisionPublisher:
    def __init__(self, client) -> None:
        self.client = client

    def publish(self, topic: str, payload, retain: bool = False) -> None:
        assert_vision_topic_safe(topic)
        encoded = json.dumps(payload, separators=(",", ":")) if isinstance(payload, (dict, list)) else str(payload)
        self.client.publish(topic, encoded, qos=1, retain=retain)

