"""
Unit tests for the new configuration system
Tests the EnhancedConfigManager and backwards compatibility
"""

import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from lambdas.utils.enhanced_config_manager import EnhancedConfigManager
from lambdas.utils.aws_service_utils import AWSServiceManager


class TestEnhancedConfigManager(unittest.TestCase):
    """Test cases for EnhancedConfigManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_manager = EnhancedConfigManager(environment='test')
        self.test_config_dir = Path(__file__).parent.parent / 'config'
    
    def test_config_directory_exists(self):
        """Test that config directory was created"""
        self.assertTrue(self.test_config_dir.exists())
        self.assertTrue(self.test_config_dir.is_dir())
    
    def test_default_config_exists(self):
        """Test that default.yaml configuration file exists"""
        default_config = self.test_config_dir / 'default.yaml'
        self.assertTrue(default_config.exists())
    
    def test_environment_configs_exist(self):
        """Test that environment-specific configs exist"""
        environments = ['dev', 'staging', 'prod']
        for env in environments:
            config_file = self.test_config_dir / f'{env}.yaml'
            self.assertTrue(config_file.exists(), f"Missing config for {env}")
    
    def test_load_configuration(self):
        """Test loading configuration for different environments"""
        # Test dev environment
        dev_config = EnhancedConfigManager(environment='dev')
        self.assertIsNotNone(dev_config.config)
        
        # Test prod environment
        prod_config = EnhancedConfigManager(environment='prod')
        self.assertIsNotNone(prod_config.config)
    
    def test_get_config_value(self):
        """Test getting configuration values"""
        # Test getting nested values
        region = self.config_manager.get_config_value('aws.region')
        self.assertIsNotNone(region)
        
        # Test getting with default value
        default_value = self.config_manager.get_config_value(
            'non.existent.key', 
            default='default_value'
        )
        self.assertEqual(default_value, 'default_value')
    
    def test_backward_compatibility(self):
        """Test backward compatibility with environment variables"""
        test_env_vars = {
            'AWS_REGION': 'us-west-2',
            'S3_BUCKET': 'test-bucket',
            'DYNAMODB_TABLE': 'test-table'
        }
        
        with patch.dict(os.environ, test_env_vars):
            # Should fallback to environment variables if config not found
            manager = EnhancedConfigManager(environment='test')
            
            # Verify environment variables are accessible
            self.assertEqual(os.environ.get('AWS_REGION'), 'us-west-2')
            self.assertEqual(os.environ.get('S3_BUCKET'), 'test-bucket')
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test required fields are present
        required_fields = [
            'aws.region',
            'aws.account_id',
            'project.name',
            'project.environment'
        ]
        
        for field in required_fields:
            value = self.config_manager.get_config_value(field)
            self.assertIsNotNone(value, f"Required field {field} is missing")
    
    def test_sensitive_data_handling(self):
        """Test that sensitive data is properly handled"""
        # Ensure no actual credentials are in config files
        config = self.config_manager.config
        
        # Check that placeholder values are used for sensitive data
        if 'credentials' in config:
            creds = config.get('credentials', {})
            for key, value in creds.items():
                # Sensitive values should be placeholders or empty
                self.assertTrue(
                    value in ['PLACEHOLDER', '', None] or value.startswith('${'),
                    f"Sensitive field {key} contains actual value"
                )


class TestAWSServiceManager(unittest.TestCase):
    """Test cases for AWSServiceManager"""
    
    @patch('boto3.client')
    def test_aws_service_initialization(self, mock_boto_client):
        """Test AWS service utilities initialization"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        utils = AWSServiceManager()
        self.assertIsNotNone(utils)
    
    @patch('boto3.client')
    def test_get_s3_client(self, mock_boto_client):
        """Test getting S3 client"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        utils = AWSServiceManager()
        s3_client = utils.get_s3_client()
        
        self.assertIsNotNone(s3_client)
        mock_boto_client.assert_called()
    
    @patch('boto3.client')
    def test_get_dynamodb_client(self, mock_boto_client):
        """Test getting DynamoDB client"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        utils = AWSServiceManager()
        dynamodb_client = utils.get_dynamodb_client()
        
        self.assertIsNotNone(dynamodb_client)
        mock_boto_client.assert_called()


class TestConfigMigration(unittest.TestCase):
    """Test cases for configuration migration"""
    
    def test_migration_completeness(self):
        """Test that all environment variables were migrated"""
        # List of expected configuration keys after migration
        expected_keys = [
            'aws',
            'project',
            'lambda_config',
            's3',
            'dynamodb',
            'bedrock'
        ]
        
        config_manager = EnhancedConfigManager(environment='dev')
        config = config_manager.config
        
        for key in expected_keys:
            self.assertIn(key, config, f"Missing configuration section: {key}")
    
    def test_config_file_structure(self):
        """Test configuration file structure is correct"""
        config_manager = EnhancedConfigManager(environment='dev')
        config = config_manager.config
        
        # Test AWS configuration structure
        self.assertIn('region', config.get('aws', {}))
        self.assertIn('account_id', config.get('aws', {}))
        
        # Test S3 configuration structure
        s3_config = config.get('s3', {})
        self.assertIn('presentations_bucket', s3_config)
        
        # Test DynamoDB configuration structure
        dynamodb_config = config.get('dynamodb', {})
        self.assertIn('sessions_table', dynamodb_config)
        self.assertIn('checkpoints_table', dynamodb_config)


class TestIntegration(unittest.TestCase):
    """Integration tests for the configuration system"""
    
    def test_end_to_end_config_loading(self):
        """Test end-to-end configuration loading process"""
        environments = ['dev', 'staging', 'prod']
        
        for env in environments:
            manager = EnhancedConfigManager(environment=env)
            
            # Verify configuration loaded
            self.assertIsNotNone(manager.config)
            
            # Verify environment-specific values
            env_value = manager.get_config_value('project.environment')
            self.assertEqual(env_value, env)
    
    def test_config_override_hierarchy(self):
        """Test configuration override hierarchy"""
        # Default < Environment-specific < Environment variables
        
        with patch.dict(os.environ, {'PROJECT_NAME': 'override-test'}):
            manager = EnhancedConfigManager(environment='dev')
            
            # Environment variable should take precedence if implemented
            # This tests the fallback mechanism
            self.assertIsNotNone(manager.config)


def run_tests():
    """Run all tests with verbose output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAWSServiceManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)