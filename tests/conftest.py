import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
