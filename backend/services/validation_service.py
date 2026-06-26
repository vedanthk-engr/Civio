import os
import json
import base64
import io
import re
import pickle
import pathlib
from typing import Optional, List
from PIL import Image, ExifTags
import imagehash

from backend.services.gemini_service import gemini_configured, model_name

# Configure genai if imported
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Keywords for Layer 1 Spam/Test Pre-Filter
_SPAM_KW = [
    'alien', 'aliens', 'ufo', 'martian', 'zombie', 'vampire', 'dragon', 'unicorn',
    'ghost haunt', 'haunted', 'demon', 'witch', 'wormhole', 'time travel',
    'buy now', 'click here', 'free money', 'lottery', 'win prize',
    'lorem ipsum', 'asdf qwerty'
]
_TEST_KW = ['test test', 'testing 123', 'abc def', 'just testing', 'ignore this']

# Load Pre-trained Spam Classifier Model
_spam_pipeline = None
try:
    _MODEL_PATH = pathlib.Path(__file__).parent.parent / "models" / "spam_clf.pkl"
    if _MODEL_PATH.exists():
        with open(_MODEL_PATH, 'rb') as f:
            _spam_pipeline = pickle.load(f)
        print("[validation_service] Loaded offline spam classifier ML model successfully.")
except Exception as e:
    print(f"[validation_service] Failed to load offline spam classifier: {e}")

def compute_image_hash(image_data_url_or_base64: str) -> Optional[str]:
    """
    Computes a 64-bit perceptual hash (pHash) of an image encoded in base64.
    """
    try:
        # Extract base64 encoded data
        if image_data_url_or_base64.startswith("data:image/"):
            _, encoded = image_data_url_or_base64.split(",", 1)
        else:
            encoded = image_data_url_or_base64
            
        raw = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        return str(imagehash.phash(img))
    except Exception as e:
        print(f"[validation_service] Failed to compute image hash: {e}")
        return None

def is_duplicate_image(new_hash: str, stored_hashes: List[str], threshold: int = 10) -> dict:
    """
    Compares a new image hash against a list of stored hashes using Hamming distance.
    """
    if not new_hash or not stored_hashes:
        return {'is_duplicate': False, 'distance': None, 'matched_hash': None}
    
    try:
        h_new = imagehash.hex_to_hash(new_hash)
        for s_hash in stored_hashes:
            if not s_hash:
                continue
            h_stored = imagehash.hex_to_hash(s_hash)
            dist = h_new - h_stored  # Hamming distance
            if dist <= threshold:
                return {'is_duplicate': True, 'distance': dist, 'matched_hash': s_hash}
    except Exception as e:
        print(f"[validation_service] Error during hash comparison: {e}")
        
    return {'is_duplicate': False, 'distance': None, 'matched_hash': None}

def classify_spam(description: str) -> dict:
    """
    3-layer spam check:
      Layer 1: Hard keyword match (instant)
      Layer 2: Offline scikit-learn TF-IDF + Logistic Regression ML pipeline
      Layer 3: Gemini 2.0 Flash classification (LLM fallback)
    """
    text = (description or '').strip()
    tl = text.lower()
    
    # Layer 1: Keywords
    for kw in _SPAM_KW:
        if kw in tl:
            return {'verdict': 'spam', 'confidence': 95, 'reason': f'Contains spam keyword: "{kw}"'}
    for kw in _TEST_KW:
        if kw in tl:
            return {'verdict': 'test', 'confidence': 92, 'reason': 'Test-pattern submission'}
            
    # Length validation (fast check)
    if len(text) > 0 and len(text) < 5:
        return {'verdict': 'test', 'confidence': 60, 'reason': 'Text too short'}
        
    # Layer 2: Offline ML Model (trained locally)
    if _spam_pipeline:
        try:
            pred = str(_spam_pipeline.predict([text])[0]).lower()
            proba = _spam_pipeline.predict_proba([text])[0]
            conf = int(max(proba) * 100)
            
            # Map predictions to labels
            # In our dataset: 0=real, 1=spam, 2=abuse, 3=test
            label = {'real': 'real', 'spam': 'spam', 'abuse': 'abuse', 'test': 'test',
                     '0': 'real', '1': 'spam', '2': 'abuse', '3': 'test'}.get(pred, 'real')
            
            if conf >= 75:
                return {'verdict': label, 'confidence': conf, 'reason': 'Offline ML Classifier'}
        except Exception as e:
            print(f"[validation_service] ML prediction failed: {e}")

    # Layer 3: Gemini LLM Fallback
    if gemini_configured and genai and text:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"""
            You are a spam filter for Civio, a community civic issue reporting platform in India.
            Classify the reported issue description text into one of these categories:
            - REAL : A legitimate civic infrastructure issue (e.g. broken road, sewer leak, traffic lights broken).
            - SPAM : Commercial ads, promotional offers, lottery, gibberish, or highly fantastical content (e.g., aliens).
            - ABUSE: Profanity, hate speech, or harassment.
            - TEST : Obvious test values (e.g. "asdf", "hello test", "123").
            
            Description Text: "{text}"
            
            Return ONLY a valid JSON object:
            {{
              "verdict": "REAL" | "SPAM" | "ABUSE" | "TEST",
              "confidence": <integer 0-100>,
              "reason": "short explanation of the decision"
            }}
            """
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            result = json.loads(clean_text)
            return {
                'verdict': result.get('verdict', 'REAL').lower(),
                'confidence': result.get('confidence', 80),
                'reason': result.get('reason', 'Gemini analysis')
            }
        except Exception as e:
            print(f"[validation_service] LLM spam check failed: {e}")
            
    return {'verdict': 'real', 'confidence': 50, 'reason': 'Default approval'}

def _check_exif(image_b64: str) -> dict:
    """
    Check if a base64 encoded image has standard device EXIF metadata tags.
    AI generated images from DALL-E/Midjourney/SD typically lack EXIF camera/GPS tags.
    """
    signals = []
    try:
        # Decode base64
        if image_b64.startswith("data:image/"):
            _, encoded = image_b64.split(",", 1)
        else:
            encoded = image_b64
        raw = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(raw))
        fmt = getattr(img, 'format', '') or ''
        
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        
        if exif_data is None:
            signals.append('No EXIF metadata found')
            if fmt.upper() == 'PNG':
                signals.append('PNG format (typical AI export)')
                return {'is_ai_generated': True, 'confidence': 75, 'method': 'exif-check', 'signals': signals}
            return {'is_ai_generated': True, 'confidence': 68, 'method': 'exif-check', 'signals': signals}
            
        tag_names = {ExifTags.TAGS.get(k, ''): v for k, v in exif_data.items()}
        has_make = bool(tag_names.get('Make'))
        has_model = bool(tag_names.get('Model'))
        has_gps = bool(tag_names.get('GPSInfo'))
        has_dt = bool(tag_names.get('DateTimeOriginal'))
        score = sum([has_make, has_model, has_gps, has_dt])
        
        if score == 0:
            signals.append('EXIF metadata present but missing all camera info (Make/Model/GPS)')
            return {'is_ai_generated': True, 'confidence': 75, 'method': 'exif-check', 'signals': signals}
        if score >= 3:
            signals.append(f'Real device EXIF: {score}/4 standard fields present')
            return {'is_ai_generated': False, 'confidence': 72, 'method': 'exif-check', 'signals': signals}
    except Exception as e:
        print(f"[validation_service] EXIF check failed: {e}")
        
    return {'is_ai_generated': False, 'confidence': 25, 'method': 'exif-unavailable', 'signals': []}

def detect_ai_image(image_b64: str, mime: str = 'image/jpeg') -> dict:
    """
    2-Layer AI-image detection:
      Layer 1: EXIF check (instant)
      Layer 2: Gemini 2.0 Flash Vision check (highly accurate)
    """
    # Layer 1: EXIF Metadata Check
    exif = _check_exif(image_b64)
    if exif['is_ai_generated'] and exif['confidence'] >= 75:
        return exif
        
    # Layer 2: Gemini Vision Check
    if gemini_configured and genai and image_b64:
        try:
            # Prepare image
            if image_b64.startswith("data:image/"):
                _, encoded = image_b64.split(",", 1)
            else:
                encoded = image_b64
            img_data = base64.b64decode(encoded)
            
            model = genai.GenerativeModel(model_name)
            prompt = """
            Analyze the attached image and determine if it is an AI-generated/synthetic image or a real photo.
            Real photos have camera artifacts, lens noise, realistic textures, and complex lighting.
            AI images often show hyper-clean lines, unnatural smooth skin/plastic textures, text gibberish, or lighting inconsistencies.
            
            Return ONLY a JSON object:
            {
              "is_ai_generated": true | false,
              "confidence": <integer 0-100>,
              "signals": ["list of reasons/visual clues noticed"]
            }
            """
            response = model.generate_content([
                prompt,
                {"mime_type": mime, "data": img_data}
            ])
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            result = json.loads(clean_text)
            return {
                'is_ai_generated': bool(result.get('is_ai_generated', False)),
                'confidence': int(result.get('confidence', 60)),
                'method': 'gemini-vision',
                'signals': result.get('signals', [])
            }
        except Exception as e:
            print(f"[validation_service] Gemini AI image check failed: {e}")
            
    return exif

def check_cross_modal_consistency(
    image_category: str,
    user_description: str,
    image_data_url_or_base64: Optional[str] = None
) -> dict:
    """
    Ensures the user's description is consistent with the visual category identified by the model.
    """
    # Quick Synonym Check (free/instant)
    # Mapping of closely related tags that should not trigger mismatch errors
    synonyms = {
        'POTHOLE': {'POTHOLE', 'ROAD_DAMAGE', 'OTHER'},
        'WATER_LEAK': {'WATER_LEAK', 'SEWAGE', 'OTHER'},
        'SEWAGE': {'SEWAGE', 'WATER_LEAK', 'OTHER'},
        'STREETLIGHT': {'STREETLIGHT', 'ELECTRICAL', 'OTHER'},
        'ELECTRICAL': {'ELECTRICAL', 'STREETLIGHT', 'OTHER'},
        'WASTE': {'WASTE', 'OTHER'},
        'ROAD_DAMAGE': {'ROAD_DAMAGE', 'POTHOLE', 'OTHER'},
        'ENCROACHMENT': {'ENCROACHMENT', 'OTHER'},
        'OTHER': set()
    }
    
    desc_clean = user_description.lower().strip()
    img_cat_upper = image_category.upper().strip()
    
    # Simple keyword matches that pass directly
    for syn in synonyms.get(img_cat_upper, {img_cat_upper}):
        if syn.lower().replace('_', ' ') in desc_clean or desc_clean in syn.lower().replace('_', ' '):
            return {'approved': True, 'reason': 'Keywords match synonym category.'}
            
    # LLM Verification fallback if mismatch is suspected
    if gemini_configured and genai and image_data_url_or_base64:
        try:
            # Decode base64 or prepare content
            img_data = None
            mime_type = "image/jpeg"
            
            if image_data_url_or_base64.startswith("data:image/"):
                header, encoded = image_data_url_or_base64.split(",", 1)
                img_data = base64.b64decode(encoded)
                mime_type = header.split(";")[0].split(":")[1]
            else:
                img_data = base64.b64decode(image_data_url_or_base64)
                
            model = genai.GenerativeModel(model_name)
            prompt = f"""
            You are a validation system for a civic issue reporting app.
            Analyze the attached image and the user's description.
            
            User Description: "{user_description}"
            Assigned Category: "{image_category}"
            
            Determine if the user's description is consistent with or describes what is actually shown in the image.
            Return a JSON object:
            {{
              "approved": true | false,
              "reason": "brief reason for decision"
            }}
            """
            response = model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": img_data}
            ])
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            return json.loads(clean_text)
        except Exception as e:
            print(f"[validation_service] LLM consistency check failed: {e}")
            
    return {'approved': True, 'reason': 'Consistency check passed by default.'}
