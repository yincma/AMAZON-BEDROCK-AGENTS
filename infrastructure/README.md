# AI PPT Assistant Infrastructure

## Phase 1: Minimal MVP Infrastructure

### 资源清单
- **S3 Bucket**: 存储生成的PPT文件
- **Lambda Functions**:
  - generate_ppt: 处理PPT生成请求
  - status_check: 检查生成状态
  - download_ppt: 提供下载链接
- **API Gateway**: RESTful API端点
- **IAM Roles**: Lambda执行权限

### 部署步骤

1. **初始化Terraform**
```bash
terraform init
```

2. **配置变量**
```bash
cp terraform.tfvars.example terraform.tfvars
# 编辑terraform.tfvars设置你的AWS区域和环境
```

3. **验证配置**
```bash
terraform validate
terraform plan
```

4. **部署基础设施**
```bash
terraform apply
```

### API端点

部署后将获得以下API端点：

- **生成PPT**: `POST /generate`
  ```json
  {
    "topic": "Your presentation topic"
  }
  ```

- **检查状态**: `GET /status/{presentation_id}`

- **下载PPT**: `GET /download/{presentation_id}`

### 环境变量

Lambda函数使用以下环境变量：
- `S3_BUCKET`: PPT存储桶名称
- `ENVIRONMENT`: 部署环境（dev/staging/prod）
- `AWS_REGION`: AWS区域

### 清理资源

```bash
terraform destroy
```

### 注意事项

1. 当前Lambda函数为占位代码，仅提供基本响应
2. 实际的PPT生成逻辑将在后续阶段实现
3. 确保AWS账户有足够权限创建这些资源
4. S3桶名称包含账户ID以确保全局唯一性