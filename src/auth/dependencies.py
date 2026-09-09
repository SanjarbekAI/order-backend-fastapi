from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.exceptions import InvalidToken
from src.auth.utils import decode_access_token
from src.exceptions import NotAuthenticated

# auto_error=False so a missing/blank header becomes our own 401 (with a
# WWW-Authenticate header) instead of Starlette's bare 403.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> int:
    if credentials is None:
        raise NotAuthenticated()
    try:
        return decode_access_token(credentials.credentials)
    except InvalidToken as exc:
        raise NotAuthenticated(exc.message) from exc


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
