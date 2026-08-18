from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class PaymentSubmissionResponse(BaseModel):
    status: str
    confidence_score: float
    decision_reasons: Dict[str, str]
    customer_message: str

class SMSWebhookPayload(BaseModel):
    sender: str
    message_text: str
    timestamp: Optional[datetime] = None

class SMSWebhookResponse(BaseModel):
    status: str
    matched_payment_id: Optional[int] = None

class OrderSchema(BaseModel):
    id: str
    customer_name: str
    phone: Optional[str] = None
    expected_amount: float
    currency: str

    class Config:
        from_attributes = True

class PaymentResponseSchema(BaseModel):
    id: int
    order_id: str
    image_path: str
    extracted_amount: Optional[float]
    extracted_ref_id: Optional[str]
    ocr_boxes: Optional[List] = None
    ela_score: Optional[float] = None
    ela_image_path: Optional[str] = None
    verification_status: str
    confidence_score: float
    decision_reasons: Dict
    customer_reply: Optional[str] = None
    processed_at: datetime
    order: Optional[OrderSchema] = None

    class Config:
        from_attributes = True

class ManualOverrideRequest(BaseModel):
    action: str
    reason: str

class CustomerRiskProfileSchema(BaseModel):
    id: int
    customer_name: str
    customer_phone: Optional[str] = None
    total_submissions: int
    approved_count: int
    rejected_count: int
    flagged_count: int
    risk_score: float
    risk_level: str
    last_flagged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerHistoryResponse(BaseModel):
    risk_profile: Optional[CustomerRiskProfileSchema] = None
    payments: List[PaymentResponseSchema] = []
