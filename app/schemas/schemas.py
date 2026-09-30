from pydantic import BaseModel
from typing import Optional


class TestCaseOut(BaseModel):
    input: str
    expected_output: str


class ProblemOut(BaseModel):
    id: str
    topic: str
    grade: str
    rank: int
    title: str
    statement: str
    starter_code: str
    language: str

    class Config:
        from_attributes = True


class SubmitCodeIn(BaseModel):
    user_id: str
    problem_id: str
    code: str
    time_taken_ms: Optional[int] = 0
    hints_used: Optional[int] = 0


class TestCaseResult(BaseModel):
    input: str
    expected_output: str
    actual_output: str
    passed: bool


class SubmitCodeOut(BaseModel):
    attempt_id: str
    passed: bool
    error_type: str
    test_results: list[TestCaseResult]
