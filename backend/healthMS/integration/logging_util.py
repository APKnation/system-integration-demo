import logging

from .models import IntegrationLog

logger = logging.getLogger(__name__)


def log_transaction(
    *,
    endpoint: str,
    method: str,
    status_code: int,
    status: str,
    error_message: str = "",
    request_id=None,
) -> None:
    """Persist an integration transaction log entry.

    Never raises: transaction logging must not break the main request flow.
    """
    try:
        IntegrationLog.objects.create(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            status=status,
            error_message=error_message or "",
            request_id=request_id,
        )
    except Exception:
        logger.exception("Failed to write IntegrationLog entry")
