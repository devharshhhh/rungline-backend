import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db import models
from app.schemas.schemas import SubmitCodeIn, SubmitCodeOut, TestCaseResult
from app.services import judge0_client

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/submit", response_model=SubmitCodeOut)
def submit_code(payload: SubmitCodeIn, db: Session = Depends(get_db)):
    problem = db.get(models.Problem, payload.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    user = db.get(models.User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        results = judge0_client.run_against_test_cases(
            code=payload.code,
            language=problem.language.value,
            test_cases=problem.test_cases,
            time_limit_ms=problem.time_limit_ms,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Judge0 rejected the request ({e.response.status_code}) — check JUDGE0_API_KEY in your .env file.",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Judge0: {e}")
    overall_passed = all(r["passed"] for r in results)
    error_type = judge0_client.classify_error(results)

    attempt = models.Attempt(
        user_id=payload.user_id,
        problem_id=payload.problem_id,
        code_submitted=payload.code,
        passed=overall_passed,
        error_type=error_type,
        time_taken_ms=payload.time_taken_ms or 0,
        hints_used=payload.hints_used or 0,
        test_results=results,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return SubmitCodeOut(
        attempt_id=attempt.id,
        passed=overall_passed,
        error_type=error_type,
        test_results=[TestCaseResult(**r) for r in results],
    )
