"""Example API test demonstrating the Pythonic testing framework."""

import pytest
from rest_api_testing import BaseApiTest
from rest_api_testing.auth import oauth_scopes


class TestExampleAPI(BaseApiTest):
    """Example API test class demonstrating the testing pattern."""

    # @pytest.mark.smoke
    # @oauth_scopes("read:users")
    # async def test_get_endpoint(self):
    #     """Test GET endpoint with Pythonic validation."""
    #     request = await self.authenticated_request()
    #     response = request.get("/my/endpoint")

    #     # Fluent validation API - should_have is a property, methods are async
    #     await response.should_have.status_code(200)
    #     await response.should_have.content_type("application/json")
    #     await response.should_have.json_path("data.id", exists=True)
    #     await response.should_have.json_path("data.name", equals="expected_value")

    # @pytest.mark.integration
    # async def test_post_with_template(self):
    #     """Test POST endpoint with template rendering."""
    #     # Render template with context
    #     json_body = self.render_template(
    #         "templates/user-create.json.j2",
    #         {
    #             "firstName": "John",
    #             "lastName": "Doe",
    #             "email": "john.doe@example.com",
    #             "age": 30,
    #             "phoneNumber": "555-1234",
    #         },
    #     )

    #     # Make authenticated POST request
    #     request = await self.authenticated_request()
    #     response = request.post("/users", body=json_body)

    #     await response.should_have.status_code(201)
    #     await response.should_have.json_path("id", exists=True)

    # @pytest.mark.integration
    # async def test_post_with_csv_data(self):
    #     """Test POST endpoint with CSV data."""
    #     # Load first row from CSV
    #     user_data = self.load_csv_as_dict("templates/user-data.csv")

    #     # Render template with CSV data
    #     json_body = self.render_template("templates/user-create.json.j2", user_data)

    #     # Make authenticated POST request
    #     request = await self.authenticated_request()
    #     response = request.post("/users", body=json_body)

    #     await response.should_have.status_code(201)
    #     await response.should_have.json_path("id", exists=True)

    # @pytest.mark.parametrize(
    #     "first_name,age",
    #     [
    #         ("Jane", 25),
    #         ("Bob", 30),
    #         ("Alice", 28),
    #     ],
    # )
    # @pytest.mark.integration
    # async def test_post_with_csv_and_overrides(self, first_name, age):
    #     """Test POST endpoint with CSV data and overrides using parametrization."""
    #     # Load CSV data and override specific values
    #     user_data = self.load_csv_as_dict("templates/user-data.csv")
    #     user_data["firstName"] = first_name  # Override
    #     user_data["age"] = age  # Override

    #     json_body = self.render_template("templates/user-create.json.j2", user_data)

    #     request = await self.authenticated_request()
    #     response = request.post("/users", body=json_body)
    #     await response.should_have.status_code(201)

    # @pytest.mark.parametrize("user_data", [
    #     pytest.param({"firstName": "User1", "lastName": "Test", "email": "user1@test.com", "age": 25}, id="user1"),
    #     pytest.param({"firstName": "User2", "lastName": "Test", "email": "user2@test.com", "age": 30}, id="user2"),
    # ])
    # @pytest.mark.integration
    # async def test_multiple_users_from_csv(self, user_data):
    #     """Test creating multiple users using pytest parametrization."""
    #     # Render template with user data
    #     json_body = self.render_template("templates/user-create.json.j2", user_data)
    #     request = await self.authenticated_request()
    #     response = request.post("/users", body=json_body)
    #     await response.should_have.status_code(201)
    #     await response.should_have.json_path("id", exists=True)

    # @pytest.mark.security
    # @pytest.mark.parametrize("endpoint", ["/my/endpoint", "/users", "/admin"])
    # async def test_unauthorized_access(self, endpoint):
    #     """Test unauthorized access without token using parametrization."""
    #     request = await self.unauthenticated_request()
    #     response = request.get(endpoint)

    #     # Accept multiple status codes
    #     await response.should_have.status_code_in([401, 403])

    # @pytest.mark.integration
    # async def test_response_validation_examples(self):
    #     """Example of various Pythonic response validation patterns."""
    #     request = await self.authenticated_request()
    #     response = request.get("/users/123")

    #     # Status code validation
    #     await response.should_have.status_code(200)
    #     await response.should_have.status_code_in([200, 201])

    #     # Content type validation
    #     await response.should_have.content_type("application/json")

    #     # JSON path validation - equality
    #     await response.should_have.json_path("id", equals=123)
    #     await response.should_have.json_path("name", equals="John Doe")

    #     # JSON path validation - existence
    #     await response.should_have.json_path("email", exists=True)
    #     await response.should_have.json_path("nonexistent", exists=False)

    #     # JSON path validation - regex matching
    #     import re
    #     await response.should_have.json_path(
    #         "email", matches=r"^[^@]+@[^@]+\.[^@]+$"
    #     )

    #     # JSON path validation - custom validation
    #     await response.should_have.json_path(
    #         "age", validate=lambda x: 18 <= x <= 100
    #     )

    #     # Extract values
    #     user_id = await response.json_path("id")
    #     user_name = await response.json_path("name")
    #     assert user_id == 123
    #     assert user_name == "John Doe"

    # @pytest.mark.parametrize(
    #     "page,limit,expected_status",
    #     [
    #         ("1", "10", 200),
    #         ("2", "20", 200),
    #         ("0", "5", 200),  # Edge case
    #     ],
    # )
    # @pytest.mark.integration
    # async def test_query_parameters(self, page, limit, expected_status):
    #     """Test GET request with query parameters using parametrization."""
    #     request = await self.authenticated_request()
    #     response = (
    #         request.get("/users")
    #         .query_param("page", page)
    #         .query_param("limit", limit)
    #     )

    #     await response.should_have.status_code(expected_status)

    # @pytest.mark.integration
    # async def test_custom_headers(self):
    #     """Test request with custom headers."""
    #     request = await self.authenticated_request()
    #     response = (
    #         request.get("/my/endpoint")
    #         .header("X-Custom-Header", "custom-value")
    #     )

    #     await response.should_have.status_code(200)

    # @pytest.mark.integration
    # async def test_response_extraction(self):
    #     """Test extracting values from response."""
    #     request = await self.authenticated_request()
    #     response = request.get("/users/123")

    #     # Extract as string
    #     response_text = await response.extract.as_string()

    #     # Extract as JSON
    #     json_data = await response.extract.as_json()
    #     assert isinstance(json_data, dict)

    #     # Extract specific path
    #     user_id = await response.extract.path("id")
    #     user_name = await response.extract.path("name", default="Unknown")

    #     assert user_id is not None
    #     assert user_name is not None

    async def test_unauthenticated_request(self):
        """Test unauthenticated request."""
        request = await self.unauthenticated_request()
        response = request.get("/users/1")
        await response.should_have.status_code(200)
        await response.should_have.json_path("id", exists=True)
        await response.should_have.json_path("name", exists=True)
        await response.should_have.json_path("email", exists=True)
        await response.should_have.json_path("age", exists=True)
        await response.should_have.json_path("phone", exists=True)
