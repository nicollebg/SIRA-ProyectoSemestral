from datetime import datetime

from models.student import Student
from models.subject import Subject
from models.group import Group
from models.enrollment import Enrollment

from repositories.enrollmentRepository import EnrollmentRepository


def test_create_enrollment(session):

    student = Student(
        code="1001",
        name="Test Student",
        email="test@example.com",
        password="1234",
        registration_date=datetime.now(),
        status=True
    )

    subject = Subject(
        code="MAT001",
        name="Mathematics",
        semester=1,
        teacher_id=1,
        status=True
    )

    group = Group(
        subject=subject,
        academic_period="2026-2",
        schedule="08:00-10:00",
        maximum_capacity=30,
        current_capacity=0,
        lock_version=0,
        status=True
    )

    session.add(student)
    session.add(subject)
    session.add(group)
    session.commit()

    enrollment = Enrollment(
        enrollment_date=datetime.now(),
        period="2026-2",
        status=True,
        student=student,
        group=group
    )

    repository = EnrollmentRepository(session)

    result = repository.create(enrollment)

    assert result.enrollment_id is not None
    assert result.student_id == student.student_id
    assert result.group_id == group.group_id