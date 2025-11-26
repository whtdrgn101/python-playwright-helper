"""Example API test demonstrating the Pythonic testing framework."""

import pytest
from rest_api_testing import BaseApiTest


class TestExampleAPI(BaseApiTest):
    """Example API test class demonstrating the testing pattern."""

    @pytest.mark.smoke
    def test_get_endpoint(self):
        """Test GET endpoint with Pythonic validation."""
        response = self.authenticated_request.get("/my/endpoint")

        # Fluent validation API
        response.should_have.status_code(200)
        response.should_have.content_type("application/json")
        response.should_have.json_path("data.id", exists=True)
        response.should_have.json_path("data.name", equals="expected_value")

    @pytest.mark.integration
    def test_post_with_template(self):
        """Test POST endpoint with template rendering."""
        # Render template with context
        json_body = self.render_template(
            "templates/user-create.json.j2",
            {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com",
                "age": 30,
                "phoneNumber": "555-1234",
            },
        )

        # Make authenticated POST request
        response = self.authenticated_request.post("/users", body=json_body)

        response.should_have.status_code(201)
        response.should_have.json_path("id", exists=True)

    @pytest.mark.integration
    def test_post_with_csv_data(self):
        """Test POST endpoint with CSV data."""
        # Load first row from CSV
        user_data = self.load_csv_as_dict("templates/user-data.csv")

        # Render template with CSV data
        json_body = self.render_template("templates/user-create.json.j2", user_data)

        # Make authenticated POST request
        response = self.authenticated_request.post("/users", body=json_body)

        response.should_have.status_code(201)
        response.should_have.json_path("id", exists=True)

    @pytest.mark.parametrize(
        "first_name,age",
        [
            ("Jane", 25),
            ("Bob", 30),
            ("Alice", 28),
        ],
    )
    @pytest.mark.integration
    def test_post_with_csv_and_overrides(self, first_name, age):
        """Test POST endpoint with CSV data and overrides using parametrization."""
        # Load CSV data and override specific values
        user_data = self.load_csv_as_dict("templates/user-data.csv")
        user_data["firstName"] = first_name  # Override
        user_data["age"] = age  # Override

        json_body = self.render_template("templates/user-create.json.j2", user_data)

        response = self.authenticated_request.post("/users", body=json_body)
        response.should_have.status_code(201)

    @pytest.mark.parametrize("user_data", [
        pytest.param({"firstName": "User1", "lastName": "Test", "email": "user1@test.com", "age": 25}, id="user1"),
        pytest.param({"firstName": "User2", "lastName": "Test", "email": "user2@test.com", "age": 30}, id="user2"),
    ])
    @pytest.mark.integration
    def test_multiple_users_from_csv(self, user_data):
        """Test creating multiple users using pytest parametrization."""
        # Render template with user data
        json_body = self.render_template("templates/user-create.json.j2", user_data)
        response = self.authenticated_request.post("/users", body=json_body)
        response.should_have.status_code(201)
        response.should_have.json_path("id", exists=True)

    @pytest.mark.security
    @pytest.mark.parametrize("endpoint", ["/my/endpoint", "/users", "/admin"])
    def test_unauthorized_access(self, endpoint):
        """Test unauthorized access without token using parametrization."""
        response = self.unauthenticated_request.get(endpoint)

        # Accept multiple status codes
        response.should_have.status_code_in([401, 403])

    @pytest.mark.integration
    def test_response_validation_examples(self):
        """Example of various Pythonic response validation patterns."""
        response = self.authenticated_request.get("/users/123")

        # Status code validation
        response.should_have.status_code(200)
        response.should_have.status_code_in([200, 201])

        # Content type validation
        response.should_have.content_type("application/json")

        # JSON path validation - equality
        response.should_have.json_path("id", equals=123)
        response.should_have.json_path("name", equals="John Doe")

        # JSON path validation - existence
        response.should_have.json_path("email", exists=True)
        response.should_have.json_path("nonexistent", exists=False)

        # JSON path validation - regex matching
        import re
        response.should_have.json_path(
            "email", matches=r"^[^@]+@[^@]+\.[^@]+$"
        )

        # JSON path validation - custom validation
        response.should_have.json_path(
            "age", validate=lambda x: 18 <= x <= 100
        )

        # Extract values
        user_id = response.json_path("id")
        user_name = response.json_path("name")
        assert user_id == 123
        assert user_name == "John Doe"

    @pytest.mark.parametrize(
        "page,limit,expected_status",
        [
            ("1", "10", 200),
            ("2", "20", 200),
            ("0", "5", 200),  # Edge case
        ],
    )
    @pytest.mark.integration
    def test_query_parameters(self, page, limit, expected_status):
        """Test GET request with query parameters using parametrization."""
        response = (
            self.authenticated_request.get("/users")
            .query_param("page", page)
            .query_param("limit", limit)
        )

        response.should_have.status_code(expected_status)

    @pytest.mark.integration
    def test_custom_headers(self):
        """Test request with custom headers."""
        response = (
            self.authenticated_request.get("/my/endpoint")
            .header("X-Custom-Header", "custom-value")
        )

        response.should_have.status_code(200)

    @pytest.mark.integration
    def test_response_extraction(self):
        """Test extracting values from response."""
        response = self.authenticated_request.get("/users/123")

        # Extract as string
        response_text = response.extract.as_string()

        # Extract as JSON
        json_data = response.extract.as_json()
        assert isinstance(json_data, dict)

        # Extract specific path
        user_id = response.extract.path("id")
        user_name = response.extract.path("name", default="Unknown")

        assert user_id is not None
        assert user_name is not None

