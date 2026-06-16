VISION_PREFIX = "lab/vision/"
FORBIDDEN_VISION_FRAGMENTS = ("/relay/", "/control/", "/set", "/command")


def assert_vision_topic_safe(topic: str) -> None:
    if not topic.startswith(VISION_PREFIX):
        raise ValueError(f"vision publisher refused non-vision topic: {topic}")
    lowered = topic.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_VISION_FRAGMENTS):
        raise ValueError(f"vision publisher refused unsafe topic: {topic}")
