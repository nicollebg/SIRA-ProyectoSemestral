from sqlalchemy import select
from sqlalchemy.orm import Session

from models.subject import Subject


class SubjectRepository:

    def __init__(self, session: Session):
        self.session = session

    def create(self, subject):
        self.session.add(subject)
        self.session.commit()
        self.session.refresh(subject)

        return subject

    def get_by_id(self, subject_id):
        return self.session.get(Subject, subject_id)

    def get_all(self):
        statement = select(Subject)

        return self.session.scalars(statement).all()

    def update(self, subject):
        self.session.commit()
        self.session.refresh(subject)

        return subject

    def delete(self, subject):
        self.session.delete(subject)
        self.session.commit()