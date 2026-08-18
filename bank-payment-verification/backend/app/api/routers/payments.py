from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.db.models import Order, Payment, AuditLog
from app.api.schemas import PaymentSubmissionResponse, PaymentResponseSchema, ManualOverrideRequest
from app.services.pipeline import verify_payment, update_customer_risk
from app.api.routers.websocket import manager
import os
import shutil

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/submit-payment", response_model=PaymentSubmissionResponse)
async def submit_payment(
    order_id: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Save image
    file_path = os.path.join(UPLOAD_DIR, image.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    # Verify
    status, conf, reasons, msg, amount, ref, raw_txt, phash, md5, ocr_boxes, ela_score, ela_image_path = verify_payment(db, order, file_path)
    
    # Save to DB
    payment = Payment(
        order_id=order.id,
        image_path=file_path,
        phash=phash,
        md5_hash=md5,
        extracted_amount=amount,
        extracted_ref_id=ref,
        raw_ocr_text=raw_txt,
        ocr_boxes=ocr_boxes,
        ela_score=ela_score,
        ela_image_path=ela_image_path,
        verification_status=status,
        confidence_score=conf,
        decision_reasons=reasons,
        customer_reply=msg
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Update customer risk profile
    update_customer_risk(db, order, status)
    
    # Broadcast via WebSocket
    await manager.broadcast({
        "type": "new_payment",
        "payment_id": payment.id,
        "order_id": order.id,
        "customer_name": order.customer_name,
        "status": status,
        "confidence": conf,
        "amount": amount
    })
    
    return PaymentSubmissionResponse(
        status=status,
        confidence_score=conf,
        decision_reasons=reasons,
        customer_message=msg
    )

@router.get("/payments")
async def get_payments(status: str = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.verification_status == status)
    payments = (
        query.options(joinedload(Payment.order))
        .order_by(Payment.processed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return payments

@router.post("/payments/{payment_id}/manual-override")
async def manual_override(payment_id: int, request: ManualOverrideRequest, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    old_status = payment.verification_status
    payment.verification_status = request.action
    payment.decision_reasons["ManualOverride"] = request.reason
    
    audit_log = AuditLog(
        payment_id=payment.id,
        action=request.action,
        performed_by="HUMAN",
        notes=request.reason
    )
    db.add(audit_log)
    
    # Update customer risk based on manual override
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        update_customer_risk(db, order, request.action)
    
    db.commit()
    
    # Broadcast status change via WebSocket
    await manager.broadcast({
        "type": "status_changed",
        "payment_id": payment.id,
        "old_status": old_status,
        "new_status": request.action
    })
    
    return {"message": "Success"}
