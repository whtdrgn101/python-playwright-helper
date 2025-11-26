# Migration Guide: Java to Python

This document highlights the key differences between the Java and Python versions of the REST API Testing framework.

## Key Differences

### 1. Template Engine

**Java:** Apache Velocity (`.vm` files)
```java
{
  "name": "$name",
  "age": $age
#if($phone)
  ,"phone": "$phone"
#end
}
```

**Python:** Jinja2 (`.j2` files)
```python
{
  "name": "{{ name }}",
  "age": {{ age }}
{% if phone %}
  ,"phone": "{{ phone }}"
{% endif %}
}
```

### 2. Data Loading

**Java:** Supports both JSON and CSV files
```java
// JSON
String jsonBody = renderTemplate("template.vm", "data.json");

// CSV
Map<String, String> data = loadCsvAsMap("data.csv");
String jsonBody = renderTemplate("template.vm", data);
```

**Python:** CSV files only (as requested)
```python
# CSV only
data = self.load_csv_as_dict("data.csv")
json_body = self.render_template("template.j2", data)
```

### 3. Test Framework

**Java:** JUnit 5
```java
@Test
public void testEndpoint() {
    APIResponse response = authenticatedRequest()
        .get("/endpoint")
        .then()
        .statusCode(200)
        .extract()
        .response();
}
```

**Python:** pytest
```python
def test_endpoint(self):
    response = self.authenticated_request.get("/endpoint")
    response.should_have.status_code(200)
```

### 4. Response Validation

**Java:** REST-assured-like fluent API
```java
response.then()
    .statusCode(200)
    .body("id", notNull())
    .body("name", equalTo("John"));
```

**Python:** Pythonic fluent API
```python
response.should_have.status_code(200)
response.should_have.json_path("id", exists=True)
response.should_have.json_path("name", equals="John")
```

### 5. Configuration

**Java:** Properties file with environment variable support
```properties
api.base.url=https://api.example.com
ping.federate.client.id=${PING_CLIENT_ID}
```

**Python:** Properties file with environment variable support (same format)
```properties
api.base.url=https://api.example.com
ping.federate.client.id=${PING_CLIENT_ID}
```

### 6. Package Management

**Java:** Maven (`pom.xml`)
```xml
<dependency>
    <groupId>com.westfieldgrp.testing</groupId>
    <artifactId>rest-api-testing</artifactId>
    <version>3.0.0</version>
</dependency>
```

**Python:** UV (`pyproject.toml`)
```bash
uv pip install rest-api-testing
```

### 7. Pythonic Features

The Python version includes several Pythonic improvements:

- **Properties instead of getters**: `self.config` instead of `getConfig()`
- **Context managers**: Automatic resource cleanup
- **Type hints**: Better IDE support and type checking
- **Fluent validation**: `response.should_have.json_path(...)` instead of `.body(...)`
- **Dictionary access**: Direct dictionary access for CSV data
- **List comprehensions**: Easy iteration over CSV rows

## Code Comparison

### Java Example
```java
@Test
public void testCreateUser() {
    Map<String, String> userData = loadCsvAsMap("templates/user-data.csv");
    String jsonBody = renderTemplate("templates/user-create.json.vm", userData);
    
    APIResponse response = authenticatedRequest()
        .post("/users", jsonBody)
        .then()
        .statusCode(201)
        .body("id", notNull())
        .extract()
        .response();
}
```

### Python Equivalent
```python
def test_create_user(self):
    user_data = self.load_csv_as_dict("templates/user-data.csv")
    json_body = self.render_template("templates/user-create.json.j2", user_data)
    
    response = self.authenticated_request.post("/users", body=json_body)
    response.should_have.status_code(201)
    response.should_have.json_path("id", exists=True)
```

## Migration Checklist

- [ ] Update template files from `.vm` to `.j2` (Velocity to Jinja2 syntax)
- [ ] Remove JSON data files (use CSV only)
- [ ] Convert test classes from JUnit to pytest
- [ ] Update imports and package names
- [ ] Update configuration file paths if needed
- [ ] Test authentication flow
- [ ] Verify template rendering
- [ ] Update CI/CD pipelines for Python/UV

## Benefits of Python Version

1. **More Pythonic**: Follows Python idioms and best practices
2. **Better IDE Support**: Type hints provide better autocomplete
3. **Simpler Syntax**: Less boilerplate than Java
4. **CSV-Only**: Simpler data loading (as requested)
5. **Modern Tooling**: UV for fast package management
6. **Flexible Validation**: Custom validation functions with lambdas

