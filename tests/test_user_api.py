from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings


def auth_headers(user_id: int = 501) -> dict[str, str]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "customer",
            "iss": settings.jwt_issuer,
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def profile_payload():
    return {
        "full_name": "Sai User",
        "phone_number": "+91 9876543210",
        "date_of_birth": "2000-01-10",
        "gender": "Prefer not to say",
        "profile_image": None,
    }


def address_payload(name="Sai User", is_default=False, address_line="12 Main Road"):
    return {
        "address_type": "Home",
        "full_name": name,
        "phone_number": "+91 9876543210",
        "address_line_1": address_line,
        "address_line_2": "Near City Park",
        "city": "Kurnool",
        "state": "Andhra Pradesh",
        "country": "India",
        "postal_code": "518001",
        "is_default": is_default,
    }


def create_profile(client, user_id=501):
    return client.post("/api/users/profile", json=profile_payload(), headers=auth_headers(user_id))


def test_missing_token_is_rejected(client):
    response = client.get("/api/users/profile")
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/users/profile", headers={"Authorization": "Bearer invalid.token"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "501",
            "role": "customer",
            "iss": settings.jwt_issuer,
            "iat": now - timedelta(minutes=5),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/users/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_create_and_get_profile(client):
    created = create_profile(client)
    assert created.status_code == 201
    assert created.json()["auth_user_id"] == 501
    assert "password" not in created.json()

    fetched = client.get("/api/users/profile", headers=auth_headers(501))
    assert fetched.status_code == 200
    assert fetched.json()["full_name"] == "Sai User"



def test_client_cannot_supply_auth_user_id_or_local_user_id(client):
    profile_payload_with_owner = profile_payload()
    profile_payload_with_owner["auth_user_id"] = 777
    denied_profile = client.post(
        "/api/users/profile", json=profile_payload_with_owner, headers=auth_headers(501)
    )
    assert denied_profile.status_code == 422

    assert create_profile(client).status_code == 201
    address_payload_with_owner = address_payload()
    address_payload_with_owner["user_id"] = 999
    denied_address = client.post(
        "/api/users/addresses", json=address_payload_with_owner, headers=auth_headers(501)
    )
    assert denied_address.status_code == 422

def test_duplicate_profile_is_rejected(client):
    assert create_profile(client).status_code == 201
    duplicate = create_profile(client)
    assert duplicate.status_code == 409


def test_profile_put_and_patch(client):
    assert create_profile(client).status_code == 201
    replaced = client.put(
        "/api/users/profile",
        json={
            "full_name": "Sai Updated",
            "phone_number": "+91 9123456780",
            "date_of_birth": "1999-05-20",
            "gender": "Other",
            "profile_image": "https://example.com/avatar.png",
        },
        headers=auth_headers(501),
    )
    assert replaced.status_code == 200
    assert replaced.json()["full_name"] == "Sai Updated"

    patched = client.patch(
        "/api/users/profile", json={"full_name": "Sai Patched"}, headers=auth_headers(501)
    )
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "Sai Patched"


def test_profile_is_scoped_to_authenticated_subject(client):
    assert create_profile(client, user_id=501).status_code == 201
    other_user = client.get("/api/users/profile", headers=auth_headers(777))
    assert other_user.status_code == 404


def test_default_address_is_unique_per_profile(client):
    assert create_profile(client).status_code == 201
    first = client.post("/api/users/addresses", json=address_payload(is_default=True), headers=auth_headers(501))
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        "/api/users/addresses",
        json=address_payload(name="Sai Office", is_default=True, address_line="88 Office Road"),
        headers=auth_headers(501),
    )
    assert second.status_code == 201
    assert second.json()["is_default"] is True

    addresses = client.get("/api/users/addresses", headers=auth_headers(501)).json()
    assert len(addresses) == 2
    assert sum(1 for item in addresses if item["is_default"]) == 1
    old_first = client.get(f"/api/users/addresses/{first_id}", headers=auth_headers(501))
    assert old_first.json()["is_default"] is False


def test_get_update_and_patch_address(client):
    assert create_profile(client).status_code == 201
    created = client.post("/api/users/addresses", json=address_payload(is_default=True), headers=auth_headers(501))
    address_id = created.json()["id"]

    fetched = client.get(f"/api/users/addresses/{address_id}", headers=auth_headers(501))
    assert fetched.status_code == 200

    updated = client.put(
        f"/api/users/addresses/{address_id}",
        json=address_payload(name="Sai Updated", is_default=True, address_line="99 New Road"),
        headers=auth_headers(501),
    )
    assert updated.status_code == 200
    assert updated.json()["address_line_1"] == "99 New Road"

    patched = client.patch(
        f"/api/users/addresses/{address_id}", json={"city": "Nandyal"}, headers=auth_headers(501)
    )
    assert patched.status_code == 200
    assert patched.json()["city"] == "Nandyal"


def test_foreign_user_cannot_access_address(client):
    assert create_profile(client, user_id=501).status_code == 201
    address = client.post("/api/users/addresses", json=address_payload(), headers=auth_headers(501))
    address_id = address.json()["id"]
    denied = client.get(f"/api/users/addresses/{address_id}", headers=auth_headers(777))
    assert denied.status_code == 404  # no profile exists for the second identity


def test_address_id_is_forbidden_for_another_profile(client):
    assert create_profile(client, user_id=501).status_code == 201
    first = client.post("/api/users/addresses", json=address_payload(), headers=auth_headers(501))
    address_id = first.json()["id"]
    assert create_profile(client, user_id=777).status_code == 201
    denied = client.get(f"/api/users/addresses/{address_id}", headers=auth_headers(777))
    assert denied.status_code == 403


def test_set_default_and_delete_address(client):
    assert create_profile(client).status_code == 201
    first = client.post("/api/users/addresses", json=address_payload(is_default=True), headers=auth_headers(501))
    second = client.post(
        "/api/users/addresses", json=address_payload(name="Office", is_default=False), headers=auth_headers(501)
    )
    first_id, second_id = first.json()["id"], second.json()["id"]

    changed = client.patch(f"/api/users/addresses/{second_id}/default", headers=auth_headers(501))
    assert changed.status_code == 200
    assert changed.json()["is_default"] is True
    listed = client.get("/api/users/addresses", headers=auth_headers(501)).json()
    assert sum(1 for item in listed if item["is_default"]) == 1

    deleted = client.delete(f"/api/users/addresses/{first_id}", headers=auth_headers(501))
    assert deleted.status_code == 204
    assert client.get(f"/api/users/addresses/{first_id}", headers=auth_headers(501)).status_code == 404


def test_deactivate_profile_blocks_profile_and_address_operations(client):
    assert create_profile(client).status_code == 201
    response = client.post("/api/users/profile/deactivate", headers=auth_headers(501))
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    blocked = client.get("/api/users/profile", headers=auth_headers(501))
    assert blocked.status_code == 403



def test_profile_rejects_invalid_phone_number(client):
    payload = profile_payload()
    payload["phone_number"] = "not-a-phone"
    response = client.post("/api/users/profile", json=payload, headers=auth_headers(501))
    assert response.status_code == 422


def test_address_rejects_invalid_postal_code(client):
    assert create_profile(client).status_code == 201
    payload = address_payload()
    payload["postal_code"] = "!@"
    response = client.post("/api/users/addresses", json=payload, headers=auth_headers(501))
    assert response.status_code == 422


def test_delete_profile_cascades_saved_addresses(client):
    assert create_profile(client).status_code == 201
    address = client.post("/api/users/addresses", json=address_payload(), headers=auth_headers(501))
    address_id = address.json()["id"]

    deleted = client.delete("/api/users/profile", headers=auth_headers(501))
    assert deleted.status_code == 204
    assert client.get("/api/users/profile", headers=auth_headers(501)).status_code == 404
    assert client.get(f"/api/users/addresses/{address_id}", headers=auth_headers(501)).status_code == 404
