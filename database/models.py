import datetime
from uuid import uuid4, UUID

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, CHAR
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy import MetaData
from sqlalchemy.sql import sqltypes

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata

    def __init__(self):
        self.metadata


class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, UUID):
            return str(value)
        return value

    def process_result_value(self, value: sqltypes.UUID, dialect=None):
        if not value:
            raise ValueError("Error, no value passed for conversion")
        return str(value)


class AdminUser(Base):
    __tablename__ = "admin_users"
    metadata

    id = Column(
        GUID,
        default=uuid4,
        unique=True,
        nullable=False,
        primary_key=True,
    )
    fullnames = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(256), nullable=False, unique=True)
    otp = Column(String(256), nullable=False, unique=True)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    inventory_rel = relationship(
        "Inventory", backref="admin_users", uselist=True, cascade="all, delete-orphan"
    )
    expense_rel = relationship(
        "OperationExpenses",
        backref="admin_users",
        uselist=True,
        cascade="all, delete-orphan",
    )

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"User: (id={self.id}, fullnames={self.fullnames}, email={self.email}, password={self.password}, otp={self.otp}, created={self.created}, updated={self.updated})"


class Inventory(Base):
    __tablename__ = "inventory"
    metadata

    id = Column(GUID, default=uuid4, unique=True, nullable=False, primary_key=True)
    category = Column(String(50), unique=False, nullable=False)
    stock = Column(Integer, nullable=True, default=0)
    amount = Column(Float, nullable=False)
    mode = Column(String(30), nullable=False, name="mode", default="cash")
    user_id = Column(
        GUID,
        ForeignKey("admin_users.id", name="user_id", ondelete="CASCADE"),
        nullable=False,
    )
    flag = Column(String(50), nullable=False, default="non-asset")
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    catalog_rel = relationship(
        "Catalog", backref="inventory", cascade="all, delete-orphan", uselist=True
    )
    creditor_rel = relationship(
        "Creditors", backref="inventory", cascade="all, delete-orphan", uselist=False
    )

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"Inventory: (id={self.id}, category={self.category}, stock={self.stock}, amount={self.amount}, mode={self.mode} user_id={self.user_id}, flag={self.flag} created={self.created}, updated={self.updated})"


class Catalog(Base):
    __tablename__ = "catalog"
    metadata

    id = Column(
        GUID, unique=True, primary_key=True, nullable=False, default=uuid4, name="id"
    )
    brand = Column(String, nullable=False, name="brand")
    stock = Column(Integer, nullable=False, name="stock", default=0)
    price = Column(Float, nullable=False, name="price")
    i_id = Column(
        GUID,
        ForeignKey("inventory.id", ondelete="CASCADE", name="i_id"),
        nullable=False,
    )
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    sales_rel = relationship(
        "Sales", backref="catalog", cascade="all, delete-orphan", uselist=True
    )
    creditors_rel = relationship(
        "Creditors", backref="catalog", cascade="all, delete-orphan"
    )

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"Catalog: (id={self.id}, brand={self.brand}, stock={self.stock}, price={self.price}, i_id={self.i_id}, created={self.created}, updated={self.updated})"


class Sales(Base):
    __tablename__ = "sales"
    metadata

    id = Column(GUID, primary_key=True, default=uuid4, nullable=False, unique=True)
    p_id = Column(
        GUID,
        ForeignKey("catalog.id", name="p_id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity = Column(Integer, default=0, nullable=False)
    amount = Column(Float, nullable=False)
    mode = Column(String(30), nullable=False, default="cash")
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    credited_rel = relationship(
        "Credited", backref="sales", cascade="all, delete-orphan", uselist=True
    )

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"Sales: (id={self.id}, p_id={self.p_id}, quantity={self.quantity}, amount={self.amount}, mode={self.mode}, created={self.created}, updated={self.updated})"


class Credited(Base):
    __tablename__ = "credited"
    metadata

    id = Column(GUID, default=uuid4, nullable=False, primary_key=True, unique=True)
    name = Column(String(50), nullable=False, unique=True)
    phone = Column(String(50), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    s_id = Column(
        GUID, ForeignKey("sales.id", ondelete="CASCADE", name="s_id"), nullable=False
    )
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"(id={self.id}, name={self.name}, phone={self.phone}, amount={self.amount}, s_id={self.s_id}, created={self.created}, updated={self.updated})"


class Creditors(Base):
    __tablename__ = "creditors"
    metadata

    id = Column(GUID, default=uuid4, nullable=False, primary_key=True, unique=True)
    name = Column(String(50), nullable=False, unique=True)
    phone = Column(String(50), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    i_id = Column(
        GUID,
        ForeignKey("inventory.id", ondelete="CASCADE", name="i_id"),
        nullable=False,
    )
    p_id = Column(
        GUID, ForeignKey("catalog.id", ondelete="CASCADE", name="p_id"), nullable=False
    )
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"(id={self.id}, name={self.name}, phone={self.phone}, amount={self.amount}, i_id={self.i_id}, p_id={self.p_id} created={self.created}, updated={self.updated})"


class OperationExpenses(Base):
    __tablename__ = "expenses"
    metadata

    id = Column(GUID, primary_key=True, nullable=False, unique=True, default=uuid4)
    name = Column(String(50), nullable=False)
    reason = Column(String(150), nullable=False, unique=True)
    user_id = Column(
        GUID,
        ForeignKey("admin_users.id", name="users", ondelete="CASCADE"),
        nullable=False,
    )
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated = Column(DateTime, nullable=True)

    def __init__(self, **kw):
        super().__init__(**kw)

    def table_size(self):
        for k, v in metadata.tables.items():
            if k != self.__tablename__:
                continue
            return v.__sizeof__()
        return metadata.tables.__sizeof__()

    def __repr__(self):
        return f"Expenses: (id={self.id}, name={self.name}, reason={self.reason}, user_id={self.user_id} created={self.created}, updated={self.updated})"
