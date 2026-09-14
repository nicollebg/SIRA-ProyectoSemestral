from sqlalchemy import select
from sqlalchemy.orm import Session

from models.student import Student


class StudentRepository:

    def __init__(self, session: Session):
        self.session = session

    def create(self, student):
        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)

        return student

    def get_by_id(self, student_id):
        return self.session.get(Student, student_id)

    def get_all(self):
        statement = select(Student)

        return self.session.scalars(statement).all()

    def update(self, student):
        self.session.commit()
        self.session.refresh(student)

        return student

    def delete(self, student):
        self.session.delete(student)
        self.session.commit()