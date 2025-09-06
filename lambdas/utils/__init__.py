"""
Utilities Package for AI PPT Assistant
Provides centralized access to all shared utilities and eliminates code duplication
"""

# API Utilities
from .api_utils import create_response  # Legacy compatibility

# AWS Service Utilities

# Checkpoint Management

# Configuration Management (Enhanced)

# Image Processing

# Timeout Management

# Version information
__version__ = "1.0.0"
__author__ = "AI PPT Assistant"
__description__ = "Shared utilities for AI PPT Assistant Lambda functions"

# Module metadata
MODULES = {
    "timeout_manager": "Lambda timeout monitoring and control",
    "enhanced_config_manager": "Enhanced YAML-based configuration management with backward compatibility",
    "api_utils": "API response and request handling utilities",
    "aws_service_utils": "AWS service interaction utilities",
    "image_processor": "Image processing and manipulation",
    "checkpoint_manager": "Task checkpoint and recovery management",
}


def get_module_info() -> dict:
    """Get information about available utility modules"""
    return {"version": __version__, "modules": MODULES, "total_modules": len(MODULES)}
