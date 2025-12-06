"""
Unit tests for database configuration utilities.

Tests the functions in app_core.config.database module.
"""

import pytest
from app_core.config.database import build_database_url


class TestBuildDatabaseUrl:
    """Tests for build_database_url function."""
    
    def test_database_url_takes_precedence(self, monkeypatch):
        """Test that DATABASE_URL environment variable takes precedence."""
        monkeypatch.setenv('DATABASE_URL', 'postgresql://custom:url@custom-host:5433/custom-db')
        monkeypatch.setenv('POSTGRES_HOST', 'other-host')
        monkeypatch.setenv('POSTGRES_USER', 'other-user')
        
        result = build_database_url()
        assert result == 'postgresql://custom:url@custom-host:5433/custom-db'
    
    def test_default_values(self, monkeypatch):
        """Test that default values are used when no env vars are set."""
        # Remove all database env vars
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.delenv('POSTGRES_HOST', raising=False)
        monkeypatch.delenv('POSTGRES_PORT', raising=False)
        monkeypatch.delenv('POSTGRES_DB', raising=False)
        monkeypatch.delenv('POSTGRES_USER', raising=False)
        monkeypatch.delenv('POSTGRES_PASSWORD', raising=False)
        
        result = build_database_url()
        assert result == 'postgresql+psycopg2://postgres:postgres@alerts-db:5432/alerts'
    
    def test_custom_values(self, monkeypatch):
        """Test with all custom environment variables."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_HOST', 'db.example.com')
        monkeypatch.setenv('POSTGRES_PORT', '5433')
        monkeypatch.setenv('POSTGRES_DB', 'production')
        monkeypatch.setenv('POSTGRES_USER', 'appuser')
        monkeypatch.setenv('POSTGRES_PASSWORD', 'secretpass')
        
        result = build_database_url()
        assert result == 'postgresql+psycopg2://appuser:secretpass@db.example.com:5433/production'
    
    def test_special_characters_in_password(self, monkeypatch):
        """Test that special characters in password are URL-encoded."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_USER', 'user')
        monkeypatch.setenv('POSTGRES_PASSWORD', 'pass@word#123')
        monkeypatch.setenv('POSTGRES_HOST', 'localhost')
        
        result = build_database_url()
        # @ should be encoded as %40, # as %23
        assert 'pass%40word%23123' in result
        assert result == 'postgresql+psycopg2://user:pass%40word%23123@localhost:5432/alerts'
    
    def test_special_characters_in_username(self, monkeypatch):
        """Test that special characters in username are URL-encoded."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_USER', 'app@user')
        monkeypatch.setenv('POSTGRES_PASSWORD', 'pass')
        monkeypatch.setenv('POSTGRES_HOST', 'localhost')
        
        result = build_database_url()
        assert 'app%40user' in result
        assert result == 'postgresql+psycopg2://app%40user:pass@localhost:5432/alerts'
    
    def test_empty_password(self, monkeypatch):
        """Test handling of empty password."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_USER', 'user')
        monkeypatch.setenv('POSTGRES_PASSWORD', '')
        monkeypatch.setenv('POSTGRES_HOST', 'localhost')
        
        result = build_database_url()
        # Should not include colon when password is empty
        assert result == 'postgresql+psycopg2://user@localhost:5432/alerts'
    
    def test_no_password_env_var(self, monkeypatch):
        """Test when POSTGRES_PASSWORD is not set (falls back to default)."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_USER', 'user')
        monkeypatch.delenv('POSTGRES_PASSWORD', raising=False)
        monkeypatch.setenv('POSTGRES_HOST', 'localhost')
        
        result = build_database_url()
        # Default password 'postgres' should be used
        assert result == 'postgresql+psycopg2://user:postgres@localhost:5432/alerts'
    
    def test_localhost_configuration(self, monkeypatch):
        """Test typical localhost development configuration."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_HOST', 'localhost')
        monkeypatch.setenv('POSTGRES_USER', 'dev')
        monkeypatch.setenv('POSTGRES_PASSWORD', 'dev')
        monkeypatch.setenv('POSTGRES_DB', 'eas_dev')
        
        result = build_database_url()
        assert result == 'postgresql+psycopg2://dev:dev@localhost:5432/eas_dev'
    
    def test_ipv6_host(self, monkeypatch):
        """Test with IPv6 address as host."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_HOST', '::1')
        monkeypatch.setenv('POSTGRES_USER', 'user')
        monkeypatch.setenv('POSTGRES_PASSWORD', 'pass')
        
        result = build_database_url()
        assert result == 'postgresql+psycopg2://user:pass@::1:5432/alerts'
    
    def test_custom_port(self, monkeypatch):
        """Test with non-standard PostgreSQL port."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setenv('POSTGRES_PORT', '15432')
        monkeypatch.setenv('POSTGRES_HOST', 'db.example.com')
        
        result = build_database_url()
        assert ':15432/' in result
