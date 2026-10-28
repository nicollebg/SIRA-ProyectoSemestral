from domain.errors import GroupNotFound
from domain.ports import EnrollmentGateway, GroupReader


class EnrollmentService:
    """
    Caso de uso: inscribir a un estudiante.
    Dos dependencias inyectadas por constructor -> se pueden reemplazar por mocks.
    """

    def __init__(self, group_reader: GroupReader, gateway: EnrollmentGateway):
        self._groups = group_reader
        self._gateway = gateway

    def enroll(self, student_id: int, group_id: int) -> str:
        if self._groups.get_group(group_id) is None:
            raise GroupNotFound(f"El grupo {group_id} no existe.")
        return self._gateway.enroll(student_id, group_id)
