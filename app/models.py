from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from app.database import Base


class Failure(Base):
    __tablename__ = "failures"

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, nullable=False)
    workflow = Column(String, nullable=False)
    run_id = Column(BigInteger, nullable=False)
    log = Column(Text, nullable=False)
    analysis = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
