# Pythonic Response Validation Examples

This document provides comprehensive examples of the Pythonic response validation patterns available in the REST API Testing framework.

## Basic Status Code Validation

```python
def test_status_code(self):
    """Validate response status code."""
    response = self.authenticated_request.get("/users/123")
    
    # Single status code
    response.should_have.status_code(200)
    
    # Multiple acceptable status codes
    response.should_have.status_code_in([200, 201])
```

## Content Type Validation

```python
def test_content_type(self):
    """Validate response content type."""
    response = self.authenticated_request.get("/users/123")
    
    response.should_have.content_type("application/json")
```

## JSON Path Validation

### Existence Checks

```python
def test_json_path_exists(self):
    """Check if a JSON path exists."""
    response = self.authenticated_request.get("/users/123")
    
    # Path should exist
    response.should_have.json_path("id", exists=True)
    response.should_have.json_path("name", exists=True)
    
    # Path should not exist
    response.should_have.json_path("deleted", exists=False)
```

### Equality Checks

```python
def test_json_path_equals(self):
    """Validate JSON path value equals expected."""
    response = self.authenticated_request.get("/users/123")
    
    response.should_have.json_path("id", equals=123)
    response.should_have.json_path("name", equals="John Doe")
    response.should_have.json_path("active", equals=True)
```

### Regex Matching

```python
def test_json_path_matches(self):
    """Validate JSON path value matches regex pattern."""
    response = self.authenticated_request.get("/users/123")
    
    # Email validation
    response.should_have.json_path(
        "email", 
        matches=r"^[^@]+@[^@]+\.[^@]+$"
    )
    
    # Phone number validation
    response.should_have.json_path(
        "phone", 
        matches=r"^\d{3}-\d{3}-\d{4}$"
    )
```

### Custom Validation Functions

```python
def test_json_path_custom_validation(self):
    """Validate JSON path with custom function."""
    response = self.authenticated_request.get("/users/123")
    
    # Age validation
    response.should_have.json_path(
        "age", 
        validate=lambda x: 18 <= x <= 100
    )
    
    # List length validation
    response.should_have.json_path(
        "tags", 
        validate=lambda tags: len(tags) > 0 and len(tags) <= 10
    )
    
    # Complex validation
    def is_valid_user(user_data):
        return (
            user_data.get("id") is not None
            and user_data.get("email") is not None
            and "@" in user_data.get("email", "")
        )
    
    response.should_have.json_path("", validate=is_valid_user)
```

## Extracting Values

```python
def test_extract_values(self):
    """Extract values from JSON response."""
    response = self.authenticated_request.get("/users/123")
    
    # Extract single value
    user_id = response.json_path("id")
    user_name = response.json_path("name")
    
    # Extract with default value
    phone = response.json_path("phone", default="N/A")
    
    # Use extracted values in assertions
    assert user_id == 123
    assert user_name is not None
    assert len(user_name) > 0
```

## Using Response Extractor

```python
def test_response_extractor(self):
    """Use response extractor for more complex extraction."""
    response = self.authenticated_request.get("/users/123")
    
    # Extract as string
    response_text = response.extract.as_string()
    assert "John" in response_text
    
    # Extract as JSON dictionary
    json_data = response.extract.as_json()
    assert isinstance(json_data, dict)
    assert json_data["id"] == 123
    
    # Extract specific path
    user_id = response.extract.path("id")
    user_email = response.extract.path("email")
    
    # Extract nested path
    address = response.extract.path("address/street")
```

## Complex Validation Examples

### Validating Nested Objects

```python
def test_nested_object_validation(self):
    """Validate nested JSON structures."""
    response = self.authenticated_request.get("/users/123")
    
    # Validate nested fields
    response.should_have.json_path("address/street", exists=True)
    response.should_have.json_path("address/city", equals="New York")
    response.should_have.json_path("address/zipCode", matches=r"^\d{5}$")
```

### Validating Arrays

```python
def test_array_validation(self):
    """Validate array elements in response."""
    response = self.authenticated_request.get("/users")
    
    # Validate array exists and has items
    response.should_have.json_path("users", exists=True)
    response.should_have.json_path(
        "users", 
        validate=lambda users: len(users) > 0
    )
    
    # Validate specific array element
    response.should_have.json_path("users/0/id", exists=True)
    response.should_have.json_path("users/0/name", exists=True)
```

### Combining Multiple Validations

```python
def test_multiple_validations(self):
    """Combine multiple validation checks."""
    response = self.authenticated_request.post("/users", body=json_body)
    
    # Chain multiple validations
    response.should_have.status_code(201)
    response.should_have.content_type("application/json")
    response.should_have.json_path("id", exists=True)
    response.should_have.json_path("createdAt", exists=True)
    response.should_have.json_path("email", matches=r"^[^@]+@[^@]+\.[^@]+$")
```

## Error Response Validation

```python
def test_error_response(self):
    """Validate error responses."""
    response = self.unauthenticated_request.get("/protected-resource")
    
    # Validate error status
    response.should_have.status_code(401)
    
    # Validate error message
    response.should_have.json_path("error", equals="Unauthorized")
    response.should_have.json_path("message", exists=True)
```

## Best Practices

1. **Use descriptive test names** that explain what is being validated
2. **Chain validations** for better readability
3. **Extract values** when you need to use them in multiple assertions
4. **Use custom validators** for complex business logic validation
5. **Validate error responses** to ensure proper error handling
6. **Use regex patterns** for format validation (emails, phone numbers, etc.)

## Advanced Patterns

### Validating Response Time

```python
import time

def test_response_time(self):
    """Validate response time is acceptable."""
    start_time = time.time()
    response = self.authenticated_request.get("/users")
    elapsed_time = time.time() - start_time
    
    response.should_have.status_code(200)
    assert elapsed_time < 1.0  # Response should be under 1 second
```

### Validating Response Headers

```python
def test_response_headers(self):
    """Validate response headers."""
    response = self.authenticated_request.get("/users/123")
    
    response.should_have.status_code(200)
    response.should_have.header("Content-Type", "application/json")
    response.should_have.header("Cache-Control", "no-cache")
```

### Conditional Validation

```python
def test_conditional_validation(self):
    """Perform conditional validation based on response."""
    response = self.authenticated_request.get("/users/123")
    
    if response.json_path("status") == "active":
        response.should_have.json_path("lastLogin", exists=True)
    else:
        response.should_have.json_path("lastLogin", exists=False)
```

