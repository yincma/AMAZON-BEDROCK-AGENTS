import json
import boto3
import yaml
import os
from datetime import datetime
from typing import Dict, List, Any

# 初始化AWS客户端
s3_client = boto3.client('s3')
apigateway_client = boto3.client('apigateway')

# 环境变量
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
API_GATEWAY_ID = os.environ['API_GATEWAY_ID']
API_GATEWAY_STAGE = os.environ['API_GATEWAY_STAGE']
API_GATEWAY_URL = os.environ['API_GATEWAY_URL']
OPENAPI_SPEC_PATH = os.environ.get('OPENAPI_SPEC_PATH', '/tmp/openapi.yaml')
DOCUMENTATION_VERSION = os.environ.get('DOCUMENTATION_VERSION', '1.0.0')


def lambda_handler(event, context):
    """
    Lambda处理函数 - 生成和更新API文档
    """
    try:
        print(f"开始生成API文档，版本: {DOCUMENTATION_VERSION}")
        
        # 1. 生成OpenAPI规范
        openapi_spec = generate_openapi_spec()
        
        # 2. 上传OpenAPI规范到S3
        upload_openapi_spec(openapi_spec)
        
        # 3. 生成Swagger UI页面
        generate_swagger_ui()
        
        # 4. 生成Postman集合
        postman_collection = generate_postman_collection(openapi_spec)
        upload_postman_collection(postman_collection)
        
        # 5. 生成主文档页面
        generate_documentation_index()
        
        # 6. 生成错误页面
        generate_error_page()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'API文档生成成功',
                'version': DOCUMENTATION_VERSION,
                'timestamp': datetime.utcnow().isoformat(),
                'urls': {
                    'swagger_ui': f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/swagger-ui/index.html",
                    'openapi_spec': f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/openapi.yaml",
                    'postman_collection': f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/postman-collection.json"
                }
            })
        }
        
    except Exception as e:
        print(f"生成API文档时发生错误: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'DOCUMENTATION_GENERATION_FAILED',
                'message': f'文档生成失败: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def generate_openapi_spec() -> Dict[str, Any]:
    """
    从API Gateway生成OpenAPI规范
    """
    try:
        # 从API Gateway获取当前的API规范
        response = apigateway_client.get_export(
            restApiId=API_GATEWAY_ID,
            stageName=API_GATEWAY_STAGE,
            exportType='oas30',
            parameters={
                'extensions': 'integrations,authorizers,documentation'
            }
        )
        
        # 解析响应体
        openapi_spec = json.loads(response['body'].read().decode('utf-8'))
        
        # 增强OpenAPI规范
        enhance_openapi_spec(openapi_spec)
        
        return openapi_spec
        
    except Exception as e:
        print(f"从API Gateway获取OpenAPI规范失败: {str(e)}")
        # 如果无法从API Gateway获取，返回基础规范
        return get_base_openapi_spec()


def enhance_openapi_spec(spec: Dict[str, Any]) -> None:
    """
    增强OpenAPI规范，添加更多详细信息
    """
    # 更新基本信息
    if 'info' not in spec:
        spec['info'] = {}
    
    spec['info'].update({
        'title': 'AI PPT Assistant API',
        'version': DOCUMENTATION_VERSION,
        'description': '''
        AI驱动的PowerPoint演示文稿生成和管理API。
        
        ## 功能特性
        - 基于主题和要求自动生成演示文稿
        - 演示文稿状态跟踪和管理
        - 幻灯片内容修改和定制
        - 模板管理和选择
        - 任务状态监控
        
        ## 认证方式
        使用API密钥进行身份验证。在请求头中包含 `X-API-Key`。
        
        ## 错误处理
        API使用标准HTTP状态码，错误响应包含详细的错误信息。
        ''',
        'contact': {
            'name': 'AI PPT Assistant Support',
            'email': 'support@ai-ppt-assistant.com'
        },
        'license': {
            'name': 'MIT',
            'url': 'https://opensource.org/licenses/MIT'
        }
    })
    
    # 添加服务器信息
    spec['servers'] = [
        {
            'url': API_GATEWAY_URL,
            'description': '生产环境'
        }
    ]
    
    # 添加安全定义
    if 'components' not in spec:
        spec['components'] = {}
    
    spec['components']['securitySchemes'] = {
        'ApiKeyAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key'
        }
    }
    
    # 添加全局安全要求
    spec['security'] = [{'ApiKeyAuth': []}]
    
    # 添加标签
    spec['tags'] = [
        {'name': 'Presentations', 'description': '演示文稿生成和管理'},
        {'name': 'Sessions', 'description': '用户会话管理'},
        {'name': 'Agents', 'description': 'AI代理执行'},
        {'name': 'Tasks', 'description': '任务状态跟踪'},
        {'name': 'Templates', 'description': '演示文稿模板'},
        {'name': 'Health', 'description': '系统健康检查'}
    ]


def get_base_openapi_spec() -> Dict[str, Any]:
    """
    返回基础的OpenAPI规范（备用方案）
    """
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "AI PPT Assistant API",
            "version": DOCUMENTATION_VERSION,
            "description": "AI驱动的PowerPoint演示文稿生成和管理API"
        },
        "servers": [
            {
                "url": API_GATEWAY_URL,
                "description": "生产环境"
            }
        ],
        "paths": {
            "/presentations": {
                "post": {
                    "summary": "生成新演示文稿",
                    "tags": ["Presentations"],
                    "responses": {
                        "202": {
                            "description": "演示文稿生成任务已创建"
                        }
                    }
                },
                "get": {
                    "summary": "列出演示文稿",
                    "tags": ["Presentations"],
                    "responses": {
                        "200": {
                            "description": "演示文稿列表"
                        }
                    }
                }
            }
        }
    }


def upload_openapi_spec(spec: Dict[str, Any]) -> None:
    """
    上传OpenAPI规范到S3
    """
    try:
        # 转换为YAML格式
        yaml_content = yaml.dump(spec, default_flow_style=False, allow_unicode=True)
        
        # 上传到S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='openapi.yaml',
            Body=yaml_content.encode('utf-8'),
            ContentType='application/x-yaml',
            CacheControl='max-age=300'  # 5分钟缓存
        )
        
        # 同时上传JSON格式
        json_content = json.dumps(spec, ensure_ascii=False, indent=2)
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='openapi.json',
            Body=json_content.encode('utf-8'),
            ContentType='application/json',
            CacheControl='max-age=300'
        )
        
        print("OpenAPI规范上传成功")
        
    except Exception as e:
        print(f"上传OpenAPI规范失败: {str(e)}")
        raise


def generate_swagger_ui() -> None:
    """
    生成Swagger UI页面
    """
    try:
        swagger_ui_html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>AI PPT Assistant API 文档</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.0.0/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.0.0/favicon-32x32.png" sizes="32x32" />
  <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.0.0/favicon-16x16.png" sizes="16x16" />
  <style>
    html {{
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }}
    *, *:before, *:after {{
      box-sizing: inherit;
    }}
    body {{
      margin:0;
      background: #fafafa;
    }}
    .swagger-ui .topbar {{
      background-color: #1f2937;
    }}
    .swagger-ui .topbar .topbar-wrapper .link {{
      color: #ffffff;
      font-size: 1.5em;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.0.0/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.0.0/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {{
      const ui = SwaggerUIBundle({{
        url: './openapi.yaml',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout",
        tryItOutEnabled: true,
        requestInterceptor: function(request) {{
          // 添加API密钥到请求头
          if (!request.headers['X-API-Key']) {{
            request.headers['X-API-Key'] = 'YOUR_API_KEY_HERE';
          }}
          return request;
        }},
        responseInterceptor: function(response) {{
          return response;
        }},
        validatorUrl: null,
        displayRequestDuration: true,
        docExpansion: 'list',
        filter: true,
        showExtensions: true,
        showCommonExtensions: true,
        defaultModelsExpandDepth: 2,
        defaultModelExpandDepth: 2,
        supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
        persistAuthorization: true
      }});
    }};
  </script>
</body>
</html>
        '''
        
        # 上传Swagger UI HTML到S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='swagger-ui/index.html',
            Body=swagger_ui_html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='max-age=3600'
        )
        
        print("Swagger UI生成成功")
        
    except Exception as e:
        print(f"生成Swagger UI失败: {str(e)}")
        raise


def generate_postman_collection(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    从OpenAPI规范生成Postman集合
    """
    try:
        collection = {
            "info": {
                "name": "AI PPT Assistant API",
                "description": openapi_spec.get('info', {}).get('description', ''),
                "version": DOCUMENTATION_VERSION,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "apikey",
                "apikey": [
                    {
                        "key": "key",
                        "value": "X-API-Key",
                        "type": "string"
                    },
                    {
                        "key": "value",
                        "value": "{{api_key}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": API_GATEWAY_URL,
                    "type": "string"
                },
                {
                    "key": "api_key",
                    "value": "YOUR_API_KEY_HERE",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # 从OpenAPI规范生成请求项
        paths = openapi_spec.get('paths', {})
        
        for path, methods in paths.items():
            folder = {
                "name": path.split('/')[1].title() if len(path.split('/')) > 1 else "Root",
                "item": []
            }
            
            for method, details in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    request_item = create_postman_request(path, method.upper(), details)
                    folder["item"].append(request_item)
            
            if folder["item"]:
                collection["item"].append(folder)
        
        return collection
        
    except Exception as e:
        print(f"生成Postman集合失败: {str(e)}")
        return {}


def create_postman_request(path: str, method: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建Postman请求项
    """
    request = {
        "name": details.get('summary', f"{method} {path}"),
        "request": {
            "method": method,
            "header": [
                {
                    "key": "Content-Type",
                    "value": "application/json",
                    "type": "text"
                }
            ],
            "url": {
                "raw": "{{base_url}}" + path,
                "host": ["{{base_url}}"],
                "path": [p for p in path.split('/') if p]
            },
            "description": details.get('description', '')
        },
        "response": []
    }
    
    # 添加请求体示例（如果存在）
    if 'requestBody' in details:
        request['request']['body'] = {
            "mode": "raw",
            "raw": json.dumps({
                "example": "请参考API文档中的请求体示例"
            }, indent=2),
            "options": {
                "raw": {
                    "language": "json"
                }
            }
        }
    
    return request


def upload_postman_collection(collection: Dict[str, Any]) -> None:
    """
    上传Postman集合到S3
    """
    try:
        if collection:
            json_content = json.dumps(collection, ensure_ascii=False, indent=2)
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key='postman-collection.json',
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                CacheControl='max-age=3600'
            )
            print("Postman集合上传成功")
        
    except Exception as e:
        print(f"上传Postman集合失败: {str(e)}")
        raise


def generate_documentation_index() -> None:
    """
    生成主文档页面
    """
    try:
        index_html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI PPT Assistant API 文档</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8fafc;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 3rem 2rem;
            margin-bottom: 3rem;
            border-radius: 8px;
        }}
        .header h1 {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }}
        .card {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-decoration: none;
            color: inherit;
            transition: transform 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }}
        .card h3 {{
            color: #4f46e5;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }}
        .card p {{
            color: #6b7280;
            margin-bottom: 1.5rem;
        }}
        .button {{
            display: inline-block;
            background: #4f46e5;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s ease;
        }}
        .button:hover {{
            background: #4338ca;
        }}
        .info-section {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
        }}
        .info-section h2 {{
            color: #1f2937;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e5e7eb;
        }}
        .version-info {{
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid #10b981;
            margin-top: 1rem;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e5e7eb;
        }}
        code {{
            background: #f1f5f9;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI PPT Assistant API</h1>
            <p>智能演示文稿生成和管理平台的API文档</p>
        </div>
        
        <div class="cards">
            <a href="swagger-ui/" class="card">
                <h3>🚀 Swagger UI</h3>
                <p>交互式API文档界面，可以直接测试API端点</p>
                <span class="button">打开 Swagger UI</span>
            </a>
            
            <a href="openapi.yaml" class="card">
                <h3>📋 OpenAPI 规范</h3>
                <p>完整的OpenAPI 3.0规范文件，包含所有API端点的详细定义</p>
                <span class="button">下载 OpenAPI 规范</span>
            </a>
            
            <a href="postman-collection.json" class="card">
                <h3>📮 Postman 集合</h3>
                <p>导入到Postman中的API请求集合，方便API测试和开发</p>
                <span class="button">下载 Postman 集合</span>
            </a>
        </div>
        
        <div class="info-section">
            <h2>快速开始</h2>
            <p>要开始使用AI PPT Assistant API，请按照以下步骤操作：</p>
            <ol style="margin-left: 2rem; margin-top: 1rem;">
                <li>获取API密钥（联系支持团队）</li>
                <li>在请求头中包含 <code>X-API-Key</code> 进行身份验证</li>
                <li>使用 <code>POST /presentations</code> 端点创建新的演示文稿</li>
                <li>通过 <code>GET /presentations/{{id}}</code> 跟踪生成状态</li>
                <li>演示文稿完成后，使用 <code>GET /presentations/{{id}}/download</code> 下载文件</li>
            </ol>
            
            <div class="version-info">
                <strong>版本信息:</strong> {DOCUMENTATION_VERSION}<br>
                <strong>生成时间:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                <strong>API基础URL:</strong> <code>{API_GATEWAY_URL}</code>
            </div>
        </div>
        
        <div class="info-section">
            <h2>主要功能</h2>
            <ul style="margin-left: 2rem;">
                <li><strong>智能生成:</strong> 基于主题和要求自动生成专业演示文稿</li>
                <li><strong>状态跟踪:</strong> 实时跟踪演示文稿生成进度</li>
                <li><strong>内容修改:</strong> 支持对已生成的幻灯片进行修改和调整</li>
                <li><strong>模板选择:</strong> 提供多种专业模板供选择</li>
                <li><strong>会话管理:</strong> 支持用户会话和历史记录管理</li>
                <li><strong>多语言支持:</strong> 支持中文、英文等多种语言</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>&copy; 2024 AI PPT Assistant. 所有权利保留。</p>
            <p>如有问题或建议，请联系 <a href="mailto:support@ai-ppt-assistant.com">support@ai-ppt-assistant.com</a></p>
        </div>
    </div>
</body>
</html>
        '''
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='index.html',
            Body=index_html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='max-age=3600'
        )
        
        print("主文档页面生成成功")
        
    except Exception as e:
        print(f"生成主文档页面失败: {str(e)}")
        raise


def generate_error_page() -> None:
    """
    生成错误页面
    """
    try:
        error_html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>页面未找到 - AI PPT Assistant API</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f8fafc;
            color: #1f2937;
        }
        .error-container {
            text-align: center;
            max-width: 500px;
            padding: 2rem;
        }
        .error-code {
            font-size: 6rem;
            font-weight: bold;
            color: #ef4444;
            margin-bottom: 1rem;
        }
        .error-message {
            font-size: 1.5rem;
            margin-bottom: 2rem;
            color: #6b7280;
        }
        .back-button {
            display: inline-block;
            background: #4f46e5;
            color: white;
            padding: 1rem 2rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s ease;
        }
        .back-button:hover {
            background: #4338ca;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">404</div>
        <div class="error-message">页面未找到</div>
        <p>抱歉，您访问的页面不存在。</p>
        <a href="/" class="back-button">返回首页</a>
    </div>
</body>
</html>
        '''
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='error.html',
            Body=error_html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='max-age=3600'
        )
        
        print("错误页面生成成功")
        
    except Exception as e:
        print(f"生成错误页面失败: {str(e)}")
        raise