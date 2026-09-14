from database import Base

from models import (
    Student,
    Teacher,
    Subject,
    Group,
    Enrollment,
    Waitlist,
    Notification,
    Coordinator,
    PerformanceMetric
)


for table in Base.metadata.tables:
    print(table)