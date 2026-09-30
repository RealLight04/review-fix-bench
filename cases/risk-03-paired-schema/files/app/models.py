"""ORM 모델."""
from sqlalchemy import Boolean, Column, Date, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    source_key = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    venue = Column(String)
    start_date = Column(Date)
    is_upcoming = Column(Boolean, default=True)
