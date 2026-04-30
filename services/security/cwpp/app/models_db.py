from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from .db_helper import Base


class CWPPWorkload(Base):
    __tablename__ = "cwpp_workloads"
    id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    provider = Column(String)
    risk_score = Column(Integer, default=0)
    status = Column(String, default="open")
    findings_count = Column(Integer, default=0)
