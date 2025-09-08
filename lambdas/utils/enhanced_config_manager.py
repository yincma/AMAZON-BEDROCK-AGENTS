"""
Enhanced Configuration Manager - AI PPT Assistant
Supports both YAML configuration files and environment variables
Provides seamless migration path from env vars to config files
"""

import os
import re
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("PyYAML not installed. Run: pip install PyYAML")

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = Logger(__name__)


class ConfigSource(Enum):
    """Configuration source types"""

    CONFIG_FILE = "config_file"
    ENVIRONMENT = "environment"
    SSM = "ssm"
    SECRETS_MANAGER = "secrets_manager"
    DEFAULT = "default"


@dataclass
class EnhancedAWSConfig:
    """Enhanced AWS configuration"""

    region: str = "us-east-1"
    profile: Optional[str] = None
    role_arn: Optional[str] = None


@dataclass
class S3Config:
    """S3 service configuration"""

    bucket: str = ""
    templates_bucket: str = ""
    lifecycle: Dict[str, int] = field(
        default_factory=lambda: {
            "transition_to_ia_days": 30,
            "transition_to_glacier_days": 90,
            "expiration_days": 365,
        }
    )


@dataclass
class DynamoDBConfig:
    """DynamoDB service configuration"""

    table: str = ""
    checkpoints_table: str = ""
    billing_mode: str = "PAY_PER_REQUEST"
    ttl_days: int = 30


@dataclass
class BedrockConfig:
    """Bedrock AI service configuration"""

    model_id: str  # Claude model for content generation - no default, must be configured
    orchestrator_model_id: str  # Claude model for orchestration - no default, must be configured  
    nova_model_id: str  # Nova model for image generation - no default, must be configured
    orchestrator_agent_id: Optional[str] = None
    content_agent_id: Optional[str] = None
    visual_agent_id: Optional[str] = None
    compiler_agent_id: Optional[str] = None


@dataclass
class LambdaConfig:
    """Lambda function configuration"""

    memory_sizes: Dict[str, int] = field(
        default_factory=lambda: {
            "create_outline": 1024,
            "generate_content": 2048,
            "generate_image": 1024,
            "compile_pptx": 2048,
            "api_endpoints": 512,
        }
    )
    timeouts: Dict[str, int] = field(
        default_factory=lambda: {
            "create_outline": 60,
            "generate_content": 120,
            "generate_image": 90,
            "compile_pptx": 180,
            "api_endpoints": 30,
        }
    )
    reserved_concurrency: Dict[str, int] = field(
        default_factory=lambda: {
            "create_outline": 2,
            "generate_content": 5,
            "generate_image": 3,
            "compile_pptx": 2,
            "api_endpoints": 5,
        }
    )


@dataclass
class EnhancedPerformanceConfig:
    """Enhanced performance configuration"""

    lambda_config: LambdaConfig = field(default_factory=LambdaConfig)
    max_concurrent_downloads: int = 5
    max_concurrent_images: int = 3
    max_concurrent_slides: int = 5
    image_download_timeout: int = 30
    cache_ttl_seconds: int = 3600
    max_slides: int = 20
    min_slides: int = 5
    max_image_size_mb: int = 10
    batch_size: int = 3


@dataclass
class EnhancedSecurityConfig:
    """Enhanced security configuration"""

    vpc_enabled: bool = False
    vpc_id: Optional[str] = None
    encryption_enabled: bool = True
    api_rate_limit: int = 100
    enable_rekognition: bool = True
    external_apis: Dict[str, Optional[str]] = field(
        default_factory=lambda: {
            "pexels_api_key": None,
            "pixabay_api_key": None,
            "unsplash_access_key": None,
        }
    )


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""

    log_level: str = "INFO"
    enable_xray: bool = False
    log_retention_days: int = 30
    enable_monitoring: bool = True
    alert_email: Optional[str] = None


@dataclass
class FeatureFlagsConfig:
    """Feature flags configuration"""

    enable_speaker_notes: bool = True
    enable_image_generation: bool = True
    enable_image_search: bool = True
    enable_batch_processing: bool = True
    enable_caching: bool = True


@dataclass
class ProjectMetadata:
    """Project metadata"""

    project_name: str = "ai-ppt-assistant"
    environment: str = "dev"
    version: str = "1.0.0"
    maintainer: str = "ai-team"
    last_updated: Optional[str] = None


class EnhancedConfigManager:
    """
    Enhanced Configuration Manager supporting YAML files and environment variables

    Features:
    - YAML configuration file support with environment-specific overrides
    - Backward compatibility with environment variables
    - SSM Parameter Store and Secrets Manager integration
    - Variable interpolation (${ENV:VAR}, ${SSM:path}, ${SECRET:name})
    - Configuration validation and type conversion
    - Caching for performance
    """

    def __init__(self, environment: str = "dev", config_dir: Optional[str] = None):
        self.environment = environment
        self.config_dir = config_dir or self._find_config_directory()

        # AWS clients for remote config sources
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        self.ssm_client = boto3.client("ssm", region_name=self.aws_region)
        self.secrets_client = boto3.client(
            "secretsmanager", region_name=self.aws_region
        )

        # Configuration cache
        self._cache: Dict[str, Any] = {}
        self._config_data: Dict[str, Any] = {}

        # Load configuration
        self._load_configuration()

    def _find_config_directory(self) -> str:
        """Find configuration directory relative to the project root"""
        current_path = Path(__file__).parent.parent.parent
        config_path = current_path / "config"

        if config_path.exists():
            return str(config_path)

        # In Lambda environment, don't try to create directories
        # Just return the path - it will be handled gracefully later
        return str(config_path)

    def _load_configuration(self) -> None:
        """Load configuration from YAML files with environment override"""
        if not YAML_AVAILABLE:
            logger.warning(
                "YAML support not available, falling back to environment variables only"
            )
            return

        config_data = {}

        # Load default configuration
        default_config_path = Path(self.config_dir) / "default.yaml"
        if default_config_path.exists():
            with open(default_config_path, "r", encoding="utf-8") as f:
                default_config = yaml.safe_load(f)
                if default_config:
                    config_data = self._deep_merge(config_data, default_config)
                    logger.info(
                        f"Loaded default configuration from {default_config_path}"
                    )

        # Load environment-specific configuration
        env_config_path = (
            Path(self.config_dir) / "environments" / f"{self.environment}.yaml"
        )
        if env_config_path.exists():
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f)
                if env_config:
                    config_data = self._deep_merge(config_data, env_config)
                    logger.info(
                        f"Loaded environment configuration from {env_config_path}"
                    )

        # Interpolate variables (${ENV:VAR}, ${SSM:path}, ${SECRET:name})
        self._config_data = self._interpolate_variables(config_data)
        logger.info(f"Configuration loaded for environment: {self.environment}")

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence"""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _interpolate_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate variables in configuration values"""
        if isinstance(config, dict):
            return {k: self._interpolate_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._interpolate_variables(item) for item in config]
        elif isinstance(config, str):
            return self._interpolate_string(config)
        else:
            return config

    def _interpolate_string(self, value: str) -> str:
        """Interpolate variables in a string value"""
        # Environment variable pattern: ${ENV:VARIABLE_NAME}
        env_pattern = r"\$\{ENV:([^}]+)\}"
        value = re.sub(env_pattern, lambda m: os.environ.get(m.group(1), ""), value)

        # SSM parameter pattern: ${SSM:/path/to/parameter}
        ssm_pattern = r"\$\{SSM:([^}]+)\}"
        for match in re.finditer(ssm_pattern, value):
            ssm_value = self._get_ssm_parameter(match.group(1))
            if ssm_value:
                value = value.replace(match.group(0), ssm_value)

        # Secrets Manager pattern: ${SECRET:secret-name}
        secret_pattern = r"\$\{SECRET:([^}]+)\}"
        for match in re.finditer(secret_pattern, value):
            secret_value = self._get_secret(match.group(1))
            if secret_value:
                value = value.replace(match.group(0), secret_value)

        return value

    def _get_ssm_parameter(self, parameter_path: str) -> Optional[str]:
        """Get parameter from SSM Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_path, WithDecryption=True
            )
            return response["Parameter"]["Value"]
        except Exception as e:
            logger.warning(f"Could not retrieve SSM parameter {parameter_path}: {e}")
            return None

    def _get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return response["SecretString"]
        except Exception as e:
            logger.warning(f"Could not retrieve secret {secret_name}: {e}")
            return None

    def get_value(
        self, path: str, default: Any = None, fallback_env_var: Optional[str] = None
    ) -> Any:
        """
        Get configuration value by dot-notation path

        Args:
            path: Dot-notation path (e.g., 'aws.region', 'services.s3.bucket')
            default: Default value if not found
            fallback_env_var: Environment variable to check if config value not found

        Returns:
            Configuration value or default
        """
        # Try config file first
        keys = path.split(".")
        value = self._config_data

        try:
            for key in keys:
                value = value[key]

            if value is not None:
                return value
        except (KeyError, TypeError):
            pass

        # Fallback to environment variable
        if fallback_env_var:
            env_value = os.environ.get(fallback_env_var)
            if env_value is not None:
                return env_value

        return default

    def get_aws_config(self) -> EnhancedAWSConfig:
        """Get AWS configuration"""
        if "aws_config" not in self._cache:
            self._cache["aws_config"] = EnhancedAWSConfig(
                region=self.get_value("aws.region", fallback_env_var="AWS_REGION")
                or "us-east-1",
                profile=self.get_value("aws.profile", fallback_env_var="AWS_PROFILE"),
                role_arn=self.get_value("aws.role_arn"),
            )
        return self._cache["aws_config"]

    def get_s3_config(self) -> S3Config:
        """Get S3 configuration"""
        if "s3_config" not in self._cache:
            self._cache["s3_config"] = S3Config(
                bucket=self.get_value(
                    "services.s3.bucket", fallback_env_var="S3_BUCKET"
                )
                or "",
                templates_bucket=self.get_value(
                    "services.s3.templates_bucket", fallback_env_var="TEMPLATES_BUCKET"
                )
                or "",
                lifecycle=self.get_value("services.s3.lifecycle", {}),
            )
        return self._cache["s3_config"]

    def get_dynamodb_config(self) -> DynamoDBConfig:
        """Get DynamoDB configuration"""
        if "dynamodb_config" not in self._cache:
            self._cache["dynamodb_config"] = DynamoDBConfig(
                table=self.get_value(
                    "services.dynamodb.table", fallback_env_var="DYNAMODB_TABLE"
                )
                or "",
                checkpoints_table=self.get_value(
                    "services.dynamodb.checkpoints_table",
                    fallback_env_var="CHECKPOINTS_TABLE",
                )
                or "",
                billing_mode=self.get_value(
                    "services.dynamodb.billing_mode", "PAY_PER_REQUEST"
                ),
                ttl_days=self.get_value("services.dynamodb.ttl_days", 30),
            )
        return self._cache["dynamodb_config"]

    def get_bedrock_config(self) -> BedrockConfig:
        """Get Bedrock configuration"""
        if "bedrock_config" not in self._cache:
            # Get model IDs from environment or config, with no hardcoded fallbacks
            model_id = self.get_value(
                "services.bedrock.model_id", fallback_env_var="BEDROCK_MODEL_ID"
            )
            orchestrator_model_id = self.get_value(
                "services.bedrock.orchestrator_model_id", fallback_env_var="BEDROCK_ORCHESTRATOR_MODEL_ID"
            )
            nova_model_id = self.get_value(
                "services.bedrock.nova_model_id", fallback_env_var="NOVA_MODEL_ID"
            )
            
            # Validate required configuration
            if not model_id:
                raise ValueError(
                    "BEDROCK_MODEL_ID must be configured via environment variable or config file. "
                    "Example: us.anthropic.claude-opus-4-20250514-v1:0"
                )
            if not orchestrator_model_id:
                raise ValueError(
                    "BEDROCK_ORCHESTRATOR_MODEL_ID must be configured. "
                    "Example: us.anthropic.claude-opus-4-1-20250805-v1:0"
                )
            if not nova_model_id:
                raise ValueError(
                    "NOVA_MODEL_ID must be configured. "
                    "Example: amazon.nova-canvas-v1:0"
                )

            self._cache["bedrock_config"] = BedrockConfig(
                model_id=model_id,
                orchestrator_model_id=orchestrator_model_id,
                nova_model_id=nova_model_id,
                orchestrator_agent_id=self.get_value(
                    "services.bedrock.orchestrator_agent_id",
                    fallback_env_var="ORCHESTRATOR_AGENT_ID",
                ),
                content_agent_id=self.get_value(
                    "services.bedrock.content_agent_id",
                    fallback_env_var="CONTENT_AGENT_ID",
                ),
                visual_agent_id=self.get_value(
                    "services.bedrock.visual_agent_id",
                    fallback_env_var="VISUAL_AGENT_ID",
                ),
                compiler_agent_id=self.get_value(
                    "services.bedrock.compiler_agent_id",
                    fallback_env_var="COMPILER_AGENT_ID",
                ),
            )
        return self._cache["bedrock_config"]

    def get_performance_config(self) -> EnhancedPerformanceConfig:
        """Get performance configuration"""
        if "performance_config" not in self._cache:
            lambda_config = LambdaConfig(
                memory_sizes=self.get_value("performance.lambda.memory_sizes", {}),
                timeouts=self.get_value("performance.lambda.timeouts", {}),
                reserved_concurrency=self.get_value(
                    "performance.lambda.reserved_concurrency", {}
                ),
            )

            self._cache["performance_config"] = EnhancedPerformanceConfig(
                lambda_config=lambda_config,
                max_concurrent_downloads=self.get_value(
                    "performance.max_concurrent_downloads",
                    fallback_env_var="MAX_CONCURRENT_DOWNLOADS",
                )
                or 5,
                max_concurrent_images=self.get_value(
                    "performance.max_concurrent_images",
                    fallback_env_var="MAX_CONCURRENT_IMAGES",
                )
                or 3,
                max_concurrent_slides=self.get_value(
                    "performance.max_concurrent_slides",
                    fallback_env_var="MAX_CONCURRENT_SLIDES",
                )
                or 5,
                image_download_timeout=self.get_value(
                    "performance.image_download_timeout",
                    fallback_env_var="IMAGE_DOWNLOAD_TIMEOUT",
                )
                or 30,
                cache_ttl_seconds=self.get_value(
                    "performance.cache_ttl_seconds",
                    fallback_env_var="CACHE_TTL_SECONDS",
                )
                or 3600,
                max_slides=self.get_value(
                    "performance.max_slides", fallback_env_var="MAX_SLIDES"
                )
                or 20,
                min_slides=self.get_value(
                    "performance.min_slides", fallback_env_var="MIN_SLIDES"
                )
                or 5,
                max_image_size_mb=self.get_value(
                    "performance.max_image_size_mb",
                    fallback_env_var="MAX_IMAGE_SIZE_MB",
                )
                or 10,
                batch_size=self.get_value(
                    "performance.batch_size", fallback_env_var="BATCH_SIZE"
                )
                or 3,
            )
        return self._cache["performance_config"]

    def get_security_config(self) -> EnhancedSecurityConfig:
        """Get security configuration"""
        if "security_config" not in self._cache:
            self._cache["security_config"] = EnhancedSecurityConfig(
                vpc_enabled=self.get_value(
                    "security.vpc_enabled", fallback_env_var="VPC_ENABLED"
                )
                or False,
                vpc_id=self.get_value("security.vpc_id", fallback_env_var="VPC_ID"),
                encryption_enabled=self.get_value("security.encryption_enabled", True),
                api_rate_limit=self.get_value(
                    "security.api_rate_limit", fallback_env_var="API_RATE_LIMIT"
                )
                or 100,
                enable_rekognition=self.get_value(
                    "security.enable_rekognition", fallback_env_var="ENABLE_REKOGNITION"
                )
                or True,
                external_apis=self.get_value("security.external_apis", {}),
            )
        return self._cache["security_config"]

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        if "monitoring_config" not in self._cache:
            self._cache["monitoring_config"] = MonitoringConfig(
                log_level=self.get_value(
                    "monitoring.log_level", fallback_env_var="LOG_LEVEL"
                )
                or "INFO",
                enable_xray=self.get_value("monitoring.enable_xray", False),
                log_retention_days=self.get_value("monitoring.log_retention_days", 30),
                enable_monitoring=self.get_value("monitoring.enable_monitoring", True),
                alert_email=self.get_value(
                    "monitoring.alert_email", fallback_env_var="ALERT_EMAIL"
                ),
            )
        return self._cache["monitoring_config"]

    def get_feature_flags(self) -> FeatureFlagsConfig:
        """Get feature flags configuration"""
        if "feature_flags" not in self._cache:
            self._cache["feature_flags"] = FeatureFlagsConfig(
                enable_speaker_notes=self.get_value(
                    "features.enable_speaker_notes", True
                ),
                enable_image_generation=self.get_value(
                    "features.enable_image_generation", True
                ),
                enable_image_search=self.get_value(
                    "features.enable_image_search", True
                ),
                enable_batch_processing=self.get_value(
                    "features.enable_batch_processing", True
                ),
                enable_caching=self.get_value("features.enable_caching", True),
            )
        return self._cache["feature_flags"]

    def get_project_metadata(self) -> ProjectMetadata:
        """Get project metadata"""
        if "project_metadata" not in self._cache:
            self._cache["project_metadata"] = ProjectMetadata(
                project_name=self.get_value(
                    "metadata.project_name", fallback_env_var="PROJECT_NAME"
                )
                or "ai-ppt-assistant",
                environment=self.environment,
                version=self.get_value("metadata.version", "1.0.0"),
                maintainer=self.get_value("metadata.maintainer", "ai-team"),
                last_updated=self.get_value("metadata.last_updated"),
            )
        return self._cache["project_metadata"]

    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary"""
        return {
            "aws": asdict(self.get_aws_config()),
            "s3": asdict(self.get_s3_config()),
            "dynamodb": asdict(self.get_dynamodb_config()),
            "bedrock": asdict(self.get_bedrock_config()),
            "performance": asdict(self.get_performance_config()),
            "security": asdict(self.get_security_config()),
            "monitoring": asdict(self.get_monitoring_config()),
            "features": asdict(self.get_feature_flags()),
            "metadata": asdict(self.get_project_metadata()),
        }

    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate all configuration and return validation report"""
        report = {"valid": [], "warnings": [], "errors": []}

        # Validate required configurations
        aws_config = self.get_aws_config()
        s3_config = self.get_s3_config()
        dynamodb_config = self.get_dynamodb_config()
        bedrock_config = self.get_bedrock_config()

        # AWS Region validation
        if aws_config.region:
            report["valid"].append(f"AWS Region: {aws_config.region}")
        else:
            report["errors"].append("AWS Region is required")

        # S3 bucket validation
        if s3_config.bucket:
            report["valid"].append(f"S3 Bucket: {s3_config.bucket}")
        else:
            report["errors"].append("S3 bucket name is required")

        # DynamoDB table validation
        if dynamodb_config.table:
            report["valid"].append(f"DynamoDB Table: {dynamodb_config.table}")
        else:
            report["errors"].append("DynamoDB table name is required")

        # Bedrock model validation
        if bedrock_config.model_id:
            report["valid"].append(f"Bedrock Model: {bedrock_config.model_id}")
        else:
            report["warnings"].append("Bedrock model ID not specified, using default")

        return report

    def reload_configuration(self) -> None:
        """Reload configuration from files"""
        self._cache.clear()
        self._config_data.clear()
        self._load_configuration()
        logger.info("Configuration reloaded")


# Global enhanced configuration manager instance
_enhanced_config_manager: Optional[EnhancedConfigManager] = None


def get_enhanced_config_manager(
    environment: Optional[str] = None, config_dir: Optional[str] = None
) -> EnhancedConfigManager:
    """Get global enhanced configuration manager instance"""
    global _enhanced_config_manager

    if _enhanced_config_manager is None or environment is not None:
        env = environment or os.environ.get("ENVIRONMENT", "dev")
        _enhanced_config_manager = EnhancedConfigManager(env, config_dir)

    return _enhanced_config_manager


# Convenience functions for backward compatibility


def get_enhanced_aws_config() -> EnhancedAWSConfig:
    """Get AWS configuration"""
    return get_enhanced_config_manager().get_aws_config()


def get_enhanced_service_config() -> Dict[str, Any]:
    """Get all service configurations"""
    manager = get_enhanced_config_manager()
    return {
        "s3": manager.get_s3_config(),
        "dynamodb": manager.get_dynamodb_config(),
        "bedrock": manager.get_bedrock_config(),
    }


def get_enhanced_performance_config() -> EnhancedPerformanceConfig:
    """Get performance configuration"""
    return get_enhanced_config_manager().get_performance_config()


def log_enhanced_configuration_summary(
    logger_instance: Optional[Logger] = None,
) -> None:
    """Log enhanced configuration summary for debugging"""
    log = logger_instance or logger
    all_config = get_enhanced_config_manager().get_all_config()
    log.info("Enhanced Configuration Summary", extra={"config_summary": all_config})
