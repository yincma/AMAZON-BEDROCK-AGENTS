# Configuration Migration Report
# Generated on: 2025-09-05 16:11:15

## Environment Variables Discovered
Total variables found: 30

### Mapped Variables
  ✅ AWS_REGION → aws.region
  ✅ ENVIRONMENT → metadata.environment
  ✅ S3_BUCKET → services.s3.bucket
  ✅ NOVA_MODEL_ID → services.bedrock.nova_model_id
  ✅ MAX_IMAGE_SIZE_MB → performance.max_image_size_mb
  ✅ CHECKPOINTS_TABLE → services.dynamodb.checkpoints_table
  ✅ CHECKPOINT_TTL_HOURS → performance.checkpoint_ttl_hours
  ✅ MAX_CHECKPOINTS_PER_TASK → performance.max_checkpoints_per_task
  ✅ TEMPLATES_BUCKET → services.s3.templates_bucket
  ✅ SESSIONS_TABLE → services.dynamodb.table
  ✅ CACHE_TTL_SECONDS → performance.cache_ttl_seconds
  ✅ MAX_TEMPLATE_SIZE_MB → performance.max_template_size_mb
  ✅ DYNAMODB_TABLE → services.dynamodb.table
  ✅ DOWNLOAD_EXPIRY_SECONDS → monitoring.download_expiry_seconds
  ✅ BEDROCK_MODEL_ID → services.bedrock.model_id
  ✅ MAX_CONCURRENT_SLIDES → performance.max_concurrent_slides
  ✅ BATCH_SIZE → performance.batch_size
  ✅ MAX_SEARCH_RESULTS → performance.max_search_results
  ✅ ENABLE_REKOGNITION → security.enable_rekognition
  ✅ MAX_CONCURRENT_DOWNLOADS → performance.max_concurrent_downloads
  ✅ IMAGE_DOWNLOAD_TIMEOUT → performance.image_download_timeout
  ✅ IMAGE_MODEL_ID → services.bedrock.nova_model_id
  ✅ MAX_CONCURRENT_IMAGES → performance.max_concurrent_images
  ✅ DEFAULT_IMAGE_SIZE → performance.default_image_size
  ✅ DEFAULT_SECONDS_PER_SLIDE → performance.default_seconds_per_slide
  ✅ MAX_SLIDES → performance.max_slides
  ✅ LOG_LEVEL → monitoring.log_level
  ✅ VPC_ENABLED → security.vpc_enabled

### Unmapped Variables
  ⚠️  USE_CONFIG_FILES (unmapped)
  ⚠️  CONFIG_MIGRATION_MODE (unmapped)
These variables were added to the 'unmapped_environment_variables' section

## Next Steps

1. Review generated configuration files
2. Update Lambda functions to use enhanced_config_manager
3. Test with new configuration system
4. Remove environment variable dependencies
5. Update deployment scripts