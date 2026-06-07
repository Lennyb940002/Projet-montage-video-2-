import os, pytest

@pytest.fixture
def sample_audio():
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.mp3")
