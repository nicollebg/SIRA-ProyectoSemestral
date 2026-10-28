"""
Adaptador de salida: reutiliza la lógica transaccional YA probada de services.py
(bloqueo de filas + reintentos). Patrón 'strangler': se migra por partes sin romper nada.
"""
from domain.ports import EnrollmentGateway


class LegacyEnrollmentGateway(EnrollmentGateway):
    def enroll(self, student_id: int, group_id: int) -> str:
        import services  # import perezoso: evita cargar la BD al importar el módulo
        return services.inscribir_estudiante(student_id, group_id)
