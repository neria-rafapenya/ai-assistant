import pytest

from app.auth import AuthenticatedUser, get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def authenticated_test_user():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        sub="test-user-sub",
        claims={"sub": "test-user-sub", "token_use": "access"},
    )
    yield
    app.dependency_overrides.clear()
