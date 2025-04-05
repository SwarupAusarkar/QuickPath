from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import database_manager

engine = create_engine("sqlite:///database.db")
Base = declarative_base()

Session = sessionmaker(engine)
session = Session()
class urls(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    long_url = Column(String,nullable=False)
    short_url = Column(String, unique = True, nullable=False)
    
Base.metadata.create_all(engine)

dbm = database_manager.DatabaseManager(urls, session)

# session.query(urls).delete()
# session.commit()