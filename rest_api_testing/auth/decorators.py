"""Decorators for OAuth scope management and token cache control in tests."""

from typing import List, Union, Callable, Any


def bypass_token_cache(obj: Any = None) -> Any:
    """
    Decorator to bypass token cache for a test method or class.

    When applied, the test will always fetch a fresh token instead of using cached tokens.

    Usage:
        @bypass_token_cache
        def test_something(self):
            ...

        @bypass_token_cache
        class TestAdminAPI(BaseApiTest):
            ...

    Args:
        obj: The function or class to decorate (handles both with and without parentheses)

    Returns:
        Decorated object with _bypass_token_cache metadata
    """
    def decorator(target: Any) -> Any:
        """Attach bypass cache metadata to the decorated object."""
        setattr(target, "_bypass_token_cache", True)
        return target
    
    # Handle both @bypass_token_cache and @bypass_token_cache() syntax
    if obj is None:
        return decorator
    else:
        return decorator(obj)


def oauth_scopes(*scopes: Union[str, List[str]]) -> Callable:
    """
    Decorator to specify OAuth scopes for a test method or class.

    Usage:
        @oauth_scopes("read:users", "write:users")
        def test_something(self):
            ...

        @oauth_scopes("admin:all")
        class TestAdminAPI(BaseApiTest):
            ...

    Args:
        *scopes: Variable number of scope strings or lists of scope strings

    Returns:
        Decorator function that attaches scope metadata to the decorated object
    """
    # Flatten scopes - handle both strings and lists
    scope_list: List[str] = []
    for scope in scopes:
        if isinstance(scope, str):
            scope_list.append(scope)
        elif isinstance(scope, (list, tuple)):
            scope_list.extend(scope)
    
    def decorator(obj: Any) -> Any:
        """Attach scopes metadata to the decorated object."""
        # Store scopes as metadata on the object
        setattr(obj, "_oauth_scopes", scope_list)
        return obj
    
    return decorator

