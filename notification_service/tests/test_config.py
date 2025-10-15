from bonsai_notification.config import Settings


def test_default_settings():
    s = Settings()
    assert s.sender_email == "noreply@example.com"
    assert s.log_level.name == "INFO"
    assert s.use_redis is False or isinstance(s.use_redis, bool)
