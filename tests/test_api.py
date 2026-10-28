
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import app, get_db
from database import Base


test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def setup_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as db:
        from models.teacher import Teacher

        teacher = Teacher(
            document="DOC-API-01",
            name="Docente",
            last_name="Prueba",
            email="docente.api@example.com",
            phone="3000000000",
            status=True,
        )

        db.add(teacher)
        db.commit()
        db.refresh(teacher)

        return teacher.teacher_id


def teardown_database():
    Base.metadata.drop_all(bind=test_engine)


def test_create_and_get_subject():
    teacher_id = setup_database()

    try:
        response = client.post(
            "/api/v1/subjects",
            json={
                "code": "API001",
                "name": "Subject Test",
                "semester": 1,
                "teacher_id": teacher_id,
                "status": True,
            },
        )

        assert response.status_code == 201
        subject_id = response.json()["subject_id"]

        get_response = client.get(
            f"/api/v1/subjects/{subject_id}"
        )

        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Subject Test"
    finally:
        teardown_database()


def test_update_subject():
    teacher_id = setup_database()

    try:
        create_response = client.post(
            "/api/v1/subjects",
            json={
                "code": "API002",
                "name": "Original Subject",
                "semester": 2,
                "teacher_id": teacher_id,
                "status": True,
            },
        )

        assert create_response.status_code == 201
        subject_id = create_response.json()["subject_id"]

        update_response = client.put(
            f"/api/v1/subjects/{subject_id}",
            json={
                "code": "API002",
                "name": "Updated Subject",
                "semester": 3,
                "teacher_id": teacher_id,
                "status": True,
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Subject"
        assert update_response.json()["semester"] == 3
    finally:
        teardown_database()


def test_subject_not_found():
    setup_database()

    try:
        response = client.get("/api/v1/subjects/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Subject not found."
    finally:
        teardown_database()
