from src.exceptions import DomainError


class UserAlreadyExists(DomainError):
    status_code = 409
    code = "user_already_exists"

    def __init__(self, email: str):
        super().__init__(f"User with email {email} already exists")


class InvalidCredentials(DomainError):
    status_code = 401
    code = "invalid_credentials"

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InvalidToken(DomainError):
    status_code = 401
    code = "invalid_token"

    def __init__(self) -> None:
        super().__init__("Invalid or expired token")
