"""
项目配置模块
统一管理环境变量和配置项
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


def parse_comma_separated(v: str) -> List[str]:
    """解析逗号分隔的字符串为列表"""
    if not v:
        return []
    return [item.strip() for item in v.split(",") if item.strip()]


class Settings(BaseSettings):
    # 企微凭证
    WECOM_CORP_ID: str
    WECOM_AGENT_ID: str
    WECOM_SECRET: str

    # 数据库
    DATABASE_URL: str = "mysql+aiomysql://perf:perf2026@localhost:3306/perf_system"

    # 应用
    APP_SECRET_KEY: str = "change-me-in-production"
    APP_BASE_URL: str = "http://localhost:8000"

    # 开发模式（仅开发环境启用，生产环境务必设为 false）
    DEV_MODE: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 管理员用户列表（企微userid，逗号分隔）
    ADMIN_USERS: str = ""

    # HR人员列表（企微userid，逗号分隔）
    # 优先于职位硬编码判断，当配置后将覆盖基于职位的HR识别逻辑
    HR_USERS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_admin_users(self) -> List[str]:
        """获取管理员用户列表"""
        return parse_comma_separated(self.ADMIN_USERS)

    def get_hr_users(self) -> List[str]:
        """获取HR人员列表"""
        return parse_comma_separated(self.HR_USERS)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
