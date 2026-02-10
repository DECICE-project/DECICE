from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class VertexpoolDB(Base):
    __tablename__ = "vertexpool_table"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    devices: Mapped[list["DeviceDB"]] = relationship(back_populates="vertexpool")
    nodes: Mapped[list["NodeDB"]] = relationship(back_populates="vertexpool")
    labels: Mapped[list["Vertexpool_LabelDB"]] = relationship(back_populates="vertexpool", cascade="all, delete-orphan")


class Vertexpool_LabelDB(Base):
    __tablename__ = "vertexpool_label_table"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vertexpool_id: Mapped[int] = mapped_column(ForeignKey("vertexpool_table.id"))
    key: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()
    vertexpool: Mapped[VertexpoolDB] = relationship(back_populates="labels")


class DeviceDB(Base):
    __tablename__ = "device_table"

    device_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    devicename: Mapped[str] = mapped_column()
    vertexpool_id: Mapped[int] = mapped_column(ForeignKey("vertexpool_table.id"))
    ip: Mapped[str] = mapped_column(nullable=True, default=None)
    vertexpool: Mapped[VertexpoolDB] = relationship(
        back_populates="devices",
    )
    labels: Mapped[list["Device_LabelDB"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Device_LabelDB(Base):
    __tablename__ = "device_label_table"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device_table.device_id"))
    key: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()
    device: Mapped[DeviceDB] = relationship(back_populates="labels")


class NodeDB(Base):
    __tablename__ = "node_table"

    nodename: Mapped[str] = mapped_column(primary_key=True)
    vertexpool_id: Mapped[int] = mapped_column(ForeignKey("vertexpool_table.id"))
    ip: Mapped[str] = mapped_column(nullable=True, default=None)
    vertexpool: Mapped[VertexpoolDB] = relationship(
        back_populates="nodes",
    )
