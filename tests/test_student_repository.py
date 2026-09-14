from datetime import datetime

from models.student import Student
from repositories.studentRepository import StudentRepository


def test_create_student(session):

    repository = StudentRepository(session)

    student = Student(
        code="1001",
        name="Test Student",
        email="test@example.com",
        password="1234",
        registration_date=datetime.now(),
        status=True
    )

    result = repository.create(student)

    assert result.student_id is not None
    assert result.name == "Test Student"