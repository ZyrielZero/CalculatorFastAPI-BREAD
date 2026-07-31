# tests/e2e/test_e2e.py

import pytest  # Import the pytest framework for writing and running tests
from playwright.sync_api import expect  # Auto-waiting assertions that retry until the condition holds

# The following decorators and functions define E2E tests for the FastAPI calculator application.

@pytest.mark.e2e
def test_hello_world(page, fastapi_server):
    """The homepage renders and the served template's header reads Hello World."""
    # Navigate the browser to the homepage URL of the FastAPI application.
    page.goto('http://localhost:8000')
    
    # Use an assertion to check that the text within the first <h1> tag is exactly "Hello World".
    # If the text does not match, the test will fail.
    assert page.inner_text('h1') == 'Hello World'

@pytest.mark.e2e
def test_calculator_add(page, fastapi_server):
    """Filling both inputs and clicking Add displays the computed sum."""
    # Navigate the browser to the homepage URL of the FastAPI application.
    page.goto('http://localhost:8000')
    
    # Fill in the first number input field (with id 'a') with the value '10'.
    page.fill('#a', '10')
    
    # Fill in the second number input field (with id 'b') with the value '5'.
    page.fill('#b', '5')
    
    # Click the button that has the exact text "Add". This triggers the addition operation.
    page.click('button:text("Add")')
    
    # The frontend updates #result only after its fetch() resolves, so a plain
    # inner_text() read races the network round trip and can see an empty div.
    # expect() retries the assertion until it passes or times out, eliminating the race.
    expect(page.locator('#result')).to_have_text('Calculation Result: 15')

@pytest.mark.e2e
def test_calculator_divide_by_zero(page, fastapi_server):
    """Dividing by zero surfaces the backend error message in the result div."""
    # Navigate the browser to the homepage URL of the FastAPI application.
    page.goto('http://localhost:8000')
    
    # Fill in the first number input field (with id 'a') with the value '10'.
    page.fill('#a', '10')
    
    # Fill in the second number input field (with id 'b') with the value '0', attempting to divide by zero.
    page.fill('#b', '0')
    
    # Click the button that has the exact text "Divide". This triggers the division operation.
    page.click('button:text("Divide")')
    
    # Same race as the add test: the error message appears only after the fetch
    # resolves, so use an auto-waiting assertion instead of an immediate read.
    expect(page.locator('#result')).to_have_text('Error: Cannot divide by zero!')

@pytest.mark.e2e
def test_calculator_subtract(page, fastapi_server):
    """Clicking Subtract routes through /subtract and renders a negative result."""
    page.goto('http://localhost:8000')
    page.fill('#a', '8')
    page.fill('#b', '20')
    page.click('button:text("Subtract")')
    # Auto-waiting assertion: the div is populated only after fetch() resolves.
    expect(page.locator('#result')).to_have_text('Calculation Result: -12')
