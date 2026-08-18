from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String)
    customer_name: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    expected_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="LKR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="PENDING")  # PENDING, PAID, FAILED
    
    payments: Mapped[List["Payment"]] = relationship(back_populates="order")

class Payment(Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    image_path: Mapped[str] = mapped_column(String)
    phash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    md5_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    extracted_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_ref_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extracted_account: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_boxes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    ela_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ela_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    verification_status: Mapped[str] = mapped_column(String)  # APPROVED, REJECTED, NEEDS VERIFICATION
    confidence_score: Mapped[float] = mapped_column(Float)
    decision_reasons: Mapped[Dict] = mapped_column(JSON)
    customer_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    order: Mapped["Order"] = relationship(back_populates="payments")
    sms_matches: Mapped[List["BankSMS"]] = relationship(back_populates="matched_payment")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="payment")

class BankSMS(Base):
    __tablename__ = "bank_sms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(Text)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    account_tail: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    matched_payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"), nullable=True)
    matched_payment: Mapped[Optional["Payment"]] = relationship(back_populates="sms_matches")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"))
    action: Mapped[str] = mapped_column(String) # APPROVE, REJECT, SYSTEM_PROCESS
    performed_by: Mapped[str] = mapped_column(String) # SYSTEM, HUMAN
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    payment: Mapped["Payment"] = relationship(back_populates="audit_logs")

class CustomerRiskProfile(Base):
    __tablename__ = "customer_risk_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String, unique=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_submissions: Mapped[int] = mapped_column(Integer, default=0)
    approved_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    flagged_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    risk_level: Mapped[str] = mapped_column(String, default="LOW")  # LOW, MEDIUM, HIGH, BLACKLISTED
    last_flagged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
