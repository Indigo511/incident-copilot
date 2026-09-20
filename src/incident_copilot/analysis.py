from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Iterable


class ErrorCategory(StrEnum):
    SYSTEM_INDUCED = "system_induced"
    USER_INDUCED = "user_induced"


# This mapping is owned by the backend. It is deliberately deterministic and auditable.
ERROR_CATEGORY_BY_CODE: dict[str, ErrorCategory] = {
    "MALFORMED_VEHICLE_ID": ErrorCategory.SYSTEM_INDUCED,
    "VERIFICATION_SERVICE_TIMEOUT": ErrorCategory.SYSTEM_INDUCED,
    "DB_CONNECTION_POOL_EXHAUSTED": ErrorCategory.SYSTEM_INDUCED,
    "INVALID_VEHICLE_NUMBER": ErrorCategory.USER_INDUCED,
    "VERIFICATION_CODE_MISMATCH": ErrorCategory.USER_INDUCED,
}


@dataclass(frozen=True)
class UnlockRequestLog:
    timestamp: datetime
    request_id: str
    deployment_version: str
    http_status: int
    error_code: str | None
    endpoint: str = "POST /v1/cards/unlock"

    @property
    def outcome(self) -> str:
        return "success" if 200 <= self.http_status < 300 else "failure"

    @property
    def error_category(self) -> ErrorCategory | None:
        if self.error_code is None:
            return None
        return ERROR_CATEGORY_BY_CODE.get(self.error_code)


@dataclass(frozen=True)
class VersionComparison:
    version: str
    request_count: int
    system_induced_failures: int
    user_induced_failures: int

    @property
    def system_induced_error_rate(self) -> float:
        return self.system_induced_failures / self.request_count if self.request_count else 0.0

    @property
    def user_induced_error_rate(self) -> float:
        return self.user_induced_failures / self.request_count if self.request_count else 0.0


def compare_versions(logs: Iterable[UnlockRequestLog]) -> list[VersionComparison]:
    """Aggregate comparable failure rates for each deployment version."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for log in logs:
        version_counts = counts[log.deployment_version]
        version_counts["requests"] += 1
        if log.outcome != "failure":
            continue
        if log.error_category == ErrorCategory.SYSTEM_INDUCED:
            version_counts["system"] += 1
        elif log.error_category == ErrorCategory.USER_INDUCED:
            version_counts["user"] += 1

    return [
        VersionComparison(
            version=version,
            request_count=values["requests"],
            system_induced_failures=values["system"],
            user_induced_failures=values["user"],
        )
        for version, values in sorted(counts.items())
    ]
