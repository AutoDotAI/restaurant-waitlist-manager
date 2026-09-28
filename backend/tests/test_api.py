import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import reset_store, store


@pytest.fixture(autouse=True)
def fresh_store():
    reset_store()


def login(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "claire@obermamma.fr", "password": "demo-password"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "MANAGER"
    return response.json()["accessToken"]


def authenticated(client: TestClient) -> TestClient:
    token = login(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_auth_session_login_logout_hashed_passwords_and_bearer_protection():
    with TestClient(app) as client:
        assert client.get("/auth/session").json() is None
        assert client.get("/restaurant").status_code == 401
        assert store.staff_by_email("claire@obermamma.fr").password_hash != "demo-password"

        bad = client.post(
            "/auth/login", json={"email": "claire@obermamma.fr", "password": "wrong"}
        )
        assert bad.status_code == 401
        assert bad.json() == {"message": "Invalid email or password."}

        token = login(client)
        assert token
        assert client.get("/auth/session", headers={"Authorization": f"Bearer {token}"}).json()["email"] == "claire@obermamma.fr"
        assert client.get("/restaurant", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        assert client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"}).json() == {"success": True}
        assert client.get("/auth/session", headers={"Authorization": f"Bearer {token}"}).json() is None
        assert client.get("/restaurant", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_restaurant_staff_and_analytics_endpoints():
    with TestClient(app) as client:
        authenticated(client)
        restaurant = client.get("/restaurant")
        assert restaurant.status_code == 200
        assert restaurant.json()["slug"] == "big-mamma"

        changed = client.patch("/restaurant", json={"remoteJoinEnabled": False})
        assert changed.status_code == 200
        assert changed.json()["remoteJoinEnabled"] is False

        staff = client.get("/restaurant/staff")
        assert staff.status_code == 200
        assert len(staff.json()) == 2
        added = client.post(
            "/restaurant/staff",
            json={"name": "Alex Host", "email": "alex@example.com", "role": "HOST", "password": "host-password"},
        )
        assert added.status_code == 201
        assert "password" not in added.json()
        assert "passwordHash" not in added.json()
        account = store.staff_by_email("alex@example.com")
        assert account is not None
        assert account.password_hash not in (None, "host-password")
        with TestClient(app) as new_staff_client:
            staff_login = new_staff_client.post(
                "/auth/login",
                json={"email": "alex@example.com", "password": "host-password"},
            )
            assert staff_login.status_code == 200
            assert staff_login.json()["user"]["email"] == "alex@example.com"
        assert client.delete(f"/restaurant/staff/{added.json()['id']}").json() == {"success": True}

        analytics = client.get("/analytics", params={"range": "today"})
        assert analytics.status_code == 200
        assert set(analytics.json()) == {
            "guestsServed", "averageEstimatedWait", "averageActualWait", "cancellations",
            "noShows", "walkIns", "remoteJoins", "averagePartySize",
        }
        assert client.get("/analytics", params={"range": "year"}).status_code == 422


def test_waitlist_lifecycle_queue_history_sms_and_reorder():
    with TestClient(app) as client:
        authenticated(client)
        created = client.post(
            "/waitlist",
            json={
                "customerName": "Amira", "phoneNumber": "+33 6 01 02 03 04",
                "partySize": 3, "source": "WALK_IN", "staffNotes": "Window seat",
            },
        )
        assert created.status_code == 201
        entry = created.json()
        assert entry["status"] == "WAITING"
        assert entry["staffNotes"] == "Window seat"
        entry_id = entry["id"]

        duplicate = client.post(
            "/waitlist",
            json={
                "customerName": "Amira", "phoneNumber": "+33601020304",
                "partySize": 3, "source": "WALK_IN",
            },
        )
        assert duplicate.status_code == 409
        assert len(client.get("/waitlist").json()) == 6

        updated = client.patch(
            f"/waitlist/{entry_id}", json={"manualWaitOverride": 42, "staffNotes": "Ready soon"}
        )
        assert updated.status_code == 200
        assert updated.json()["manualWaitOverride"] == 42

        notified = client.put(f"/waitlist/{entry_id}/status", json={"status": "NOTIFIED"})
        assert notified.status_code == 200
        assert notified.json()["notifiedAt"]
        assert client.get("/waitlist/sms").json()[0]["messageType"] == "TABLE_NEARLY_READY"

        queue = client.get("/waitlist").json()
        ids = [row["id"] for row in reversed(queue)]
        reordered = client.put("/waitlist/reorder", json={"orderedIds": ids})
        assert reordered.status_code == 200
        assert [row["id"] for row in reordered.json()] == ids

        seated = client.put(f"/waitlist/{entry_id}/status", json={"status": "SEATED"})
        assert seated.status_code == 200
        assert entry_id not in [row["id"] for row in client.get("/waitlist").json()]
        assert entry_id in [row["id"] for row in client.get("/waitlist/history").json()]


def test_public_restaurant_join_status_confirm_and_cancel():
    with TestClient(app) as client:
        public_info = client.get("/public/restaurants/big-mamma")
        assert public_info.status_code == 200
        assert public_info.json()["remoteJoinEnabled"] is True
        assert client.get("/public/restaurants/missing").status_code == 404

        joined = client.post(
            "/public/restaurants/big-mamma/waitlist",
            json={"customerName": "Noah", "phoneNumber": "+33611112222", "partySize": 2},
        )
        assert joined.status_code == 201
        token = joined.json()["token"]
        assert client.get(f"/public/waitlist/{token}").json()["customerName"] == "Noah"
        assert client.post(f"/public/waitlist/{token}/confirm").json()["status"] == "CONFIRMED"

        cancel_join = client.post(
            "/public/restaurants/big-mamma/waitlist",
            json={"customerName": "Mina", "phoneNumber": "+33611113333", "partySize": 2},
        )
        cancel_token = cancel_join.json()["token"]
        assert client.post(f"/public/waitlist/{cancel_token}/cancel").json()["status"] == "CANCELLED"
        assert client.get("/public/waitlist/not-a-token").status_code == 404


def test_public_join_rejects_closed_remote_join_and_invalid_input():
    with TestClient(app) as client:
        auth = login(client)
        client.patch("/restaurant", headers={"Authorization": f"Bearer {auth}"}, json={"remoteJoinEnabled": False})
        closed = client.post(
            "/public/restaurants/big-mamma/waitlist",
            json={"customerName": "Noah", "phoneNumber": "+33611112222", "partySize": 2},
        )
        assert closed.status_code == 409

        bad = client.post(
            "/public/restaurants/big-mamma/waitlist",
            json={"customerName": "Noah", "phoneNumber": "+33611112222", "partySize": 0},
        )
        assert bad.status_code == 422
        assert "message" in bad.json()
