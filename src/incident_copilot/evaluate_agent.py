from __future__ import annotations

import json

from incident_copilot.cli import build_copilot, project_root


def evaluate_agent() -> dict[str, float | int]:
    cases = json.loads(
        (project_root() / "evaluation" / "agent_cases.json").read_text(encoding="utf-8")
    )
    copilot = build_copilot()
    passed_status = passed_tools = passed_guardrails = 0
    total_latency = 0.0

    for case in cases:
        result = copilot.investigate(case["question"], scenario=case["scenario"])
        called = {item.name for item in result.trace.tool_executions}
        required = set(case["expected_tools"])
        forbidden = set(case.get("forbidden_tools", []))
        blocked = set(case.get("expected_blocked_actions", []))
        status_ok = result.report.status == case["expected_status"]
        tools_ok = required.issubset(called) and forbidden.isdisjoint(called)
        guardrail_ok = blocked.issubset(result.trace.blocked_actions)
        passed_status += status_ok
        passed_tools += tools_ok
        passed_guardrails += guardrail_ok
        total_latency += result.trace.total_latency_ms
        print(
            f"{'PASS' if status_ok and tools_ok and guardrail_ok else 'FAIL'} | "
            f"{case['scenario']} | {case['question']}"
        )

    total = len(cases)
    return {
        "cases": total,
        "status_accuracy": passed_status / total,
        "tool_requirement_accuracy": passed_tools / total,
        "guardrail_accuracy": passed_guardrails / total,
        "average_local_latency_ms": total_latency / total,
    }


def main() -> None:
    print(json.dumps(evaluate_agent(), indent=2))


if __name__ == "__main__":
    main()
