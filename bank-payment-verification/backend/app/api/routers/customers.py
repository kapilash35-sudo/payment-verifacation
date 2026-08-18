from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.db.models import CustomerRiskProfile, Payment, Order
from app.api.schemas import CustomerRiskProfileSchema, CustomerHistoryResponse, PaymentResponseSchema

router = APIRouter()

@router.get("/customers", response_model=list[CustomerRiskProfileSchema])
async def get_all_customers(db: Session = Depends(get_db)):
    """Get all customer risk profiles sorted by risk score (highest first)."""
    profiles = db.query(CustomerRiskProfile).order_by(
        CustomerRiskProfile.risk_score.desc()
    ).all()
    return profiles

@router.get("/customers/{customer_name}/history", response_model=CustomerHistoryResponse)
async def get_customer_history(customer_name: str, db: Session = Depends(get_db)):
    """Get a customer's risk profile and full payment history."""
    # Get risk profile
    profile = db.query(CustomerRiskProfile).filter(
        CustomerRiskProfile.customer_name == customer_name
    ).first()
    
    # Get all orders for this customer
    orders = db.query(Order).filter(Order.customer_name == customer_name).all()
    order_ids = [o.id for o in orders]
    
    # Get all payments for those orders
    payments = []
    if order_ids:
        payments = (
            db.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.order_id.in_(order_ids))
            .order_by(Payment.processed_at.desc())
            .all()
        )
    
    return CustomerHistoryResponse(
        risk_profile=profile,
        payments=payments
    )
