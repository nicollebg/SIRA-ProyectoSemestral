from sqlalchemy import select
from sqlalchemy.orm import Session

from models.enrollment import Enrollment


class EnrollmentRepository:

    def __init__(self, session: Session):
        self.session = session

    def create(self, enrollment):
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)

        return enrollment

    def get_by_id(self, enrollment_id):
        return self.session.get(Enrollment, enrollment_id)

    def get_all(self):
        statement = select(Enrollment)

        return self.session.scalars(statement).all()

    def update(self, enrollment):
        self.session.commit()
        self.session.refresh(enrollment)

        return enrollment

    def delete(self, enrollment):
        self.session.delete(enrollment)
        self.session.commit()