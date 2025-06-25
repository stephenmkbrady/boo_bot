"""
Pytest configuration for BOO_BOT tests
"""

import pytest
import os
import subprocess
import time


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "storage: Storage functionality tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests not requiring external dependencies"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests taking more than 5 seconds"
    )


@pytest.fixture(scope="session")
def api_available():
    """Check if the boo_memories API is available for integration tests"""
    try:
        # Try to connect to the API
        api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
        
        # Use Python urllib since curl may not be available in container
        import urllib.request
        import json
        
        req = urllib.request.Request("http://172.17.0.1:8000/health")
        req.add_header("Authorization", f"Bearer {api_key}")
        response = urllib.request.urlopen(req, timeout=5)
        health_data = json.loads(response.read().decode())
        
        return health_data.get("status") == "healthy"
    except:
        return False


@pytest.fixture(scope="session")
def skip_if_no_api(api_available):
    """Skip test if API is not available"""
    if not api_available:
        pytest.skip("boo_memories API not available - skipping integration test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add storage marker to storage-related tests
        if "storage" in item.nodeid or "file_cycle" in item.nodeid:
            item.add_marker(pytest.mark.storage)
        
        # Add integration marker to tests that need API
        if any(keyword in item.nodeid for keyword in ["integration", "file_cycle", "api"]):
            item.add_marker(pytest.mark.integration)
        
        # Add unit marker to tests that don't need external services
        if "test_storage_simple" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to file cycle tests
        if "file_cycle" in item.nodeid or "automated" in item.nodeid:
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """Setup before each test"""
    # Skip integration tests if API is not available
    if "integration" in [mark.name for mark in item.iter_markers()]:
        api_key = "0DZ9a/sbgajCRmAMO+6SU2qCkw3QqTe5uJaPGa5YptA="
        try:
            import urllib.request
            import json
            
            req = urllib.request.Request("http://172.17.0.1:8000/health")
            req.add_header("Authorization", f"Bearer {api_key}")
            response = urllib.request.urlopen(req, timeout=5)
            health_data = json.loads(response.read().decode())
            
            if health_data.get("status") != "healthy":
                pytest.skip("boo_memories API not healthy - skipping integration test")
        except:
            pytest.skip("boo_memories API not available - skipping integration test")


@pytest.fixture
def temp_test_file():
    """Create a temporary test file for testing"""
    import tempfile
    import hashlib
    
    # Create test data
    test_data = b'\x89PNG\r\n\x1a\n' + b'PYTEST_TEST_DATA_' + b'X' * 1000
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        temp_file.write(test_data)
        temp_path = temp_file.name
    
    yield temp_path, test_data
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)