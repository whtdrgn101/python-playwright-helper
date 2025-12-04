import pytest
from rest_api_testing import BaseApiTest
from rest_api_testing.auth import oauth_scopes

@oauth_scopes("pingDirectory:users:write","pingDirectory:users:read", "pingDirectory:users:delete")
class TestUserEndpoint(BaseApiTest):
   
   endpointBase = "/sys-ping-directory-v1"
   endpoint = endpointBase + "/api/users"
   healthcheck = endpointBase + "/actuator/health"
   apiDocs = endpointBase + "/api/api-docs"

   async def test_healthcheck(self):
        """Test healthcheck endpoint."""
        request = await self.authenticated_request()
        response = request.get(self.healthcheck)
        await response.should_have.status_code(200)
        await response.should_have.json_path("status", "UP")

   async def test_unauthenticated_request(self):
        """Test unauthenticated request."""
        request = await self.unauthenticated_request()
        response = request.get(self.endpoint)
        await response.should_have.status_code(401)

   async def test_get_api_spec(self):
        """Test retrieving the API specification."""
        request = await self.authenticated_request()
        response = request.get(self.apiDocs)
        await response.should_have.status_code(200)
        await response.should_have.json_path("openapi", "3.1.0")
       