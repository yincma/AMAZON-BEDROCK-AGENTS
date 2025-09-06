快速开始
========

本指南将帮助您在10分钟内完成AI PPT Assistant的基本设置和使用。

第一步：部署基础设施
------------------

1. 初始化Terraform
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   make tf-init

2. 部署AWS基础设施
~~~~~~~~~~~~~~~~

.. code-block:: bash

   make deploy

这将创建所有必要的AWS资源，包括：

* Lambda函数
* DynamoDB表
* S3存储桶
* API Gateway
* Bedrock Agent配置

第二步：验证部署
--------------

运行部署验证脚本：

.. code-block:: bash

   python verify_deployment.py

确保所有组件都正常工作。

第三步：创建第一个演示文稿
-----------------------

使用API创建演示文稿：

.. code-block:: bash

   curl -X POST https://your-api-gateway-url/presentations/generate \
     -H "Content-Type: application/json" \
     -d '{
       "title": "我的第一个AI演示文稿",
       "topic": "人工智能的未来发展趋势",
       "duration": 20,
       "slide_count": 15,
       "language": "zh",
       "style": "professional"
     }'

API将返回一个任务ID，您可以使用它来跟踪生成进度。

第四步：检查生成状态
------------------

.. code-block:: bash

   curl https://your-api-gateway-url/tasks/{task_id}/status

第五步：下载演示文稿
------------------

生成完成后，下载演示文稿：

.. code-block:: bash

   curl https://your-api-gateway-url/presentations/{task_id} -o presentation.pptx

支持的参数
----------

创建演示文稿时，您可以使用以下参数：

.. list-table:: 演示文稿参数
   :widths: 25 25 50
   :header-rows: 1

   * - 参数
     - 类型
     - 描述
   * - title
     - string
     - 演示文稿标题 (必需)
   * - topic
     - string
     - 主题内容 (必需)
   * - duration
     - integer
     - 演示时长(分钟) 5-120
   * - slide_count
     - integer
     - 幻灯片数量 5-100
   * - language
     - string
     - 语言 (en, ja, zh, es, fr, de, pt, ko)
   * - style
     - string
     - 风格 (professional, creative, minimalist, technical, academic)
   * - audience
     - string
     - 目标受众
   * - include_speaker_notes
     - boolean
     - 是否包含演讲备注
   * - include_images
     - boolean
     - 是否包含图片

使用前端界面 (可选)
-----------------

如果您部署了前端界面，可以通过浏览器访问：

1. 启动前端开发服务器：

.. code-block:: bash

   cd frontend
   npm run dev

2. 在浏览器中访问 http://localhost:3000

3. 使用图形界面创建演示文稿

故障排除
--------

如果遇到问题，请检查：

1. AWS凭证是否正确配置
2. Bedrock服务是否在您的区域可用
3. Lambda函数是否有足够的权限
4. 查看 :doc:`troubleshooting` 获取更多帮助

下一步
------

现在您已经成功创建了第一个演示文稿！您可以：

* 阅读 :doc:`configuration` 了解详细配置选项
* 查看 :doc:`../api/lambdas` API文档
* 探索 :doc:`architecture` 了解系统架构