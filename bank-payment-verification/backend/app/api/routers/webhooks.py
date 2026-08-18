from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import BankSMS, Payment
from app.api.schemas import SMSWebhookPayload, SMSWebhookResponse
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/sms-webhook", response_model=SMSWebhookResponse)
async def sms_webhook(payload: SMSWebhookPayload, db: Session = Depends(get_db)):
    # Very basic parsing, assuming amount and ref_id can be pulled from raw text
    import re
    amount_matches = re.findall(r'[\d,]+\.\d{2}', payload.message_text)
    amount = float(amount_matches[0].replace(',', '')) if amount_matches else None
    
    ref_matches = re.findall(r'\b[A-Za-z0-9]{6,16}\b', payload.message_text)
    ref_id = next((m for m in ref_matches if not re.match(r'^\d+$', m) and len(m) >= 6), None)
    if not ref_id and ref_matches:
         ref_id = ref_matches[0]
         
    sms = BankSMS(
        sender=payload.sender,
        raw_text=payload.message_text,
        amount=amount,
        ref_id=ref_id,
        received_at=payload.timestamp or datetime.utcnow()
    )
    
    # Try to auto-match with pending payments
    matched_payment_id = None
    if ref_id:
        payment = db.query(Payment).filter(Payment.extracted_ref_id == ref_id).first()
        if payment:
            sms.matched_payment_id = payment.id
            matched_payment_id = payment.id
            if payment.verification_status == "NEEDS VERIFICATION":
                payment.verification_status = "APPROVED"
                payment.confidence_score += 0.3
                payment.decision_reasons["SMS"] = "Late SMS match found"
    
    db.add(sms)
    db.commit()
    
    return SMSWebhookResponse(status="success", matched_payment_id=matched_payment_id)
