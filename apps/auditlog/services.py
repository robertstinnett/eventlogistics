from apps.auditlog.models import AuditLogEntry


def log_account_action(*, account, actor, action, message="", target=None, event=None, metadata=None):
    if account is None:
        return None

    target_type = ""
    target_id = ""
    if target is not None:
        target_type = target._meta.label_lower
        target_id = str(target.pk)

    return AuditLogEntry.objects.create(
        account=account,
        actor=actor,
        event=event,
        action=action,
        target_type=target_type,
        target_id=target_id,
        message=message,
        metadata=metadata or {},
    )
