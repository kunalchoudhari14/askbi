"""Tests for core.auth.check_login, using fake users instead of real secrets."""

import pytest

from core import auth

END_USER = "end_user"
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_pass"
FAKE_USERS = {TEST_USERNAME: {"password": TEST_PASSWORD, "role": END_USER}}


@pytest.fixture(autouse=True)
def fake_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace st.secrets with fake users for every test in this file."""
    # check_login reads st.secrets when it's called, so swapping it here means
    # .streamlit/secrets.toml is never opened. That file doesn't exist in CI.
    # monkeypatch puts the real st.secrets back after each test.
    monkeypatch.setattr(auth.st, "secrets", {"users": FAKE_USERS})


def test_correct_password_returns_role() -> None:
    """A known user with the right password gets their role back."""
    assert auth.check_login(TEST_USERNAME, TEST_PASSWORD) == END_USER


def test_wrong_password_returns_none() -> None:
    """A known user with the wrong password is rejected."""
    assert auth.check_login(TEST_USERNAME, "wrong_password") is None


def test_unknown_user_returns_none() -> None:
    """A username that isn't in the users list is rejected."""
    assert auth.check_login("nobody", TEST_PASSWORD) is None
