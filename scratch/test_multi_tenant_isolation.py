"""Automated Multi-Tenant Isolation & Security Test Suite for DocuChat-AI.

Tests:
1. Password hashing & authentication (JWT issuance, verification, /auth/me).
2. Conversation IDOR protection & tenant scoping (list, get, delete).
3. Knowledge Base & Document multi-tenant isolation (list, upload, delete).
4. Chat isolation (unauthenticated rejection, cross-tenant conversation injection prevention).
"""
import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def log_test(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name} {f'({details})' if details else ''}")
    if not passed:
        sys.exit(1)

def main():
    print("=" * 70)
    print("🔒 RUNNING DOCUCHAT-AI MULTI-TENANT ISOLATION SECURITY SUITE")
    print("=" * 70)

    client = httpx.Client(timeout=90.0)

    uid_a = uuid.uuid4().hex[:6]
    uid_b = uuid.uuid4().hex[:6]
    email_a = f"alice_{uid_a}@testcorp.io"
    email_b = f"bob_{uid_b}@securenet.io"
    password = "SecurePassword#2026!"

    # -------------------------------------------------------------
    # 1. Unauthenticated endpoints check
    # -------------------------------------------------------------
    r = client.get(f"{BASE_URL}/conversations")
    log_test("Conversations requires authentication (401)", r.status_code == 401, f"Status: {r.status_code}")

    r = client.get(f"{BASE_URL}/documents")
    log_test("Documents requires authentication (401)", r.status_code == 401, f"Status: {r.status_code}")

    r = client.get(f"{BASE_URL}/knowledge-bases")
    log_test("Knowledge Bases requires authentication (401)", r.status_code == 401, f"Status: {r.status_code}")

    r = client.post(f"{BASE_URL}/chat", json={"message": "Hello without auth"})
    log_test("Chat requires authentication (401)", r.status_code == 401, f"Status: {r.status_code}")

    # -------------------------------------------------------------
    # 2. Register & Login User A and User B
    # -------------------------------------------------------------
    r_reg_a = client.post(f"{BASE_URL}/auth/register", json={
        "email": email_a,
        "name": "Alice Tenant",
        "password": password
    })
    log_test("Register User A", r_reg_a.status_code == 200, f"Email: {email_a}")
    user_a = r_reg_a.json()["user"]
    token_a = r_reg_a.json()["access_token"]

    r_reg_b = client.post(f"{BASE_URL}/auth/register", json={
        "email": email_b,
        "name": "Bob Tenant",
        "password": password
    })
    log_test("Register User B", r_reg_b.status_code == 200, f"Email: {email_b}")
    user_b = r_reg_b.json()["user"]
    token_b = r_reg_b.json()["access_token"]

    # Wrong password test
    r_bad_login = client.post(f"{BASE_URL}/auth/login", json={
        "email": email_a,
        "password": "WrongPassword!"
    })
    log_test("Login with wrong password rejected (401)", r_bad_login.status_code == 401)

    # Auth Me check
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r_me_a = client.get(f"{BASE_URL}/auth/me", headers=headers_a)
    log_test("User A /auth/me returns correct identity", r_me_a.status_code == 200 and r_me_a.json()["email"] == email_a)

    r_me_b = client.get(f"{BASE_URL}/auth/me", headers=headers_b)
    log_test("User B /auth/me returns correct identity", r_me_b.status_code == 200 and r_me_b.json()["email"] == email_b)

    # -------------------------------------------------------------
    # 3. Conversation Tenant Isolation & IDOR Prevention
    # -------------------------------------------------------------
    r_conv_a = client.post(f"{BASE_URL}/conversations", json={"title": "Alice Secret Strategy"}, headers=headers_a)
    log_test("Create Conversation for User A", r_conv_a.status_code == 200)
    conv_a_id = r_conv_a.json()["id"]

    r_conv_b = client.post(f"{BASE_URL}/conversations", json={"title": "Bob Audit Report"}, headers=headers_b)
    log_test("Create Conversation for User B", r_conv_b.status_code == 200)
    conv_b_id = r_conv_b.json()["id"]

    # Listing isolation
    r_list_a = client.get(f"{BASE_URL}/conversations", headers=headers_a)
    list_a_ids = [c["id"] for c in r_list_a.json()]
    log_test("User A sees only own conversations", conv_a_id in list_a_ids and conv_b_id not in list_a_ids)

    r_list_b = client.get(f"{BASE_URL}/conversations", headers=headers_b)
    list_b_ids = [c["id"] for c in r_list_b.json()]
    log_test("User B sees only own conversations", conv_b_id in list_b_ids and conv_a_id not in list_b_ids)

    # IDOR Check on GET /{conversation_id}
    r_idor_a_reads_b = client.get(f"{BASE_URL}/conversations/{conv_b_id}", headers=headers_a)
    log_test("IDOR blocked: User A cannot read User B's conversation (404)", r_idor_a_reads_b.status_code == 404)

    r_idor_b_reads_a = client.get(f"{BASE_URL}/conversations/{conv_a_id}", headers=headers_b)
    log_test("IDOR blocked: User B cannot read User A's conversation (404)", r_idor_b_reads_a.status_code == 404)

    # IDOR Check on DELETE /{conversation_id}
    r_idor_del_b_tries_a = client.delete(f"{BASE_URL}/conversations/{conv_a_id}", headers=headers_b)
    log_test("IDOR blocked: User B cannot delete User A's conversation (404)", r_idor_del_b_tries_a.status_code == 404)

    # -------------------------------------------------------------
    # 4. Knowledge Bases Multi-Tenant Isolation
    # -------------------------------------------------------------
    r_kb_a = client.post(f"{BASE_URL}/knowledge-bases", json={"name": "Alice Proprietary IP", "description": "Strictly confidential"}, headers=headers_a)
    log_test("User A creates private Knowledge Base", r_kb_a.status_code == 200)
    kb_a_id = r_kb_a.json()["id"]

    r_kb_list_b = client.get(f"{BASE_URL}/knowledge-bases", headers=headers_b)
    kb_b_ids = [kb["id"] for kb in r_kb_list_b.json()]
    log_test("User B cannot see User A's Knowledge Base in listing", kb_a_id not in kb_b_ids)

    r_idor_kb_get = client.get(f"{BASE_URL}/knowledge-bases/{kb_a_id}", headers=headers_b)
    log_test("IDOR blocked: User B cannot fetch User A's Knowledge Base (404)", r_idor_kb_get.status_code == 404)

    r_idor_kb_del = client.delete(f"{BASE_URL}/knowledge-bases/{kb_a_id}", headers=headers_b)
    log_test("IDOR blocked: User B cannot delete User A's Knowledge Base (404)", r_idor_kb_del.status_code == 404)

    # -------------------------------------------------------------
    # 5. Document Multi-Tenant Isolation
    # -------------------------------------------------------------
    dummy_doc_content = b"# Alice Confidential Doc\nRevenue was 50 million in 2025."
    files = {"file": ("alice_confidential.md", dummy_doc_content, "text/markdown")}
    r_up_a = client.post(f"{BASE_URL}/documents/upload", files=files, headers=headers_a)
    log_test("User A uploads document", r_up_a.status_code == 200)
    doc_a_id = r_up_a.json().get("document_id")

    r_doc_list_b = client.get(f"{BASE_URL}/documents", headers=headers_b)
    b_doc_names = [d["name"] for d in r_doc_list_b.json()["files"]]
    log_test("User B does NOT see User A's uploaded file", "alice_confidential.md" not in b_doc_names)

    if doc_a_id:
        r_idor_doc_del = client.delete(f"{BASE_URL}/documents/{doc_a_id}", headers=headers_b)
        log_test("IDOR blocked: User B cannot delete User A's document (404)", r_idor_doc_del.status_code == 404)

    # -------------------------------------------------------------
    # 6. Chat Tenant & Thread Injection Defense
    # -------------------------------------------------------------
    # User B attempts to chat into User A's conversation thread
    r_inject = client.post(f"{BASE_URL}/chat", json={
        "message": "Attempting cross-tenant thread injection",
        "conversation_id": conv_a_id
    }, headers=headers_b)
    log_test("IDOR blocked: User B cannot inject turns into User A's conversation (404)", r_inject.status_code == 404)

    # User A chats in User A's conversation thread
    r_chat_a = client.post(f"{BASE_URL}/chat", json={
        "message": "Summarize what this document is about in one sentence.",
        "conversation_id": conv_a_id
    }, headers=headers_a)
    log_test("User A chats in own thread successfully", r_chat_a.status_code == 200)

    # Verify conversation history updated for User A only
    r_hist_a = client.get(f"{BASE_URL}/conversations/{conv_a_id}", headers=headers_a)
    msg_senders = [m["sender"] for m in r_hist_a.json()["messages"]]
    log_test("User A conversation history recorded user and assistant turns", "user" in msg_senders and "assistant" in msg_senders)

    # User B still receives 404 when querying User A's thread history
    r_hist_b_try = client.get(f"{BASE_URL}/conversations/{conv_a_id}", headers=headers_b)
    log_test("User B still cannot read User A's enriched history (404)", r_hist_b_try.status_code == 404)

    print("=" * 70)
    print("🏆 ALL MULTI-TENANT ISOLATION & SECURITY TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
