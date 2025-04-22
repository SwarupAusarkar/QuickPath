from sqlalchemy import Column, Integer, MetaData, String, Table

metadata = MetaData()

urls = Table(
    "urls",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("long_url", String, nullable=False),
    Column("short_url", String, unique=True, nullable=False),
    Column("qr_code", String, nullable=False),
)
