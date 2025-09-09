"""Shared command line utilities."""

from typing import Literal

from minhash_service.core.config import Settings


def format_startup_banner(
    settings: Settings, mode: Literal["worker", "scheduler"]
) -> str:
    """Return a startup banner describing sw configuration."""
    s = settings

    # Notification status
    notif_configured = bool(s.notification.api_url)
    notif_level = s.notification.integrity_report_level.value
    recip_count = len(s.notification.recipient)

    # Periodic tasks
    integ_enabled = getattr(s.periodic_integrity_check, "endabled", False)
    integ_cron = s.periodic_integrity_check.cron
    integ_queue = s.periodic_integrity_check.queue

    cleanup_enabled = getattr(s.cleanup_removed_files, "endabled", False)
    cleanup_cron = s.cleanup_removed_files.cron
    cleanup_queue = s.cleanup_removed_files.queue

    # Build banner
    title = f"Minhash Service — {mode.upper()}"
    title_bar = "─" * len(title)

    lines: list[str] = [
        f"{title}\n{title_bar}",
        f"Log level: {s.log_level.value}",
        "",
        "Storage & Signatures",
        f"  • signature_dir: {s.signature_dir}",
        f"  • trash_dir:     {s.trash_dir}",
        f"  • index_format:  {s.index_format.value}",
        f"  • kmer_size:     {s.kmer_size if s.kmer_size is not None else 'auto'}",
        "",
        "MongoDB",
        f"  • host:        {s.mongodb.host}",
        f"  • port:        {s.mongodb.port}",
        f"  • db:          {s.mongodb.database}",
        f"  • signatures:  {s.mongodb.signature_collection}",
        f"  • reports:     {s.mongodb.report_collection}",
        f"  • audit trail: {s.mongodb.audit_trail_collection}",
        "",
        "Redis",
        f"  • host: {s.redis.host}",
        f"  • port: {s.redis.port}",
        f"  • default queue: {s.redis.queue}",
        "",
        "Notifications",
        f"  • configured: {'YES' if notif_configured else 'NO'}",
        f"  • level:      {notif_level}",
        f"  • recipients: {recip_count}",
    ]

    if mode == "worker":
        lines += [
            "",
            "Worker",
            f"  • RQ queues: [{s.redis.queue}]",
            "  • Actions:",
            "      − Initialize MongoDB indexes",
            "      − Start RQ worker",
        ]
    else:
        lines += [
            "",
            "Scheduler (periodic tasks)",
            f"  • integrity_check: {'ENABLED' if integ_enabled else 'DISABLED'}"
            + (f" → {integ_cron} (queue='{integ_queue}')" if integ_enabled else ""),
            f"  • cleanup_removed_files: {'ENABLED' if cleanup_enabled else 'DISABLED'}"
            + (
                f" → {cleanup_cron} (queue='{cleanup_queue}')"
                if cleanup_enabled
                else ""
            ),
            "",
            "  • Actions:",
            "      − Register enabled cron jobs",
            "      − Start RQ CronScheduler",
        ]

    return "\n".join(lines)
