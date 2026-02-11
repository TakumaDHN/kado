"""Validation utilities"""
import re


def validate_mac_address(mac_addr: str) -> bool:
    """MACアドレスの形式を検証"""
    # 12桁の16進数（コロンやハイフンなし）
    pattern = r'^[0-9A-Fa-f]{12}$'
    return bool(re.match(pattern, mac_addr))
