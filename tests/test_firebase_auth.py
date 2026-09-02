import pytest
import json
import base64
import time
from app.services.firebase_auth import FirebaseTokenVerifier

def create_mock_jwt(payload_dict):
    header = json.dumps({"alg": "RS256", "typ": "JWT"}).encode('utf-8')
    header_b64 = base64.urlsafe_b64encode(header).decode('utf-8').rstrip('=')

    payload = json.dumps(payload_dict).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload).decode('utf-8').rstrip('=')

    signature_b64 = "mock_signature_bytes"
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def test_firebase_token_verifier():
    # Valid JWT mock with email_verified claim
    payload = {
        "user_id": "firebase_user_99812",
        "email": "sarah.johnson@example.com",
        "email_verified": True,
        "name": "Sarah Johnson",
        "exp": int(time.time()) + 3600,
        "firebase": {"sign_in_provider": "google.com"}
    }
    jwt_token = create_mock_jwt(payload)

    claims = FirebaseTokenVerifier.verify_id_token(jwt_token)
    assert claims["uid"] == "firebase_user_99812"
    assert claims["email"] == "sarah.johnson@example.com"
    assert claims["email_verified"] is True
    assert claims["name"] == "Sarah Johnson"
    assert claims["auth_provider"] == "google.com"

def test_unverified_email_token():
    payload = {
        "user_id": "firebase_user_unverified",
        "email": "unverified@example.com",
        "email_verified": False,
        "exp": int(time.time()) + 3600
    }
    jwt_token = create_mock_jwt(payload)

    claims = FirebaseTokenVerifier.verify_id_token(jwt_token)
    assert claims["email_verified"] is False

def test_expired_token_handling():
    payload = {
        "user_id": "firebase_user_expired",
        "email": "expired@example.com",
        "exp": int(time.time()) - 3600
    }
    jwt_token = create_mock_jwt(payload)

    with pytest.raises(Exception):
        FirebaseTokenVerifier.verify_id_token(jwt_token)
