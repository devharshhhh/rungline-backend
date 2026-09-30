"""
Thin client around the Judge0 CE API (works against RapidAPI's hosted Judge0
or a self-hosted instance with the same URL shape — just swap JUDGE0_API_URL
and drop the RapidAPI headers if self-hosting).

Docs: https://ce.judge0.com/
"""

import base64
import httpx

from app.core.config import settings

LANGUAGE_IDS = {
    "python": 71,   # Python 3.8.1
    "cpp": 54,      # C++ (GCC 9.2.0)
}


def _headers() -> dict:
    # If pointed at a self-hosted Judge0 (no RapidAPI key set), skip these headers.
    if not settings.judge0_api_key:
        return {"Content-Type": "application/json"}
    return {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": settings.judge0_api_key,
        "X-RapidAPI-Host": settings.judge0_api_host,
    }


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _from_b64(text: str | None) -> str:
    if not text:
        return ""
    return base64.b64decode(text).decode("utf-8", errors="replace")


def run_against_test_cases(
    code: str,
    language: str,
    test_cases: list[dict],
    time_limit_ms: int = 2000,
) -> list[dict]:
    """
    Submits one batch request covering all test cases for a single problem.
    Returns a list of dicts: {input, expected_output, actual_output, passed,
    status, stderr}.
    """
    language_id = LANGUAGE_IDS.get(language)
    if language_id is None:
        raise ValueError(f"Unsupported language: {language}")

    submissions = [
        {
            "source_code": _b64(code),
            "language_id": language_id,
            "stdin": _b64(tc["input"]),
            "expected_output": _b64(tc["expected_output"]),
            "cpu_time_limit": round(time_limit_ms / 1000, 1),
        }
        for tc in test_cases
    ]

    url = f"{settings.judge0_api_url}/submissions/batch"
    params = {"base64_encoded": "true", "wait": "true"}

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, params=params, headers=_headers(), json={"submissions": submissions})
        response.raise_for_status()
        results = response.json()

    output = []
    for tc, result in zip(test_cases, results):
        status_desc = result.get("status", {}).get("description", "Unknown")
        actual_output = _from_b64(result.get("stdout")).rstrip("\n")
        expected = tc["expected_output"].rstrip("\n")
        passed = status_desc == "Accepted" and actual_output == expected

        output.append({
            "input": tc["input"],
            "expected_output": tc["expected_output"],
            "actual_output": actual_output or _from_b64(result.get("stderr")) or _from_b64(result.get("compile_output")),
            "passed": passed,
            "status": status_desc,
        })

    return output


def classify_error(results: list[dict]) -> str:
    """Maps Judge0 statuses across all test cases to our internal error_type enum."""
    statuses = {r["status"] for r in results}
    if all(r["passed"] for r in results):
        return "none"
    if "Compilation Error" in statuses:
        return "syntax_error"
    if "Time Limit Exceeded" in statuses:
        return "timeout"
    if any(s.startswith("Runtime Error") for s in statuses):
        return "runtime_error"
    return "wrong_output"
