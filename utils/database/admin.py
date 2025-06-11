from datetime import datetime, timedelta
import time
from unittest import result
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DATE,
    delete,
    select,
    cast,
)
from sqlalchemy.orm import declarative_base
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker, Session

from utils.settings.logger import LoggerFactory
from ..settings.config import EnvConfig
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import HTTPException, Cookie, status
from ..error.exception import *

# Конфигурация
SECRET_KEY = EnvConfig.SECRET_KEY
ALGORITHM = EnvConfig.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = EnvConfig.ACCESS_TOKEN_EXPIRE_MINUTES

# Хеширование паролей
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# База данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./admin.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Модель пользователя
class SuperUser(Base):
    __tablename__ = "superuser"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class ActiveUser(Base):
    __tablename__ = "active_user"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    player_id = Column(Integer)
    region = Column(String)
    data = Column(DATE, default=datetime.now())


Base.metadata.create_all(bind=engine)


def initialize_db():
    with SessionLocal() as session:
        try:
            user = SuperUser(
                username=EnvConfig.SUPERUSER,
                hashed_password=get_password_hash(EnvConfig.PASSWORD),
            )
            session.add(user)
            session.commit()
        except Exception:
            session.rollback()
        LoggerFactory.log("Superuser root created")


# Утилиты
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    with SessionLocal() as session:
        return session.query(SuperUser).filter(SuperUser.username == username).first()


def get_active_users():
    with SessionLocal() as session:
        fourteen_days_ago = (datetime.now() - timedelta(days=14)).date()
        query = select(ActiveUser).filter(
            cast(ActiveUser.data, DATE) < fourteen_days_ago
        )

        result = session.execute(query).scalars().all()
        return result


def add_active_user(name: str, player_id: int, region: str):
    with SessionLocal() as session:
        active_user = ActiveUser(name=name, player_id=player_id, region=region)
        session.add(active_user)
        fourteen_days_ago = (datetime.now() - timedelta(days=14)).date()
        stmt = delete(ActiveUser).where(cast(ActiveUser.data, DATE) < fourteen_days_ago)
        session.execute(stmt)
        session.commit()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire.timestamp()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def valid(admin_token: str = Cookie("admin_token")):
    try:
        payload = jwt.decode(admin_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise InvalidAdminToken
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истёк",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
