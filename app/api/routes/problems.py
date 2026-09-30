from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db
from app.db import models
from app.schemas.schemas import ProblemOut

router = APIRouter(prefix="/problems", tags=["problems"])


def _to_out(p: models.Problem) -> ProblemOut:
    return ProblemOut(
        id=p.id,
        topic=p.topic.name,
        grade=p.grade,
        rank=p.rank,
        title=p.title,
        statement=p.statement,
        starter_code=p.starter_code,
        language=p.language.value,
    )


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.get(models.Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return _to_out(problem)


@router.get("/next/{user_id}", response_model=ProblemOut)
def get_next_problem(user_id: str, language: str = "python", db: Session = Depends(get_db)):
    """
    Phase 1 version: dumb sequential selection — the first problem, in
    topic order then grade then rank, that this user hasn't solved yet.
    This gets replaced by the real adaptive engine in Phase 2, once there's
    real attempt data to tune it against.
    """
    solved_ids = {
        row[0]
        for row in db.execute(
            select(models.Attempt.problem_id).where(
                models.Attempt.user_id == user_id, models.Attempt.passed == True  # noqa: E712
            )
        ).all()
    }

    stmt = (
        select(models.Problem)
        .join(models.Topic)
        .where(models.Problem.language == language)
        .order_by(models.Topic.order_index, models.Problem.grade, models.Problem.rank)
    )
    for problem in db.execute(stmt).scalars().all():
        if problem.id not in solved_ids:
            return _to_out(problem)

    raise HTTPException(status_code=404, detail="No more problems available — congrats, they solved everything!")
