from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    report_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 上报间隔(秒)，null 使用默认值
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    domains: Mapped[list["Domain"]] = relationship("Domain", back_populates="machine", cascade="all, delete-orphan")
    ip_history: Mapped[list["IPHistory"]] = relationship("IPHistory", back_populates="machine", cascade="all, delete-orphan")


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(Integer, ForeignKey("machines.id"), nullable=False)
    domain_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    machine: Mapped[Machine] = relationship("Machine", back_populates="domains")


class IPHistory(Base):
    __tablename__ = "ip_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(Integer, ForeignKey("machines.id"), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    machine: Mapped[Machine] = relationship("Machine", back_populates="ip_history")
