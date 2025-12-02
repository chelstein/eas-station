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
    with patch.multiple(
        'webapp.routes_snow_emergencies',
        _ensure_snow_emergencies_table=MagicMock(return_value=True),
        _initialize_counties=MagicMock(),
        SnowEmergency=MagicMock()
    ) as mocks:
        # Setup mock query
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mocks['SnowEmergency'].query = mock_query
        
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


def test_snow_emergency_in_public_paths():
    """Test that snow emergency endpoint is included in PUBLIC_API_GET_PATHS."""
    from app import PUBLIC_API_GET_PATHS
    
    assert '/api/snow_emergencies' in PUBLIC_API_GET_PATHS, \
        "Snow emergency endpoint should be in PUBLIC_API_GET_PATHS for guest access"
