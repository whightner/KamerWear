"""Saved delivery addresses: CRUD, default handling and ownership."""

import pytest

from tests.commerce import ADDRESS, add_address, signup
from tests.test_auth import error_code


@pytest.fixture
def alex(client):
    return signup(client, "alex@example.com")


@pytest.fixture
def bella(client):
    return signup(client, "bella@example.com")


def test_create_normalises_and_first_address_is_default(client, alex):
    body = add_address(client, alex, region="littoral")
    assert body["region"] == "Littoral"
    assert body["phone"] == "+237699112233"
    assert body["country_code"] == "CM"
    assert body["street_or_landmark"] == "Near Tradex, blue gate"
    assert body["latitude"] is None
    assert body["is_default"] is True


def test_landmark_address_without_coordinates_or_street_number(client, alex):
    body = add_address(
        client,
        alex,
        city="Yaoundé",
        region="Centre",
        quarter="Bastos",
        street_or_landmark="Behind the Total station, 2nd yellow house",
    )
    assert body["city"] == "Yaoundé"


def test_optional_coordinates(client, alex):
    body = add_address(client, alex, latitude="4.0511", longitude="9.7679")
    assert body["latitude"] == "4.051100" and body["longitude"] == "9.767900"


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"region": "Lagos"}, "region"),
        ({"phone": ""}, "phone"),
        ({"quarter": "  "}, "quarter"),
        ({"user_id": 99}, "user_id"),
        ({"latitude": 120}, "latitude"),
    ],
)
def test_invalid_address_is_rejected(client, alex, changes, field):
    response = client.post("/api/v1/addresses", json={**ADDRESS, **changes}, headers=alex)
    assert response.status_code == 422
    assert field in response.json()["detail"]["fields"]


def test_list_only_own_addresses_default_first(client, alex, bella):
    add_address(client, alex, label="Home")
    office = add_address(client, alex, label="Office", is_default=True)
    add_address(client, bella, label="Bella home")
    labels = [a["label"] for a in client.get("/api/v1/addresses", headers=alex).json()]
    assert labels == ["Office", "Home"]
    assert office["is_default"]


def test_setting_default_clears_previous(client, alex):
    home = add_address(client, alex, label="Home")
    office = add_address(client, alex, label="Office")
    assert office["is_default"] is False
    response = client.patch(
        f"/api/v1/addresses/{office['id']}", json={"is_default": True}, headers=alex
    )
    assert response.json()["is_default"] is True
    addresses = {a["label"]: a for a in client.get("/api/v1/addresses", headers=alex).json()}
    assert addresses["Home"]["is_default"] is False
    assert sum(a["is_default"] for a in addresses.values()) == 1
    assert home["id"] != office["id"]


def test_update_own_address(client, alex):
    address = add_address(client, alex)
    response = client.patch(
        f"/api/v1/addresses/{address['id']}",
        json={"quarter": "Akwa", "street_or_landmark": "Opposite the cathedral"},
        headers=alex,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["quarter"] == "Akwa" and body["city"] == "Douala"


def test_cannot_read_update_or_delete_another_users_address(client, alex, bella):
    address = add_address(client, alex)
    url = f"/api/v1/addresses/{address['id']}"
    patched = client.patch(url, json={"label": "Hacked"}, headers=bella)
    assert patched.status_code == 404 and error_code(patched) == "address_not_found"
    deleted = client.delete(url, headers=bella)
    assert deleted.status_code == 404
    assert client.get("/api/v1/addresses", headers=bella).json() == []
    assert client.get("/api/v1/addresses", headers=alex).json()[0]["label"] == "Home"


def test_delete_default_promotes_newest(client, alex):
    home = add_address(client, alex, label="Home")
    add_address(client, alex, label="Office")
    add_address(client, alex, label="Shop")
    assert client.delete(f"/api/v1/addresses/{home['id']}", headers=alex).status_code == 204
    remaining = client.get("/api/v1/addresses", headers=alex).json()
    assert [a["label"] for a in remaining] == ["Shop", "Office"]
    assert remaining[0]["is_default"] is True


def test_addresses_require_authentication(client):
    assert client.get("/api/v1/addresses").status_code == 401
    assert client.post("/api/v1/addresses", json=ADDRESS).status_code == 401
