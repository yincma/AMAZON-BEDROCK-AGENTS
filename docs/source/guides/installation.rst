安装指南
========

系统要求
--------

在开始安装之前，请确保您的系统满足以下要求：

* Python 3.13 或更高版本
* AWS CLI (配置了适当的权限)
* Node.js 18+ (用于前端开发)
* Terraform (用于基础设施部署)

环境准备
--------

1. 克隆代码仓库
~~~~~~~~~~~~~~

.. code-block:: bash

   git clone <repository-url>
   cd ai-ppt-assistant

2. 创建Python虚拟环境
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows

3. 安装依赖包
~~~~~~~~~~~

.. code-block:: bash

   make install

这将安装所有必要的Python依赖包。

AWS配置
-------

1. 配置AWS凭证
~~~~~~~~~~~~

.. code-block:: bash

   aws configure

输入您的AWS Access Key ID、Secret Access Key和默认区域。

2. 验证权限
~~~~~~~~~

确保您的AWS账户具有以下服务的权限：

* Amazon Bedrock
* AWS Lambda
* Amazon DynamoDB
* Amazon S3
* Amazon SQS
* Amazon API Gateway
* AWS CloudFormation

前端安装 (可选)
--------------

如果需要运行前端开发服务器：

.. code-block:: bash

   cd frontend
   npm install
   npm run dev

验证安装
--------

运行以下命令验证安装是否成功：

.. code-block:: bash

   make test-unit

如果所有测试通过，说明安装成功。

下一步
------

安装完成后，您可以继续阅读：

* :doc:`quickstart` - 快速开始指南
* :doc:`configuration` - 配置说明
* :doc:`deployment` - 部署指南