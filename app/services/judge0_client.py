"""
Thin client around the Judge0 CE API (works against RapidAPI's hosted Judge0
or a self-hosted instance with the same URL shape — just swap JUDGE0_API_URL
and drop the RapidAPI headers if self-hosting).

Docs: https://ce.judge0.com/
"""

import base64
import time
import httpx

from app.core.config import settings

LANGUAGE_IDS = {
    "python": 71,
    "cpp": 54,
}


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if "rapidapi.com" in settings.judge0_api_url:
        headers["X-RapidAPI-Key"] = settings.judge0_rapidapi_key
        headers["X-RapidAPI-Host"] = settings.judge0_rapidapi_host
    elif settings.judge0_auth_token:
        headers["X-Auth-Token"] = settings.judge0_auth_token
    return headers


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _from_b64(text):
    if not text:
        return ""
    return base64.b64decode(text).decode("utf-8", errors="replace")


def run_against_test_cases(code, language, test_cases, time_limit_ms=2000):
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

    submit_url = f"{settings.judge0_api_url}/submissions/batch"

    with httpx.Client(timeout=30.0) as client:
        submit_response = client.post(
            submit_url,
            params={"base64_encoded": "true"},
            headers=_headers(),
            json={"submissions": submissions},
        )
        submit_response.raise_for_status()
        tokens = [item["token"] for item in submit_response.json()]

        results = _poll_for_results(client, tokens)

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


def _poll_for_results(client, tokens, max_wait_seconds=20.0):
    get_url = f"{settings.judge0_api_url}/submissions/batch"
    deadline = time.monotonic() + max_wait_seconds
    poll_interval = 0.5

    while True:
        response = client.get(
            get_url,
            params={
                "tokens": ",".join(tokens),
                "base64_encoded": "true",
                "fields": "token,status,stdout,stderr,compile_output,message,time,memory",
            },
            headers=_headers(),
        )
        response.raise_for_status()
        submissions = response.json()["submissions"]

        if all(s.get("status", {}).get("id", 0) > 2 for s in submissions):
            return submissions

        if time.monotonic() > deadline:
            return submissions

        time.sleep(poll_interval)


def classify_error(results):
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