"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

Repository: https://github.com/KR8MER/eas-station

Tests for snow emergency public access on index page.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_snow_emergency_endpoint_is_public(app_client):
    """Test that the snow emergency endpoint is accessible without authentication."""
    # Mock the database query to avoid database dependencies
    with patch('webapp.routes_snow_emergencies._ensure_snow_emergencies_table', return_value=True):
        with patch('webapp.routes_snow_emergencies._initialize_counties'):
            with patch('webapp.routes_snow_emergencies.SnowEmergency') as mock_snow:
                # Setup mock query
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = []
                mock_snow.query = mock_query
                
                # Make request without authentication
                response = app_client.get('/api/snow_emergencies')
                
                # Should return 200 OK for guests (not 401 Unauthorized)
                assert response.status_code == 200, \
                    f"Expected 200 OK for public access, got {response.status_code}"
                
                # Should return valid JSON
                data = response.get_json()
                assert data is not None, "Response should contain JSON data"
                assert 'emergencies' in data, "Response should contain 'emergencies' key"
                assert 'levels' in data, "Response should contain 'levels' key"


def test_snow_emergency_in_public_paths(app):
    """Test that snow emergency endpoint is included in PUBLIC_API_GET_PATHS."""
    from app import PUBLIC_API_GET_PATHS
    
    assert '/api/snow_emergencies' in PUBLIC_API_GET_PATHS, \
        "Snow emergency endpoint should be in PUBLIC_API_GET_PATHS for guest access"


# Fixture for creating test client
@pytest.fixture
def app_client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def app():
    """Create and configure a test Flask app instance."""
    import os
    os.environ['SKIP_DB_INIT'] = '1'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SETUP_MODE'] = False
    
    return flask_app
