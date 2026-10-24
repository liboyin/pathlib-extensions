import logging

import pytest


@pytest.fixture
def package_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Capture INFO and higher records from every pathlib_extensions logger, so silence checks cover all modules."""
    caplog.set_level(logging.INFO, logger='pathlib_extensions')
    return caplog
