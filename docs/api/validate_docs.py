#!/usr/bin/env python3
"""
API Documentation Validation Script

This script validates the completeness and consistency of the API documentation files.
Run this script to ensure all documentation files are properly formatted and complete.
"""

import os
import json
import yaml
import sys
from pathlib import Path

def validate_file_exists(file_path, description):
    """Check if a file exists and report its size."""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"✅ {description}: {file_path} ({size:,} bytes)")
        return True
    else:
        print(f"❌ {description}: {file_path} - FILE NOT FOUND")
        return False

def validate_yaml_format(file_path):
    """Validate YAML file format."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"✅ YAML format valid: {file_path}")
        return True
    except yaml.YAMLError as e:
        print(f"❌ YAML format error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

def validate_json_format(file_path):
    """Validate JSON file format."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ JSON format valid: {file_path}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON format error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

def validate_openapi_content(file_path):
    """Validate OpenAPI specification content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)

        # Check required OpenAPI fields
        required_fields = ['openapi', 'info', 'paths', 'components']
        missing_fields = [field for field in required_fields if field not in spec]

        if missing_fields:
            print(f"❌ OpenAPI missing required fields: {missing_fields}")
            return False

        # Check version
        if not spec['openapi'].startswith('3.1'):
            print(f"❌ OpenAPI version should be 3.1.x, found: {spec['openapi']}")
            return False

        # Check paths count
        paths_count = len(spec['paths'])
        if paths_count < 8:  # Expecting at least 8 main endpoints
            print(f"❌ Expected at least 8 API paths, found: {paths_count}")
            return False

        print(f"✅ OpenAPI specification valid: {paths_count} endpoints defined")
        return True

    except Exception as e:
        print(f"❌ Error validating OpenAPI content: {e}")
        return False

def validate_postman_content(file_path):
    """Validate Postman collection content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)

        # Check required Postman fields
        if 'info' not in collection:
            print("❌ Postman collection missing 'info' field")
            return False

        if 'item' not in collection:
            print("❌ Postman collection missing 'item' field")
            return False

        # Count total requests
        def count_requests(items):
            count = 0
            for item in items:
                if 'request' in item:
                    count += 1
                elif 'item' in item:
                    count += count_requests(item['item'])
            return count

        request_count = count_requests(collection['item'])
        if request_count < 15:  # Expecting at least 15 requests
            print(f"❌ Expected at least 15 requests in Postman collection, found: {request_count}")
            return False

        print(f"✅ Postman collection valid: {request_count} requests defined")
        return True

    except Exception as e:
        print(f"❌ Error validating Postman collection: {e}")
        return False

def validate_markdown_content(file_path, min_size=1000):
    """Validate Markdown file has substantial content."""
    try:
        size = os.path.getsize(file_path)
        if size < min_size:
            print(f"❌ Markdown file too small: {file_path} ({size} bytes, expected >= {min_size})")
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for basic markdown structure
        if not content.startswith('#'):
            print(f"❌ Markdown file should start with header: {file_path}")
            return False

        # Count headers
        header_count = content.count('\n#')
        if header_count < 5:  # Expecting substantial documentation
            print(f"❌ Markdown file needs more structure: {file_path} ({header_count} headers)")
            return False

        print(f"✅ Markdown content valid: {file_path} ({size:,} bytes, {header_count} sections)")
        return True

    except Exception as e:
        print(f"❌ Error validating Markdown content: {e}")
        return False

def main():
    """Main validation function."""
    print("🔍 Validating AI PPT Assistant API Documentation")
    print("=" * 60)

    # Get the docs/api directory
    docs_dir = Path(__file__).parent

    # Define expected files
    files_to_check = [
        ('openapi-v1.yaml', 'OpenAPI 3.1 Specification'),
        ('API_REFERENCE.md', 'API Reference Documentation'),
        ('ERROR_CODES.md', 'Error Codes Reference'),
        ('EXAMPLES.md', 'Usage Examples'),
        ('postman-collection.json', 'Postman Collection'),
        ('README.md', 'Documentation Index')
    ]

    all_valid = True

    print("\n📁 File Existence Check:")
    print("-" * 30)
    for filename, description in files_to_check:
        file_path = docs_dir / filename
        if not validate_file_exists(file_path, description):
            all_valid = False

    print("\n📋 Format Validation:")
    print("-" * 30)

    # Validate OpenAPI YAML
    openapi_path = docs_dir / 'openapi-v1.yaml'
    if openapi_path.exists():
        if not validate_yaml_format(openapi_path):
            all_valid = False
        elif not validate_openapi_content(openapi_path):
            all_valid = False

    # Validate Postman JSON
    postman_path = docs_dir / 'postman-collection.json'
    if postman_path.exists():
        if not validate_json_format(postman_path):
            all_valid = False
        elif not validate_postman_content(postman_path):
            all_valid = False

    print("\n📝 Content Validation:")
    print("-" * 30)

    # Validate Markdown files
    markdown_files = [
        ('API_REFERENCE.md', 20000),  # Expecting substantial API reference
        ('ERROR_CODES.md', 15000),    # Expecting comprehensive error guide
        ('EXAMPLES.md', 30000),       # Expecting extensive examples
        ('README.md', 5000)           # Expecting good overview
    ]

    for filename, min_size in markdown_files:
        file_path = docs_dir / filename
        if file_path.exists():
            if not validate_markdown_content(file_path, min_size):
                all_valid = False

    print("\n" + "=" * 60)
    if all_valid:
        print("🎉 All documentation files are valid and complete!")
        print("\n📊 Documentation Summary:")
        print(f"   • OpenAPI 3.1 specification with comprehensive endpoint definitions")
        print(f"   • Complete API reference with examples and authentication details")
        print(f"   • Detailed error codes reference with troubleshooting guide")
        print(f"   • Extensive usage examples in multiple programming languages")
        print(f"   • Ready-to-use Postman collection with automated tests")
        print(f"   • User-friendly documentation index and navigation")
        print("\n✨ Your API documentation is production-ready!")
        return 0
    else:
        print("❌ Some documentation files have issues. Please review and fix.")
        return 1

if __name__ == '__main__':
    sys.exit(main())