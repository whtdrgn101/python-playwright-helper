"""Example API test demonstrating the Pythonic testing framework."""

import pytest
from rest_api_testing import BaseApiTest
from rest_api_testing.auth import oauth_scopes

@oauth_scopes("sapi-mule")
class TestExampleAPI(BaseApiTest):
    """Example API test class demonstrating the testing pattern."""

    @pytest.mark.smoke
    @oauth_scopes("read:users")
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
            "../templates/user-create.json.j2",
            {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com",
                "age": 30,
                "phoneNumber": "555-1234",
            }
        )

        # Make authenticated POST request
        response = self.authenticated_request.post("/users", body=json_body)

        response.should_have.status_code(201)
        response.should_have.json_path("id", exists=True)

   
