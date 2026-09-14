from models.subject import Subject
from repositories.SubjectRepository import SubjectRepository


def test_get_subject(session):

    repository = SubjectRepository(session)

    subject = Subject(
        code="MAT001",
        name="Mathematics",
        semester=1,
        teacher_id=1,
        status=True
    )

    created = repository.create(subject)

    result = repository.get_by_id(
        created.subject_id
    )

    assert result is not None
    assert result.name == "Mathematics"