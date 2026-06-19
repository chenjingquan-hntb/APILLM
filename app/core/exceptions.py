from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str = "error"):
        super().__init__(status_code=status_code, detail={"code": code, "message": detail})


class AuthError(AppError):
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "auth_error")


class NotFoundError(AppError):
    def __init__(self, resource: str):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found", "not_found")


class UpstreamError(AppError):
    def __init__(self, detail: str, upstream_name: str = ""):
        super().__init__(status.HTTP_502_BAD_GATEWAY, detail, "upstream_error")


class NoAvailableUpstreamError(AppError):
    def __init__(self):
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, "No available upstream", "no_upstream")
