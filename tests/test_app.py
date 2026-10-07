from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(app_module, "activities", deepcopy(INITIAL_ACTIVITIES))
    return TestClient(app_module.app)


def test_root_redirects_to_static_homepage(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_data_without_caching(client: TestClient) -> None:
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == INITIAL_ACTIVITIES
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_student_to_activity(client: TestClient) -> None:
    email = "newstudent@mergington.edu"

    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert email in app_module.activities["Chess Club"]["participants"]


def test_signup_rejects_duplicate_student_without_changing_participants(
    client: TestClient,
) -> None:
    email = INITIAL_ACTIVITIES["Chess Club"]["participants"][0]
    participants_before = list(app_module.activities["Chess Club"]["participants"])

    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert app_module.activities["Chess Club"]["participants"] == participants_before


def test_signup_returns_not_found_for_unknown_activity(client: TestClient) -> None:
    response = client.post(
        "/activities/Unknown Club/signup",
        params={"email": "newstudent@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_remove_participant_removes_student(client: TestClient) -> None:
    email = INITIAL_ACTIVITIES["Chess Club"]["participants"][0]

    response = client.delete(
        "/activities/Chess Club/participants",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Chess Club"}
    assert email not in app_module.activities["Chess Club"]["participants"]


@pytest.mark.parametrize(
    ("activity_name", "email", "detail"),
    [
        ("Unknown Club", "student@mergington.edu", "Activity not found"),
        (
            "Chess Club",
            "not-signed-up@mergington.edu",
            "Student is not signed up for this activity",
        ),
    ],
)
def test_remove_participant_returns_not_found_for_missing_activity_or_student(
    client: TestClient,
    activity_name: str,
    email: str,
    detail: str,
) -> None:
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/activities/Chess Club/signup"),
        ("delete", "/activities/Chess Club/participants"),
    ],
)
def test_participant_routes_require_email(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    response = getattr(client, method)(path)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]
