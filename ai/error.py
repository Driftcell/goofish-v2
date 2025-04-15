class AiUtilsError(Exception):
    """
    AI工具错误异常类
    用于在AI工具执行过程中捕获和处理特定的错误情况
    继承自Python标准Exception类
    """
    def __init__(self, status_code: int, message: str) -> None:
        """
        初始化AI工具错误异常
        
        参数:
            status_code: int - 错误状态码
            message: str - 错误信息描述
        
        返回:
            None
        """
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        """
        将异常对象转换为字符串
        
        返回:
            str - 格式化的错误信息，包含状态码和错误信息
        """
        return f"AiUtilsError with status code {self.status_code}: {self.message}"
