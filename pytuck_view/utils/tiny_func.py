import socket
import traceback
from pathlib import Path


def simplify_exception(err: Exception) -> str:
    """简化错误日志"""
    msg = "".join(traceback.format_exception(err)).replace(str(Path.cwd()), "")
    return f"{err.__class__.__name__}: {err}\nAt: \n{msg}"


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否可用

    :param port: 端口号
    :param host: 主机地址，默认 127.0.0.1
    :return: 端口可用返回 True，否则返回 False
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """从指定端口开始查找可用端口，若占用则递增

    :param start_port: 起始端口号
    :param max_attempts: 最大尝试次数，默认 100
    :return: 可用端口号
    :raises RuntimeError: 无法找到可用端口时抛出
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(port):
            return port
    end_port = start_port + max_attempts - 1
    raise RuntimeError(f"无法找到可用端口（尝试范围: {start_port}-{end_port}）")
