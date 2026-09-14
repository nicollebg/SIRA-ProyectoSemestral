import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base


@pytest.fixture
def session():

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    session = Session()

    yield session

    session.close()

    Base.metadata.drop_all(engine)