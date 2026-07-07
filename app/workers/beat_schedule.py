from datetime import timedelta

BEAT_SCHEDULE = {
    "cleanup-expired-verification-tokens": {
        "task": "cleanup_expired_tokens",
        "schedule": timedelta(hours=1),
    },
    "cleanup-unverified-users": {
        "task": "cleanup_unverified_users",
        "schedule": timedelta(hours=1),
    },
}
