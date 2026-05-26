from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库连接字符串
    DATABASE_URL: str = "mysql+aiomysql://ecommerce_user:strong_password@localhost:3306/ecommerce_db"
    
    # JWT 配置
    SECRET_KEY: str = "aa065cc2462b488a3f7517e9a0b5abe639f1d0b6d1046d7634013a37b0a124a6"  # 生产环境必须修改
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
