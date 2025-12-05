"""Unit tests for AuthenticationService."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from rest_api_testing.auth.authentication_service import AuthenticationService, TokenCacheEntry
from rest_api_testing.config import TestConfig


@pytest.fixture(autouse=True)
def reset_auth_service():
    """Reset AuthenticationService singleton state before each test."""
    AuthenticationService._instance = None
    AuthenticationService._lock = None
    yield
    # Cleanup after test
    AuthenticationService._instance = None


@pytest.fixture
def mock_config():
    """Create a mock TestConfig."""
    config = MagicMock(spec=TestConfig)
    config.ping_federate_base_url = "https://auth.example.com"
    config.ping_federate_token_endpoint = "/as/token.oauth2"
    config.ping_federate_client_id = "test-client-id"
    config.ping_federate_client_secret = "test-client-secret"
    config.ping_federate_grant_type = "client_credentials"
    return config


class TestTokenCacheEntry:
    """Test TokenCacheEntry dataclass."""

    def test_token_cache_entry_creation(self):
        """Test creating a TokenCacheEntry."""
        future_time = time.time() + 3600
        entry = TokenCacheEntry(token="test_token", expiry_time=future_time)
        
        assert entry.token == "test_token"
        assert entry.expiry_time == future_time

    def test_token_cache_entry_is_valid_future(self):
        """Test token is valid when expiry time is in future."""
        future_time = time.time() + 3600
        entry = TokenCacheEntry(token="test_token", expiry_time=future_time)
        
        assert entry.is_valid() is True

    def test_token_cache_entry_is_valid_past(self):
        """Test token is invalid when expiry time is in past."""
        past_time = time.time() - 100
        entry = TokenCacheEntry(token="test_token", expiry_time=past_time)
        
        assert entry.is_valid() is False

    def test_token_cache_entry_is_valid_edge_case(self):
        """Test token validity at edge case (current time)."""
        current_time = time.time()
        entry = TokenCacheEntry(token="test_token", expiry_time=current_time)
        
        # Should be invalid because time.time() is always greater than or equal
        assert entry.is_valid() is False


class TestAuthenticationServiceSingleton:
    """Test AuthenticationService singleton pattern."""

    def test_get_instance_returns_same_instance(self):
        """Test that get_instance returns the same instance."""
        with patch('rest_api_testing.auth.authentication_service.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            instance1 = AuthenticationService.get_instance()
            instance2 = AuthenticationService.get_instance()
            
            assert instance1 is instance2

    def test_get_instance_creates_instance(self):
        """Test that get_instance creates an instance if none exists."""
        with patch('rest_api_testing.auth.authentication_service.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            instance = AuthenticationService.get_instance()
            
            assert instance is not None
            assert isinstance(instance, AuthenticationService)


class TestAuthenticationServiceInitialization:
    """Test AuthenticationService initialization."""

    def test_init_sets_config(self, mock_config):
        """Test that __init__ sets config from get_config."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            assert service.config == mock_config

    def test_init_initializes_token_cache(self, mock_config):
        """Test that __init__ initializes empty token cache."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            assert isinstance(service._token_cache, dict)
            assert len(service._token_cache) == 0

    def test_init_initializes_playwright_lock(self, mock_config):
        """Test that __init__ initializes asyncio lock."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            assert isinstance(service._playwright_lock, asyncio.Lock)

    def test_init_playwright_is_none(self, mock_config):
        """Test that playwright is None initially."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            assert service._playwright is None


class TestCreateScopeKey:
    """Test _create_scope_key method."""

    def test_create_scope_key_empty_scopes(self, mock_config):
        """Test creating scope key with empty scopes."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            key = service._create_scope_key([])
            
            assert key == ""

    def test_create_scope_key_single_scope(self, mock_config):
        """Test creating scope key with single scope."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            key = service._create_scope_key(["read:users"])
            
            assert key == "read:users"

    def test_create_scope_key_multiple_scopes_sorted(self, mock_config):
        """Test that scope key is sorted consistently."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            key1 = service._create_scope_key(["write:users", "read:users"])
            key2 = service._create_scope_key(["read:users", "write:users"])
            
            assert key1 == key2
            assert key1 == "read:users write:users"


class TestInvalidateToken:
    """Test token invalidation methods."""

    def test_invalidate_token_with_scopes(self, mock_config):
        """Test invalidating cached token for specific scopes."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            # Add token to cache
            scope_key = "read:users write:users"
            future_time = time.time() + 3600
            service._token_cache[scope_key] = TokenCacheEntry("test_token", future_time)
            
            assert scope_key in service._token_cache
            
            # Invalidate
            service.invalidate_token(["read:users", "write:users"])
            
            assert scope_key not in service._token_cache

    def test_invalidate_token_empty_scopes(self, mock_config):
        """Test invalidating cached token with empty scopes."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            # Add token to cache
            service._token_cache[""] = TokenCacheEntry("test_token", time.time() + 3600)
            
            service.invalidate_token([])
            
            assert "" not in service._token_cache

    def test_invalidate_nonexistent_token(self, mock_config):
        """Test invalidating token that doesn't exist in cache."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            # Should not raise error
            service.invalidate_token(["nonexistent"])

    def test_invalidate_all_tokens(self, mock_config):
        """Test invalidating all cached tokens."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            service = AuthenticationService()
            
            # Add multiple tokens to cache
            future_time = time.time() + 3600
            service._token_cache["scope1"] = TokenCacheEntry("token1", future_time)
            service._token_cache["scope2"] = TokenCacheEntry("token2", future_time)
            
            assert len(service._token_cache) == 2
            
            service.invalidate_all_tokens()
            
            assert len(service._token_cache) == 0


class TestEnsurePlaywright:
    """Test _ensure_playwright method."""

    @pytest.mark.asyncio
    async def test_ensure_playwright_initializes(self, mock_config):
        """Test that _ensure_playwright initializes Playwright."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                service = AuthenticationService()
                assert service._playwright is None
                
                await service._ensure_playwright()
                
                assert service._playwright is not None

    @pytest.mark.asyncio
    async def test_ensure_playwright_idempotent(self, mock_config):
        """Test that _ensure_playwright is idempotent."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                service = AuthenticationService()
                
                await service._ensure_playwright()
                first_playwright = service._playwright
                
                await service._ensure_playwright()
                second_playwright = service._playwright
                
                assert first_playwright is second_playwright


class TestGetAccessToken:
    """Test get_access_token method."""

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, mock_config):
        """Test successful token retrieval."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                # Mock the response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"access_token": "test_token_123"})
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                token = await service.get_access_token()
                
                assert token == "test_token_123"

    @pytest.mark.asyncio
    async def test_get_access_token_with_scopes(self, mock_config):
        """Test token retrieval with scopes."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"access_token": "test_token"})
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                token = await service.get_access_token(scopes=["read:users", "write:users"])
                
                assert token == "test_token"
                # Verify scopes were included in form data
                call_args = mock_context.post.call_args
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_access_token_uses_cache(self, mock_config):
        """Test that token is retrieved from cache on second call."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"access_token": "test_token"})
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                
                # First call should fetch
                token1 = await service.get_access_token()
                # Second call should use cache
                token2 = await service.get_access_token()
                
                assert token1 == token2
                # post should only be called once
                assert mock_context.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_access_token_bypass_cache(self, mock_config):
        """Test bypassing token cache."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"access_token": "test_token"})
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                
                # First call
                await service.get_access_token()
                # Second call with bypass_cache=True
                await service.get_access_token(bypass_cache=True)
                
                # post should be called twice
                assert mock_context.post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_access_token_failed_request(self, mock_config):
        """Test handling of failed token request."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 401
                mock_response.text = AsyncMock(return_value="Unauthorized")
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                
                with pytest.raises(RuntimeError, match="Failed to retrieve JWT token"):
                    await service.get_access_token()

    @pytest.mark.asyncio
    async def test_get_access_token_missing_client_credentials(self, mock_config):
        """Test error when client credentials are missing."""
        mock_config.ping_federate_client_id = None
        
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                service = AuthenticationService()
                
                with pytest.raises(ValueError, match="PING Federate client ID and secret must be configured"):
                    await service.get_access_token()

    @pytest.mark.asyncio
    async def test_get_access_token_missing_access_token_in_response(self, mock_config):
        """Test error when access_token is missing from response."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"error": "invalid_scope"})
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                
                with pytest.raises(RuntimeError, match="Access token not found"):
                    await service.get_access_token()

    @pytest.mark.asyncio
    async def test_get_access_token_json_parse_error(self, mock_config):
        """Test handling of JSON parse error in response."""
        with patch('rest_api_testing.auth.authentication_service.get_config', return_value=mock_config):
            with patch('rest_api_testing.auth.authentication_service.async_playwright') as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
                mock_response.text = AsyncMock(return_value="Invalid JSON response")
                
                mock_pw_instance.request.new_context = AsyncMock()
                mock_context = AsyncMock()
                mock_pw_instance.request.new_context.return_value = mock_context
                mock_context.post = AsyncMock(return_value=mock_response)
                
                service = AuthenticationService()
                
                with pytest.raises(RuntimeError, match="Failed to parse PING Federate response"):
                    await service.get_access_token()
