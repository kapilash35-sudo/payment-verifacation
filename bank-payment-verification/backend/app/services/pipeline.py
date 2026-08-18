import os
import cv2
import easyocr
import numpy as np
import imagehash
from PIL import Image, ImageChops, ImageEnhance
import hashlib
import re
import json
from groq import Groq
from sqlalchemy.orm import Session
from app.db.models import Payment, Order, BankSMS, CustomerRiskProfile
from datetime import datetime, timedelta
import logging
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (this will download models if not present)
reader = easyocr.Reader(['en'], gpu=False)

# Configure Groq Client
groq_api_key = os.environ.get("GROQ_API_KEY", "dummy")
client = Groq(api_key=groq_api_key)

def compute_hashes(image_path: str):
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    md5_hash = hashlib.md5(img_bytes).hexdigest()
    
    pil_image = Image.open(image_path)
    phash = str(imagehash.phash(pil_image))
    return phash, md5_hash

def preprocess_image(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # 1. Grayscale-ஆக மாற்றுதல்
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. CLAHE மூலம் Contrast-ஐ அதிகரிக்கவும் (எழுத்துகள் தெளிவாகத் தெரிய)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 3. Noise-ஐக் குறைப்பது (Denoising)
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    
    # 4. Resize (எழுத்துகள் சிறியதாக இருந்தால் தெளிவுபடுத்த 2x பெரிதாக்குதல்)
    resized = cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    return resized

def detect_blur(image_path: str, threshold: float = 100.0) -> bool:
    """Detect if an image is blurry using Laplacian variance.
    Returns True if the image is blurry (below threshold).
    A typical clear document scores 300-1000+, blurry ones score < 100.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return True  # Can't read image = treat as blurry
    laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
    logger.info(f"Blur score (Laplacian variance): {laplacian_var:.2f} (threshold: {threshold})")
    return laplacian_var < threshold

def compute_ela(image_path: str, quality: int = 90):
    """Error Level Analysis - detects image tampering.
    Re-saves image at known quality and computes pixel-level difference.
    High differences in specific areas = possible tampering.
    Returns (ela_score, ela_image_path).
    """
    try:
        original = Image.open(image_path).convert("RGB")
        
        # Re-save at known JPEG quality
        ela_temp_path = image_path + "_ela_temp.jpg"
        original.save(ela_temp_path, 'JPEG', quality=quality)
        resaved = Image.open(ela_temp_path)
        
        # Compute pixel-level difference
        ela_image = ImageChops.difference(original, resaved)
        
        # Amplify differences for visibility
        extrema = ela_image.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        scale = 255.0 / max_diff
        ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
        
        # Save ELA heatmap image
        base, ext = os.path.splitext(image_path)
        ela_save_path = base + "_ela.png"
        ela_image.save(ela_save_path)
        
        # Compute tampering score (mean pixel intensity of ELA)
        ela_array = np.array(ela_image)
        mean_ela = float(np.mean(ela_array))
        
        # Clean up temp file
        os.remove(ela_temp_path)
        
        logger.info(f"ELA Score: {mean_ela:.2f} (higher = more suspicious)")
        return mean_ela, ela_save_path
    except Exception as e:
        logger.error(f"ELA computation failed: {e}")
        return 0.0, None

def extract_text(image_path: str):
    img = preprocess_image(image_path)
    if img is None:
        return None, None, "", []
        
    results = reader.readtext(img, allowlist='0123456789.,ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:-/')
    full_text = " ".join([res[1] for res in results])
    
    ocr_boxes = []
    for res in results:
        # Bounding boxes அளவு 2x பெரிதாக்கப்பட்டதால், அவற்றை ஒரிஜினல் அளவுக்கு மாற்ற 2ஆல் வகுக்கிறோம்
        box = [[float(p[0])/2.0, float(p[1])/2.0] for p in res[0]]
        ocr_boxes.append({"box": box, "text": res[1], "confidence": float(res[2])})
    
    # 1. முதலில் LKR அல்லது Rs உடன் உள்ள தொகையைத் தேடுதல்
    amount_matches = re.findall(r'(?:LKR|Rs\.?)\s*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
    
    if not amount_matches:
        # 2. அல்லது டெசிமலுடன் கூடிய பெரிய எண்களைத் தேடுதல்
        all_nums = re.findall(r'\b\d{4,}(?:,\d{3})*(?:\.\d{2})?\b', full_text)
        if all_nums:
            amount_matches = all_nums

    amount = None
    if amount_matches:
        clean_amount_str = amount_matches[0].replace(',', '')
        try:
            amount = float(clean_amount_str)
        except ValueError:
            amount = None
    
    # Reference ID: 6 to 16 alphanumeric
    ref_matches = re.findall(r'\b[A-Za-z0-9]{6,16}\b', full_text)
    ref_id = next((m for m in ref_matches if not re.match(r'^\d+$', m) and len(m) >= 6), None)
    if not ref_id and ref_matches:
         ref_id = ref_matches[0]
         
    return amount, ref_id, full_text, ocr_boxes

def escalate_to_ai(image_path: str, extracted_text: str = ""):
    """Groq API (llama-3.1-8b-instant) Fallback"""
    if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "dummy":
        logger.warning("Groq API key missing, skipping AI escalation.")
        return None, None, False
        
    try:
        prompt = f"""
        Analyze this bank payment slip OCR text:
        "{extracted_text}"
        
        Extract the exact amount paid (as a float number) and the transaction reference ID.
        Also determine if the slip looks authentic or tampered with (true/false).
        Respond in strict JSON format only, with no extra text: 
        {{"amount": 25000.0, "ref_id": "ABC12345", "is_authentic": true, "reason": "Looks clean"}}
        """

        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Updated active Groq model
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.1
        )
        
        response_text = chat_completion.choices[0].message.content
        json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
        data = json.loads(json_str)
        return data.get("amount"), data.get("ref_id"), data.get("is_authentic", True)
    except Exception as e:
        logger.error(f"Groq AI Escalation failed: {e}")
        return None, None, False

def get_customer_risk(db: Session, customer_name: str):
    """Get or create customer risk profile and return risk adjustment."""
    profile = db.query(CustomerRiskProfile).filter(
        CustomerRiskProfile.customer_name == customer_name
    ).first()
    
    if not profile:
        return 0.0, "LOW", None
    
    return profile.risk_score, profile.risk_level, profile

def update_customer_risk(db: Session, order: Order, verification_status: str):
    """Update customer risk profile after each verification."""
    profile = db.query(CustomerRiskProfile).filter(
        CustomerRiskProfile.customer_name == order.customer_name
    ).first()
    
    if not profile:
        profile = CustomerRiskProfile(
            customer_name=order.customer_name,
            customer_phone=order.phone
        )
        db.add(profile)
    
    profile.total_submissions += 1
    
    if verification_status == "APPROVED":
        profile.approved_count += 1
    elif verification_status == "REJECTED":
        profile.rejected_count += 1
        profile.flagged_count += 1
        profile.last_flagged_at = datetime.utcnow()
    elif verification_status == "NEEDS VERIFICATION":
        profile.flagged_count += 1
    
    if profile.total_submissions > 0:
        fraud_ratio = profile.rejected_count / profile.total_submissions
        flag_ratio = profile.flagged_count / profile.total_submissions
        profile.risk_score = round(min(1.0, (fraud_ratio * 0.7) + (flag_ratio * 0.3)), 2)
    
    if profile.risk_score >= 0.7 or profile.rejected_count >= 5:
        profile.risk_level = "BLACKLISTED"
    elif profile.risk_score >= 0.5 or profile.rejected_count >= 3:
        profile.risk_level = "HIGH"
    elif profile.risk_score >= 0.3 or profile.rejected_count >= 2:
        profile.risk_level = "MEDIUM"
    else:
        profile.risk_level = "LOW"
    
    db.commit()
    return profile

def verify_payment(db: Session, order: Order, image_path: str):
    reasons = {}
    confidence = 1.0
    status = "APPROVED"
    customer_msg = "Your payment has been verified."
    ela_score = 0.0
    ela_image_path = None
    
    # Step 0: Blur Detection
    if detect_blur(image_path):
        return (
            "NEEDS VERIFICATION", 0.2,
            {"Blur": "Image is too blurry to read. Auto-requested resend."},
            "⚠️ Your payment slip image is too blurry and we cannot read it clearly. "
            "Please take a new, clear photo of your payment slip and resend it.",
            None, None, None, None, None, [], 0.0, None
        )
    
    # Step 0.5: ELA Tampering Detection
    ela_score, ela_image_path = compute_ela(image_path)
    if ela_score > 40.0:
        confidence -= 0.3
        reasons["ELA"] = f"Image tampering suspected (ELA score: {ela_score:.1f})"
        if ela_score > 60.0:
            return (
                "REJECTED", 0.1,
                {"ELA": f"High probability of image tampering detected (ELA score: {ela_score:.1f})"},
                "⚠️ Your payment slip appears to have been digitally edited or tampered with.",
                None, None, None, None, None, [], ela_score, ela_image_path
            )
    
    # Step 0.7: Customer Risk Check
    risk_score, risk_level, risk_profile = get_customer_risk(db, order.customer_name)
    if risk_level == "BLACKLISTED":
        confidence -= 0.5
        reasons["Risk"] = f"Customer is BLACKLISTED (risk score: {risk_score})"
    elif risk_level == "HIGH":
        confidence -= 0.3
        reasons["Risk"] = f"High-risk customer (risk score: {risk_score})"
    elif risk_level == "MEDIUM":
        confidence -= 0.15
        reasons["Risk"] = f"Medium-risk customer (risk score: {risk_score})"
    
    # Step 1: Hashing
    phash, md5_hash = compute_hashes(image_path)
    
    existing_payment = db.query(Payment).filter(Payment.md5_hash == md5_hash).first()
    if existing_payment:
        return "REJECTED", 0.0, {"Duplicate": "Exact image duplicate found."}, "Your slip was flagged as a duplicate.", None, None, None, phash, md5_hash, [], ela_score, ela_image_path
    
    past_payments = db.query(Payment).filter(Payment.phash.isnot(None)).all()
    for past_p in past_payments:
        if imagehash.hex_to_hash(past_p.phash) - imagehash.hex_to_hash(phash) <= 5:
            return "REJECTED", 0.0, {"Duplicate": "Slightly modified duplicate slip found."}, "Your slip was flagged as a duplicate.", None, None, None, phash, md5_hash, [], ela_score, ela_image_path

    # Step 2: OCR
    amount, ref_id, raw_text, ocr_boxes = extract_text(image_path)
    
    if not amount:
        # Fallback to Groq AI
        ai_amount, ai_ref, is_auth = escalate_to_ai(image_path, raw_text)
        if ai_amount:
            amount = ai_amount
            ref_id = ai_ref or ref_id
            confidence -= 0.2
            reasons["OCR"] = "Amount extracted via Groq AI Fallback"
        else:
            return "NEEDS VERIFICATION", 0.3, {"OCR": "Could not extract amount"}, "We are manually reviewing your payment.", amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path

    # Step 3: Rules
    if amount != order.expected_amount:
        return "REJECTED", 0.1, {"Amount": f"Expected {order.expected_amount}, found {amount}"}, "The payment amount does not match the order.", amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path
    
    if ref_id:
        existing_ref = db.query(Payment).filter(Payment.extracted_ref_id == ref_id).first()
        if existing_ref:
             return "REJECTED", 0.0, {"RefID": "Reference ID already used"}, "This transaction reference has already been used.", amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path
             
    if "987654321" not in raw_text.replace(" ", ""):
        return "REJECTED", 0.1, {"Account": "Destination account does not match business account"}, "The payment was made to an incorrect bank account.", amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path
        
    date_matches = re.findall(r'\d{4}-\d{2}-\d{2}', raw_text)
    if date_matches:
        try:
            slip_date = datetime.strptime(date_matches[0], "%Y-%m-%d")
            if (order.created_at - slip_date).days > 7:
                 return "REJECTED", 0.1, {"Date": "Stale payment slip"}, "The payment slip date is too old.", amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path
        except:
            pass
             
    # Step 4: SMS Evidence
    sms_match = None
    if ref_id:
        sms_match = db.query(BankSMS).filter(BankSMS.ref_id == ref_id).first()
    if not sms_match and amount:
        time_threshold = datetime.utcnow() - timedelta(hours=24)
        sms_match = db.query(BankSMS).filter(BankSMS.amount == amount, BankSMS.received_at >= time_threshold).first()
    
    if sms_match:
        confidence += 0.3
        reasons["SMS"] = "Matched with Bank SMS"
    else:
        confidence -= 0.2
        reasons["SMS"] = "No matching Bank SMS found yet."
        if confidence < 0.7:
             status = "NEEDS VERIFICATION"
             customer_msg = "We are waiting for bank confirmation to verify your payment."
             
    confidence = min(max(confidence, 0.0), 1.0)
    
    return status, confidence, reasons, customer_msg, amount, ref_id, raw_text, phash, md5_hash, ocr_boxes, ela_score, ela_image_path