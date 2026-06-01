"""Base declarativa do SQLAlchemy.

Apenas define a Base. NÃO importe os modelos aqui para evitar import circular
(os modelos importam esta Base). Para registrar os modelos no metadata (usado
pelo Alembic autogenerate), importe-os em app/db/base_all.py.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
