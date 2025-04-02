from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine("sqlite:///database.db")

Base = declarative_base()

class urls(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    long_url = Column(String,nullable=False)
    short_url = Column(String, unique = True, nullable=False)
    
Base.metadata.create_all(engine)

Session = sessionmaker(engine)
session = Session()

# new_url = urls(long_url = "http://youtube.com", short_url = "yt")
# session.add(new_url)
# session.commit()

# result = session.query(urls).all()
# for i in result:
#     print(i.id, i.long_url, i.short_url)