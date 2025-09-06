#!/usr/bin/env python3
"""
Migration Script: Environment Variables to YAML Configuration
AI PPT Assistant - Config Migration Tool
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    print("PyYAML not installed. Please run: pip install PyYAML")
    sys.exit(1)

class ConfigMigrator:
    """Migrate from environment variables to YAML configuration files"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.environments_dir = self.config_dir / "environments"
        
        # Environment variable mappings to config paths
        self.env_var_mappings = {
            # AWS Configuration
            'AWS_REGION': 'aws.region',
            'AWS_PROFILE': 'aws.profile',
            
            # S3 Configuration
            'S3_BUCKET': 'services.s3.bucket',
            'TEMPLATES_BUCKET': 'services.s3.templates_bucket',
            
            # DynamoDB Configuration
            'DYNAMODB_TABLE': 'services.dynamodb.table',
            'SESSIONS_TABLE': 'services.dynamodb.table',
            'CHECKPOINTS_TABLE': 'services.dynamodb.checkpoints_table',
            
            # SQS Configuration
            'SQS_QUEUE_URL': 'services.sqs.queue_url',
            
            # Bedrock Configuration
            'BEDROCK_MODEL_ID': 'services.bedrock.model_id',
            'NOVA_MODEL_ID': 'services.bedrock.nova_model_id',
            'IMAGE_MODEL_ID': 'services.bedrock.nova_model_id',
            'ORCHESTRATOR_AGENT_ID': 'services.bedrock.orchestrator_agent_id',
            'CONTENT_AGENT_ID': 'services.bedrock.content_agent_id',
            'VISUAL_AGENT_ID': 'services.bedrock.visual_agent_id',
            'COMPILER_AGENT_ID': 'services.bedrock.compiler_agent_id',
            
            # Performance Configuration
            'MAX_CONCURRENT_DOWNLOADS': 'performance.max_concurrent_downloads',
            'MAX_CONCURRENT_IMAGES': 'performance.max_concurrent_images',
            'MAX_CONCURRENT_SLIDES': 'performance.max_concurrent_slides',
            'IMAGE_DOWNLOAD_TIMEOUT': 'performance.image_download_timeout',
            'CACHE_TTL_SECONDS': 'performance.cache_ttl_seconds',
            'MAX_SLIDES': 'performance.max_slides',
            'MIN_SLIDES': 'performance.min_slides',
            'MAX_IMAGE_SIZE_MB': 'performance.max_image_size_mb',
            'BATCH_SIZE': 'performance.batch_size',
            'CHECKPOINT_TTL_HOURS': 'performance.checkpoint_ttl_hours',
            'MAX_CHECKPOINTS_PER_TASK': 'performance.max_checkpoints_per_task',
            'DEFAULT_SECONDS_PER_SLIDE': 'performance.default_seconds_per_slide',
            'MAX_SEARCH_RESULTS': 'performance.max_search_results',
            'MAX_TEMPLATE_SIZE_MB': 'performance.max_template_size_mb',
            'DEFAULT_IMAGE_SIZE': 'performance.default_image_size',
            
            # Security Configuration
            'VPC_ENABLED': 'security.vpc_enabled',
            'VPC_ID': 'security.vpc_id',
            'API_RATE_LIMIT': 'security.api_rate_limit',
            'ENABLE_REKOGNITION': 'security.enable_rekognition',
            'PEXELS_API_KEY': 'security.external_apis.pexels_api_key',
            'PIXABAY_API_KEY': 'security.external_apis.pixabay_api_key',
            'UNSPLASH_ACCESS_KEY': 'security.external_apis.unsplash_access_key',
            
            # Monitoring Configuration
            'LOG_LEVEL': 'monitoring.log_level',
            'ALERT_EMAIL': 'monitoring.alert_email',
            'DOWNLOAD_EXPIRY_SECONDS': 'monitoring.download_expiry_seconds',
            
            # Project Metadata
            'PROJECT_NAME': 'metadata.project_name',
            'ENVIRONMENT': 'metadata.environment'
        }
    
    def discover_environment_variables(self) -> Dict[str, str]:
        """Discover environment variables from code files"""
        discovered_vars = {}
        
        # Search for environment variable usage in code
        for code_file in self.project_root.rglob("*.py"):
            if "venv" in str(code_file) or "__pycache__" in str(code_file):
                continue
                
            try:
                with open(code_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Find os.environ.get() patterns
                    env_patterns = [
                        r'os\.environ\.get\([\'"]([^\'\"]+)[\'"](?:,\s*[\'"]([^\'\"]*)[\'"])?\)',
                        r'os\.getenv\([\'"]([^\'\"]+)[\'"](?:,\s*[\'"]([^\'\"]*)[\'"])?\)'
                    ]
                    
                    for pattern in env_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            var_name = match[0]
                            default_value = match[1] if len(match) > 1 else None
                            
                            if var_name not in discovered_vars:
                                # Get current value from environment
                                current_value = os.environ.get(var_name, default_value)
                                if current_value:
                                    discovered_vars[var_name] = current_value
                                    
            except Exception as e:
                print(f"Warning: Could not read {code_file}: {e}")
        
        return discovered_vars
    
    def convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if not value:
            return None
            
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # JSON conversion
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        return value
    
    def set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value in configuration dictionary using dot notation"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def generate_config_from_env_vars(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Generate configuration dictionary from environment variables"""
        config = {}
        
        # Map known environment variables
        for env_var, config_path in self.env_var_mappings.items():
            if env_var in env_vars:
                value = self.convert_value(env_vars[env_var])
                self.set_nested_value(config, config_path, value)
        
        # Add unmapped variables to a special section
        unmapped_vars = {}
        for env_var, value in env_vars.items():
            if env_var not in self.env_var_mappings:
                # Skip common system variables
                if not any(env_var.startswith(prefix) for prefix in [
                    'PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'PWD', 'OLDPWD', 
                    'LANG', 'LC_', 'SSH_', 'DISPLAY', 'TMPDIR', '_'
                ]):
                    unmapped_vars[env_var.lower()] = self.convert_value(value)
        
        if unmapped_vars:
            config['unmapped_environment_variables'] = unmapped_vars
        
        return config
    
    def create_environment_config(self, environment: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create environment-specific configuration"""
        env_config = base_config.copy()
        
        # Update metadata
        if 'metadata' not in env_config:
            env_config['metadata'] = {}
        env_config['metadata']['environment'] = environment
        env_config['metadata']['last_updated'] = '2025-01-15'
        
        # Environment-specific adjustments
        if environment == 'dev':
            # Development optimizations
            if 'performance' in env_config:
                # Reduce resource usage for dev
                if 'lambda' in env_config['performance']:
                    memory_sizes = env_config['performance']['lambda'].get('memory_sizes', {})
                    for func_name in memory_sizes:
                        memory_sizes[func_name] = min(memory_sizes[func_name], 1024)
                
                env_config['performance']['max_concurrent_downloads'] = min(
                    env_config['performance'].get('max_concurrent_downloads', 5), 3
                )
            
            if 'monitoring' in env_config:
                env_config['monitoring']['log_level'] = 'DEBUG'
        
        elif environment == 'prod':
            # Production optimizations
            if 'security' in env_config:
                env_config['security']['vpc_enabled'] = True
                env_config['security']['encryption_enabled'] = True
            
            if 'monitoring' in env_config:
                env_config['monitoring']['enable_xray'] = True
                env_config['monitoring']['enable_monitoring'] = True
        
        return env_config
    
    def write_yaml_config(self, config: Dict[str, Any], file_path: Path) -> None:
        """Write configuration to YAML file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, 
                     allow_unicode=True, width=120, indent=2)
        
        print(f"✅ Created configuration file: {file_path}")
    
    def generate_migration_report(self, discovered_vars: Dict[str, str], 
                                config: Dict[str, Any]) -> str:
        """Generate migration report"""
        report = []
        report.append("# Configuration Migration Report")
        report.append(f"# Generated on: {self.get_current_timestamp()}")
        report.append("")
        
        report.append("## Environment Variables Discovered")
        report.append(f"Total variables found: {len(discovered_vars)}")
        report.append("")
        
        mapped_vars = []
        unmapped_vars = []
        
        for env_var in discovered_vars:
            if env_var in self.env_var_mappings:
                mapped_vars.append(f"  ✅ {env_var} → {self.env_var_mappings[env_var]}")
            else:
                unmapped_vars.append(f"  ⚠️  {env_var} (unmapped)")
        
        if mapped_vars:
            report.append("### Mapped Variables")
            report.extend(mapped_vars)
            report.append("")
        
        if unmapped_vars:
            report.append("### Unmapped Variables")
            report.extend(unmapped_vars)
            report.append("These variables were added to the 'unmapped_environment_variables' section")
            report.append("")
        
        report.append("## Next Steps")
        report.append("")
        report.append("1. Review generated configuration files")
        report.append("2. Update Lambda functions to use enhanced_config_manager")
        report.append("3. Test with new configuration system")
        report.append("4. Remove environment variable dependencies")
        report.append("5. Update deployment scripts")
        
        return "\n".join(report)
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def migrate(self, environments: List[str] = None, 
               dry_run: bool = False) -> None:
        """Perform migration from environment variables to config files"""
        
        if environments is None:
            environments = ['dev', 'staging', 'prod']
        
        print("🚀 Starting Configuration Migration...")
        print(f"Project root: {self.project_root}")
        print(f"Config directory: {self.config_dir}")
        print("")
        
        # Discover environment variables
        print("🔍 Discovering environment variables from code...")
        discovered_vars = self.discover_environment_variables()
        print(f"Found {len(discovered_vars)} environment variables")
        
        # Generate base configuration
        print("⚙️  Generating configuration from environment variables...")
        base_config = self.generate_config_from_env_vars(discovered_vars)
        
        if dry_run:
            print("\n📋 DRY RUN - Configuration preview:")
            print(yaml.dump(base_config, default_flow_style=False, sort_keys=False))
            return
        
        # Create configuration files for each environment
        for env in environments:
            print(f"📝 Creating {env} environment configuration...")
            env_config = self.create_environment_config(env, base_config)
            config_path = self.environments_dir / f"{env}.yaml"
            self.write_yaml_config(env_config, config_path)
        
        # Create default configuration (base template)
        print("📝 Creating default configuration...")
        default_config = base_config.copy()
        if 'metadata' in default_config:
            default_config['metadata']['environment'] = 'default'
        self.write_yaml_config(default_config, self.config_dir / "default.yaml")
        
        # Generate migration report
        report = self.generate_migration_report(discovered_vars, base_config)
        report_path = self.config_dir / "migration_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📊 Migration report: {report_path}")
        print("")
        print("✅ Migration completed successfully!")
        print("")
        print("Next steps:")
        print("1. Review the generated configuration files")
        print("2. Install PyYAML: pip install PyYAML")
        print("3. Update your Lambda functions to use enhanced_config_manager")
        print("4. Test the new configuration system")

def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description="Migrate from environment variables to YAML configuration")
    parser.add_argument("--project-root", help="Project root directory", default=None)
    parser.add_argument("--environments", nargs="+", help="Environments to create", 
                       default=["dev", "staging", "prod"])
    parser.add_argument("--dry-run", action="store_true", help="Preview configuration without creating files")
    
    args = parser.parse_args()
    
    migrator = ConfigMigrator(args.project_root)
    migrator.migrate(args.environments, args.dry_run)

if __name__ == "__main__":
    main()