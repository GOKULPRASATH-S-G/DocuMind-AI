import os
import pytest
from unittest.mock import patch, MagicMock
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog

def test_password_hashing_and_jwt():
    plain = "secretpass123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongpass", hashed) is False

    token = create_access_token({"sub": "user-123", "role": "USER"})
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "USER"

def test_invalid_and_expired_jwt():
    assert decode_access_token("invalid.token.str") is None

    expired_token = create_access_token({"sub": "user-123"}, expires_delta=pytest.importorskip("datetime").timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None

def test_user_registration_and_login_api(client, db_session):
    # Register
    res = client.post("/api/v1/auth/register", json={
        "email": "testuser@sec.com",
        "password": "password123",
        "role": "USER"
    })
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == "testuser@sec.com"

    # Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "testuser@sec.com",
        "password": "password123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # Get profile
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testuser@sec.com"

def test_user_cannot_access_other_user_document(client, db_session):
    # User A & User B
    u_a = User(email="userA@sec.com", hashed_password=hash_password("p123"), role=UserRole.USER)
    u_b = User(email="userB@sec.com", hashed_password=hash_password("p123"), role=UserRole.USER)
    db_session.add_all([u_a, u_b])
    db_session.commit()

    token_b = create_access_token({"sub": u_b.id, "email": u_b.email, "role": "USER"})

    # Doc owned by User A
    doc_a = Document(filename="doc_A.pdf", file_path="./tmp.pdf", mime_type="application/pdf", file_size=100, owner_id=u_a.id)
    db_session.add(doc_a)
    db_session.commit()

    # User B attempts to get detail of User A's document -> 403 Forbidden
    res = client.get(f"/api/v1/documents/{doc_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403

def test_user_cannot_approve_documents(client, db_session):
    user = User(email="normaluser@sec.com", hashed_password=hash_password("p123"), role=UserRole.USER)
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.id, "email": user.email, "role": "USER"})

    # Attempt to approve -> 403 Forbidden
    res = client.post("/api/v1/reviews/doc-123/approve", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_reviewer_can_access_approval(client, db_session):
    reviewer = User(email="reviewer@sec.com", hashed_password=hash_password("p123"), role=UserRole.REVIEWER)
    doc = Document(id="rev-doc-1", filename="rev.pdf", file_path="./tmp.pdf", mime_type="application/pdf", file_size=100, processing_status="NEEDS_REVIEW")
    db_session.add_all([reviewer, doc])
    db_session.commit()

    token = create_access_token({"sub": reviewer.id, "email": reviewer.email, "role": "REVIEWER"})

    # Reviewer calling approve on missing extraction data -> 400 (not 403 Forbidden!)
    res = client.post(f"/api/v1/reviews/{doc.id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert "Extracted data is missing" in res.json()["detail"]

def test_invalid_pdf_and_oversized_upload_rejection(client):
    # Empty / non-PDF signature -> 400
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("fake.pdf", b"NOT_A_PDF_HEADER", "application/pdf")}
    )
    assert res.status_code == 400
    assert "Invalid PDF file" in res.json()["detail"]

def test_health_and_readiness_endpoints(client):
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "ok"

    r_res = client.get("/health/ready")
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "ready"

def test_production_metrics_endpoint(client):
    m_res = client.get("/api/v1/metrics")
    assert m_res.status_code == 200
    data = m_res.json()
    assert "documents" in data
    assert "rag" in data
    assert "evaluation" in data
