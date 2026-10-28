
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal
from models.subject import Subject

import logging

from fastapi import Request
from google.genai import errors
from pydantic import Field

from ai_service import ask_ai

app = FastAPI(
    title="SIRA REST API",
    description="REST API for managing academic subjects in SIRA.",
    version="1.0.0",
)


# ==================================================
# DATABASE SESSION
# ==================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================================================
# REQUEST AND RESPONSE SCHEMAS
# ==================================================

class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    semester: int = Field(ge=1, le=20)
    teacher_id: int = Field(gt=0)
    status: bool = True


class SubjectUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    semester: int = Field(ge=1, le=20)
    teacher_id: int = Field(gt=0)
    status: bool


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: int
    code: str
    name: str
    semester: int
    teacher_id: int
    status: bool


# ==================================================
# ENDPOINT 1: GET ALL SUBJECTS
# ==================================================

@app.get(
    "/api/v1/subjects",
    response_model=list[SubjectResponse],
    summary="List all subjects",
    description="Returns all academic subjects registered in SIRA.",
)
def list_subjects(db: Session = Depends(get_db)):
    try:
        subjects = db.scalars(
            select(Subject).order_by(Subject.subject_id)
        ).all()
        return subjects
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve subjects.",
        )


# ==================================================
# ENDPOINT 2: GET SUBJECT BY ID
# ==================================================

@app.get(
    "/api/v1/subjects/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a subject by ID",
    description="Returns one subject using its unique identifier.",
)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    try:
        subject = db.get(Subject, subject_id)

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found.",
            )

        return subject
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve the subject.",
        )


# ==================================================
# ENDPOINT 3: CREATE SUBJECT
# ==================================================

@app.post(
    "/api/v1/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subject",
    description="Registers a new academic subject in SIRA.",
)
def create_subject(
    data: SubjectCreate,
    db: Session = Depends(get_db),
):
    try:
        subject = Subject(
            code=data.code.strip(),
            name=data.name.strip(),
            semester=data.semester,
            teacher_id=data.teacher_id,
            status=data.status,
        )

        if not subject.code or not subject.name:
            raise HTTPException(
                status_code=422,
                detail="Code and name cannot be blank.",
            )

        db.add(subject)
        db.commit()
        db.refresh(subject)

        return subject

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The subject data conflicts with database constraints.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create the subject.",
        )


# ==================================================
# ENDPOINT 4: UPDATE SUBJECT
# ==================================================

@app.put(
    "/api/v1/subjects/{subject_id}",
    response_model=SubjectResponse,
    summary="Update a subject",
    description="Updates an existing subject using its unique identifier.",
)
def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    db: Session = Depends(get_db),
):
    try:
        subject = db.get(Subject, subject_id)

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found.",
            )

        subject.code = data.code.strip()
        subject.name = data.name.strip()
        subject.semester = data.semester
        subject.teacher_id = data.teacher_id
        subject.status = data.status

        if not subject.code or not subject.name:
            raise HTTPException(
                status_code=422,
                detail="Code and name cannot be blank.",
            )

        db.commit()
        db.refresh(subject)

        return subject

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The subject data conflicts with database constraints.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update the subject.",
        )


# ==================================================
# ENDPOINT 5: DELETE SUBJECT
# ==================================================

@app.delete(
    "/api/v1/subjects/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subject",
    description="Deletes a subject if no database relationships prevent deletion.",
)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    try:
        subject = db.get(Subject, subject_id)

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found.",
            )

        db.delete(subject)
        db.commit()

        return None

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The subject cannot be deleted because related records exist.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to delete the subject.",
        )


# ----------


logger = logging.getLogger("sira.ai")


class AIRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AIResponse(BaseModel):
    answer: str


@app.post(
    "/api/v1/ai",
    response_model=AIResponse,
    summary="Ask the SIRA AI assistant",
    description=(
        "Answers an academic question using the SIRA "
        "context provided by the application."
    ),
)
def ask_sira_ai(
    data: AIRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    question = data.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="The question cannot be blank.",
        )

    try:
        subjects = db.scalars(
            select(Subject).order_by(Subject.subject_id)
        ).all()

        context = "\n".join(
            (
                f"Subject code: {subject.code}; "
                f"name: {subject.name}; "
                f"semester: {subject.semester}; "
                f"active: {subject.status}"
            )
            for subject in subjects
        )

        answer = ask_ai(question, context)

        return AIResponse(answer=answer)

    except HTTPException:
        raise

    except errors.APIError as exc:
        logger.exception("Gemini API error")

        error_code = getattr(exc, "code", None)

        if error_code == 429:
            raise HTTPException(
                status_code=429,
                detail="The Gemini API rate limit was reached.",
            ) from exc

        if error_code == 408:
            raise HTTPException(
                status_code=504,
                detail="The Gemini API request timed out.",
            ) from exc

        raise HTTPException(
            status_code=502,
            detail="The Gemini provider returned an error.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error in the SIRA AI endpoint")

        raise HTTPException(
            status_code=500,
            detail="An unexpected AI service error occurred.",
        ) from exc

