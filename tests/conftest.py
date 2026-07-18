import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import create_app
from app.seed.seed_v2 import seed_v2

@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    seed_v2(session)
    yield session
    session.close()

@pytest.fixture(scope="function")
def client(db):
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def _login(client, email, password="Demo@123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

@pytest.fixture
def fresher_token(client):
    return _login(client, "fresher@skillflow.local")

@pytest.fixture
def pm_token(client):
    return _login(client, "pm@skillflow.local")

@pytest.fixture
def fresher_headers(fresher_token):
    return {"Authorization": f"Bearer {fresher_token}"}

@pytest.fixture
def pm_headers(pm_token):
    return {"Authorization": f"Bearer {pm_token}"}
