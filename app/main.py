import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.llm import analyze_failure
from app.models import Failure

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CI/CD Failure Analyzer")

WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]


def require_token(x_webhook_token: str = Header(default="")):
    if not secrets.compare_digest(x_webhook_token, WEBHOOK_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid or missing token")


class FailureReport(BaseModel):
    repo: str
    workflow: str
    run_id: int
    log: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/failure", dependencies=[Depends(require_token)])
def receive_failure(report: FailureReport, db: Session = Depends(get_db)):
    failure = Failure(
        repo=report.repo,
        workflow=report.workflow,
        run_id=report.run_id,
        log=report.log,
    )
    db.add(failure)
    db.commit()
    db.refresh(failure)

    failure.analysis = analyze_failure(report.repo, report.workflow, report.log)
    db.commit()

    return {"received": True, "id": failure.id, "analysis": failure.analysis}


@app.get("/failures", dependencies=[Depends(require_token)])
def list_failures(db: Session = Depends(get_db)):
    rows = db.query(Failure).order_by(Failure.id.desc()).all()
    return [
        {
            "id": r.id,
            "repo": r.repo,
            "workflow": r.workflow,
            "run_id": r.run_id,
            "has_analysis": r.analysis is not None,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@app.get("/failures/{failure_id}", dependencies=[Depends(require_token)])
def get_failure(failure_id: int, db: Session = Depends(get_db)):
    row = db.get(Failure, failure_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Failure not found")
    return {
        "id": row.id,
        "repo": row.repo,
        "workflow": row.workflow,
        "run_id": row.run_id,
        "log": row.log,
        "analysis": row.analysis,
        "created_at": row.created_at,
    }