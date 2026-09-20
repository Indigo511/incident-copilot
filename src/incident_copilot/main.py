from datetime import datetime, timezone

from incident_copilot.analysis import UnlockRequestLog, compare_versions


def sample_logs() -> list[UnlockRequestLog]:
    timestamp = datetime(2026, 9, 20, 10, 7, tzinfo=timezone.utc)
    old_version = [
        UnlockRequestLog(timestamp, f"old-{number}", "v2.3", 200, None)
        for number in range(98)
    ] + [
        UnlockRequestLog(timestamp, "old-user-1", "v2.3", 400, "INVALID_VEHICLE_NUMBER"),
        UnlockRequestLog(timestamp, "old-system-1", "v2.3", 500, "MALFORMED_VEHICLE_ID"),
    ]
    new_version = [
        UnlockRequestLog(timestamp, f"new-{number}", "v2.4", 200, None)
        for number in range(80)
    ] + [
        UnlockRequestLog(timestamp, f"new-user-{number}", "v2.4", 400, "INVALID_VEHICLE_NUMBER")
        for number in range(2)
    ] + [
        UnlockRequestLog(timestamp, f"new-system-{number}", "v2.4", 500, "MALFORMED_VEHICLE_ID")
        for number in range(18)
    ]
    return old_version + new_version


def main() -> None:
    print("Deployment comparison for card-unlock-service")
    for result in compare_versions(sample_logs()):
        print(
            f"{result.version}: requests={result.request_count}, "
            f"system-induced={result.system_induced_error_rate:.1%}, "
            f"user-induced={result.user_induced_error_rate:.1%}"
        )


if __name__ == "__main__":
    main()
