class AiUtilsError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        return f"AiUtilsError with status code {self.status_code}: {self.message}"
