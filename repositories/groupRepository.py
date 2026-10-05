from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.group import Group
from models.subject import Subject


class GroupRepository:

    def __init__(self, session: Session):

        self.session = session

    def get_available_groups(
        self,
        page=1,
        size=10
    ):

        statement = (

            select(Group)

            .options(

                joinedload(
                    Group.subject
                )
                .joinedload(
                    Subject.teacher
                )

            )

            .where(

                Group.status.is_(True),

                Group.current_capacity
                < Group.maximum_capacity

            )

            .offset(
                (page - 1) * size
            )

            .limit(size)

        )

        return self.session.scalars(
            statement
        ).all()