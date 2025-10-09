import pytest
import os
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig, config

class TestConfig:
    """Test base configuration"""
    
    def test_base_config_has_secret_key(self):
        """Test base config has secret key"""
        assert hasattr(Config, 'SECRET_KEY')
        assert Config.SECRET_KEY is not None
    
    def test_sqlalchemy_track_modifications_disabled(self):
        """Test SQLAlchemy track modifications is disabled"""
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False

class TestDevelopmentConfig:
    """Test development configuration"""
    
    def test_debug_enabled(self):
        """Test debug mode is enabled in development"""
        assert DevelopmentConfig.DEBUG is True
    
    def test_has_database_uri(self):
        """Test development config has database URI"""
        assert hasattr(DevelopmentConfig, 'SQLALCHEMY_DATABASE_URI')
        assert DevelopmentConfig.SQLALCHEMY_DATABASE_URI is not None

class TestTestingConfig:
    """Test testing configuration"""
    
    def test_testing_enabled(self):
        """Test testing flag is enabled"""
        assert TestingConfig.TESTING is True
    
    def test_uses_sqlite_memory(self):
        """Test testing uses SQLite in-memory database"""
        assert 'sqlite:///:memory:' in TestingConfig.SQLALCHEMY_DATABASE_URI
    
    def test_csrf_disabled(self):
        """Test CSRF is disabled for testing"""
        assert TestingConfig.WTF_CSRF_ENABLED is False

class TestProductionConfig:
    """Test production configuration"""
    
    def test_debug_disabled(self):
        """Test debug mode is disabled in production"""
        assert ProductionConfig.DEBUG is False
    
    def test_requires_database_url(self, monkeypatch):
        """Test production requires DATABASE_URL environment variable"""
        # Remove DATABASE_URL if it exists
        monkeypatch.delenv('DATABASE_URL', raising=False)
        
        from app import create_app
        with pytest.raises(AssertionError):
            app = create_app('production')

class TestConfigSelector:
    """Test configuration selector"""
    
    def test_config_contains_all_environments(self):
        """Test config dict has all environment configurations"""
        assert 'development' in config
        assert 'testing' in config
        assert 'production' in config
        assert 'default' in config
    
    def test_default_is_development(self):
        """Test default configuration is development"""
        assert config['default'] == DevelopmentConfig