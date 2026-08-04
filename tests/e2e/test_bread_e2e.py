# tests/e2e/test_bread_e2e.py
"""Browser-level tests for the /dashboard BREAD interface.

Each test drives the real UI against the live uvicorn server the session
fixture starts, so a passing assertion covers the whole path: input,
client-side validation, the fetch call, the bearer token, FastAPI,
Postgres, and the DOM re-render.

Every test registers and logs in a fresh uuid-suffixed user. That is not
just collision avoidance — it also means the browse table starts empty,
so a row count is an exact assertion rather than a delta against
whatever earlier tests left behind.
"""

from uuid import uuid4

import pytest
from playwright.sync_api import expect

BASE = "http://localhost:8000"
PASSWORD = "Correct-Horse-9"


def login_fresh_user(page) -> None:
    """Register a new account, log in, and land on the dashboard."""
    suffix = uuid4().hex[:10]
    username = f"bread_{suffix}"

    page.goto(f"{BASE}/register")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.net")
    page.fill("#password", PASSWORD)
    page.fill("#confirm", PASSWORD)
    page.click("#submit")
    expect(page.locator("#success")).to_be_visible()

    page.goto(f"{BASE}/login")
    page.fill("#identifier", username)
    page.fill("#password", PASSWORD)
    page.click("#submit")
    # The dashboard link only appears once the token is stored, so
    # waiting on it is also waiting on a successful login.
    expect(page.locator("#dashboard-nav")).to_be_visible()
    page.click("#dashboard-link")
    expect(page.locator("#add-submit")).to_be_visible()


def add_calculation(page, a: str, operation: str, b: str) -> None:
    page.fill("#add-a", a)
    page.select_option("#add-type", operation)
    page.fill("#add-b", b)
    page.click("#add-submit")


# --- Add ---------------------------------------------------------------


@pytest.mark.e2e
def test_add_creates_row_with_computed_result(page, fastapi_server):
    """Positive: a valid submission returns 201 and the new row appears
    in the browse table with the result the server computed."""
    login_fresh_user(page)
    add_calculation(page, "6", "multiply", "7")

    expect(page.locator("#success")).to_have_text("Saved. Result: 42")
    expect(page.locator("tr.calc-row")).to_have_count(1)
    expect(page.locator(".cell-expr")).to_have_text("6 x 7")
    expect(page.locator(".cell-result")).to_have_text("42")


@pytest.mark.e2e
def test_add_rejects_non_numeric_operand_client_side(page, fastapi_server):
    """Negative: a blank operand fails the client-side numeric check, so
    no request is made and the table stays empty."""
    login_fresh_user(page)
    add_calculation(page, "", "add", "5")

    expect(page.locator("#error")).to_have_text("Both operands are required.")
    expect(page.locator("#success")).to_be_hidden()
    expect(page.locator("#empty")).to_be_visible()


@pytest.mark.e2e
def test_add_rejects_divide_by_zero_client_side(page, fastapi_server):
    """Negative: the divide-by-zero rule mirrors CalculationCreate, so
    the browser refuses the payload the server would have refused."""
    login_fresh_user(page)
    add_calculation(page, "9", "divide", "0")

    expect(page.locator("#error")).to_have_text("Cannot divide by zero.")
    expect(page.locator("tr.calc-row")).to_have_count(0)


# --- Browse ------------------------------------------------------------


@pytest.mark.e2e
def test_browse_lists_every_saved_calculation(page, fastapi_server):
    """Positive: three adds produce three rows, oldest first, each with
    its own computed result."""
    login_fresh_user(page)
    add_calculation(page, "1", "add", "2")
    expect(page.locator("tr.calc-row")).to_have_count(1)
    add_calculation(page, "10", "sub", "4")
    expect(page.locator("tr.calc-row")).to_have_count(2)
    add_calculation(page, "20", "divide", "5")

    expect(page.locator("tr.calc-row")).to_have_count(3)
    expect(page.locator(".cell-result")).to_have_text(["3", "6", "4"])


@pytest.mark.e2e
def test_browse_shows_only_the_logged_in_users_rows(page, fastapi_server):
    """Negative on the isolation axis: a second account sees an empty
    table even though the first user's row is still in the database."""
    login_fresh_user(page)
    add_calculation(page, "3", "add", "4")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    login_fresh_user(page)  # different account, same browser
    expect(page.locator("#empty")).to_be_visible()
    expect(page.locator("tr.calc-row")).to_have_count(0)


# --- Read --------------------------------------------------------------


@pytest.mark.e2e
def test_read_opens_detail_panel_for_one_row(page, fastapi_server):
    """Positive: View refetches GET /calculations/{id} and fills the
    detail panel with that single row."""
    login_fresh_user(page)
    add_calculation(page, "100", "divide", "25")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".view-btn")
    expect(page.locator("#detail")).to_be_visible()
    expect(page.locator("#detail-expr")).to_have_text("Expression: 100 / 25")
    expect(page.locator("#detail-result")).to_have_text("Result: 4")

    page.click("#detail-close")
    expect(page.locator("#detail")).to_be_hidden()


# --- Edit --------------------------------------------------------------


@pytest.mark.e2e
def test_edit_updates_one_field_and_persists(page, fastapi_server):
    """Positive: changing only the second operand sends a PATCH with a
    single field, and the change survives a full page reload."""
    login_fresh_user(page)
    add_calculation(page, "6", "multiply", "7")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".edit-btn")
    expect(page.locator("#edit-panel")).to_be_visible()
    page.fill("#edit-b", "8")
    page.click("#edit-save")

    expect(page.locator("#success")).to_have_text("Updated. Result: 48")
    expect(page.locator("#edit-panel")).to_be_hidden()
    expect(page.locator(".cell-expr")).to_have_text("6 x 8")

    # Reload proves the database changed, not just the rendered table.
    page.reload()
    expect(page.locator(".cell-result")).to_have_text("48")


@pytest.mark.e2e
def test_edit_with_no_changes_is_refused_client_side(page, fastapi_server):
    """Negative: saving an untouched form would be an empty PATCH body,
    which the server 400s — the browser stops it first."""
    login_fresh_user(page)
    add_calculation(page, "2", "add", "3")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".edit-btn")
    expect(page.locator("#edit-panel")).to_be_visible()
    page.click("#edit-save")

    expect(page.locator("#error")).to_have_text("No changes to save.")
    expect(page.locator("#edit-panel")).to_be_visible()


@pytest.mark.e2e
def test_edit_to_divide_by_zero_is_refused(page, fastapi_server):
    """Negative: switching an add whose b is 0 over to divide breaks the
    merged row, and the client-side rule catches it before the PATCH."""
    login_fresh_user(page)
    add_calculation(page, "5", "add", "0")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".edit-btn")
    expect(page.locator("#edit-panel")).to_be_visible()
    page.select_option("#edit-type", "divide")
    page.click("#edit-save")

    expect(page.locator("#error")).to_have_text("Cannot divide by zero.")
    expect(page.locator(".cell-expr")).to_have_text("5 + 0")


@pytest.mark.e2e
def test_edit_cancel_leaves_the_row_alone(page, fastapi_server):
    """Negative: Cancel discards the edited fields without a request."""
    login_fresh_user(page)
    add_calculation(page, "9", "sub", "4")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".edit-btn")
    page.fill("#edit-a", "1000")
    page.click("#edit-cancel")

    expect(page.locator("#edit-panel")).to_be_hidden()
    expect(page.locator(".cell-expr")).to_have_text("9 - 4")


# --- Delete ------------------------------------------------------------


@pytest.mark.e2e
def test_delete_requires_confirmation_then_removes_the_row(page, fastapi_server):
    """Positive: the first click arms the button, the second issues the
    DELETE, and the row is gone after a reload."""
    login_fresh_user(page)
    add_calculation(page, "2", "add", "2")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".delete-btn")
    expect(page.locator(".delete-btn")).to_have_text("Confirm delete")
    expect(page.locator("tr.calc-row")).to_have_count(1)

    page.click(".delete-btn")
    expect(page.locator("#success")).to_have_text("Calculation deleted.")
    expect(page.locator("#empty")).to_be_visible()

    page.reload()
    expect(page.locator("tr.calc-row")).to_have_count(0)


@pytest.mark.e2e
def test_delete_removes_only_the_targeted_row(page, fastapi_server):
    """Positive: deleting the middle of three rows leaves the other two
    intact and correctly rendered."""
    login_fresh_user(page)
    add_calculation(page, "1", "add", "1")
    expect(page.locator("tr.calc-row")).to_have_count(1)
    add_calculation(page, "2", "add", "2")
    expect(page.locator("tr.calc-row")).to_have_count(2)
    add_calculation(page, "3", "add", "3")
    expect(page.locator("tr.calc-row")).to_have_count(3)

    middle = page.locator("tr.calc-row").nth(1).locator(".delete-btn")
    middle.click()
    middle.click()

    expect(page.locator("tr.calc-row")).to_have_count(2)
    expect(page.locator(".cell-result")).to_have_text(["2", "6"])


# --- Authorization -----------------------------------------------------


@pytest.mark.e2e
def test_dashboard_without_a_token_redirects_to_login(page, fastapi_server):
    """Negative: an unauthenticated visitor never sees the BREAD UI."""
    page.goto(f"{BASE}/dashboard")
    page.wait_for_url("**/login")
    expect(page.locator("#identifier")).to_be_visible()


@pytest.mark.e2e
def test_stale_token_is_cleared_and_the_user_is_sent_back_to_login(
    page, fastapi_server
):
    """Negative: a forged token gets a 401 from /calculations; the page
    treats that like a logout instead of rendering a broken table."""
    page.goto(f"{BASE}/login")
    page.evaluate("() => localStorage.setItem('access_token', 'not.a.jwt')")
    page.goto(f"{BASE}/dashboard")

    page.wait_for_url("**/login")
    assert page.evaluate("() => localStorage.getItem('access_token')") is None


@pytest.mark.e2e
def test_logout_clears_the_token_and_returns_to_login(page, fastapi_server):
    """Positive: logging out discards the credential, so going straight
    back to /dashboard bounces to the login form."""
    login_fresh_user(page)
    page.click("#logout")

    page.wait_for_url("**/login")
    assert page.evaluate("() => localStorage.getItem('access_token')") is None

    page.goto(f"{BASE}/dashboard")
    page.wait_for_url("**/login")