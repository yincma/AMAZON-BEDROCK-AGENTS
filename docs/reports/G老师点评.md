结论（先给答案）
可行：该《问题修复计划》基本可落地，能把当前环境恢复到可用状态。
还不够“长久”：要成为长期稳态方案，需要补上配置统一、标识一致性、密钥管理、IaC落盘与数据迁移等关键环节，否则会反复出现漂移和环境不一致问题。
需要调整的关键点（高优先级）
Bedrock Agent 标识不一致
《问题报告.md》中同时出现了两套Agent标识：
“实际Agent ID”一组：Q6RODNGFYR / L0ZQHJSU4X / FO53FNXIRL / B02XIGCUKI
“4.2 配置”一组：NLZPTOVMQ5 / LG4G5YGKJQ / LDGBZPBZEZ / CCGOODF22J
建议：统一以“别名”为准进行调用，把Lambda环境变量改为使用“别名”而非硬编码ID，所有Agent创建统一别名（如dev），避免ID变化带来的连锁修改。计划中只为orchestrator使用了ORCHESTRATOR_ALIAS_ID，建议为四个Agent全部建立别名并在代码与配置中统一引用。
API Gateway 多ID/多Stage 混用
文档中出现了两个API ID：otmr3noxg5 与 t8jhz8li6e，且legacy/dev交叉使用。计划里既有指向legacy的说明，也有统一到dev的操作。
建议：只保留一个API（建议保留当前使用计划关联更清晰的那个），只保留一个Stage（建议dev）。删除其它API与多余Stage，重新把Usage Plan绑定到唯一的dev，并统一所有脚本、配置与文档的Base URL。完成后立即轮换API Key（文档已泄露Key值）。
DynamoDB 表名与数据一致性
现状是写tasks、查sessions。计划建议统一用sessions，但没安排迁移。
建议：明确“权威表”后进行数据迁移（当前tasks里已有2条记录）。短平快可选：先把presentation-status临时改查tasks，恢复功能；随后脚本迁移历史数据，最终统一为sessions并删除写入tasks路径。若未来确需两表，可用DynamoDB Streams做双写/回填，避免查询404。
环境变量更新的长期做法
计划中短期用CLI/Python更新可行，但容易再次漂移。
建议：把Lambda环境变量、API URL、表名、Agent别名等全部纳管到Terraform/SAM/CDK与SSM Parameter Store中。部署只读参数中心，不再把密钥与动态ID写入仓库文件。并开启部署后“自动验收”步骤（健康检查+端到端测试）。
密钥与敏感信息
文档中包含真实API Key，且api_config_info.json明文存储。
建议：立刻轮换Key、从仓库与报告中清除敏感值，改为从SSM Parameter Store或Secrets Manager按环境拉取；api_config_info.json仅保留非敏感信息或引用参数名。
具体建议（对照计划的精炼补充/修正）
替换硬编码Agent ID为“别名”
为四个Agent统一创建并使用别名（如dev），Lambda仅持别名；Agent ID变化时无需改代码/配置。
统一唯一API与Stage
选定一个API（建议继续用otmr3noxg5或以名字检索现网在用的），统一Stage为dev；把Usage Plan绑定到dev，删除legacy，更新所有脚本、测试与文档URL。
数据迁移
在统一表名前，补一条一次性迁移脚本，把tasks的现存数据迁到sessions（或反之），并回收旧通路，避免状态查询404。
IaC 与参数中心
Terraform中声明aws_ssm_parameter并在aws_lambda_function.environment里引用，禁止手工更改生产环境变量；在CI/CD中执行部署后自动验证脚本（你已有test_all_backend_apis.py与system_health_check.py，直接串联）。
安全与合规
轮换API Key，所有环境的Key改为只保存在Parameter Store，前后端与测试脚本以环境变量或参数拉取；禁止在仓库中落地真实Key/ID。
脚本健壮性
计划里用CLI直接传--environment Variables='{}'在macOS zsh环境易因转义失败，优先使用你文档中提供的boto3脚本方案（已写的fix_lambda_env.py/update_lambda_env.py），或改为“从文件读取JSON”的CLI形式。
Usage Plan变更路径
计划中的/apiStages/0/...操作对数组下标脆弱，建议按“restApiId+stageName”精确定位，或先清空再添加，避免重复或下标错位。
版本管理策略
如要长期保留v1/v2，建议使用“自定义域名 + Base Path Mapping（/v1、/v2）”，而不是堆多个Stage名与分散URL；否则测试/文档/监控都会复杂化。
可观测性与成本控制
X-Ray与CloudWatch告警的方向正确；再补充结构化日志、链路ID（通过API网关传递header到Lambda），并设置关键函数并发保护与指标报警（错误率、超时、冷启动）。
一步到位的“长期化”补强（落地即可杜绝反复）
配置中心化：SSM Parameter Store持久化API_BASE_URL、API_KEY、DYNAMODB_TABLE、AGENT_ALIAS_*，Terraform引用，Lambda按环境读取。
单一真相源：只保留一个API与Stage，删除其余资源，避免下一次“指向错环境”。
数据模型基线：确定“sessions”为权威表，提供迁移脚本与回滚脚本，测试通过后冻结写tasks路径。
CI/CD校验闸：部署后自动跑健康检查+端到端测试+告警自检，不通过则阻断发布并自动回滚。
密钥治理：强制密钥轮换与扫描（如gitleaks），仓库禁止明文密钥。
结语
现有《问题修复计划》可以把系统快速修复到“可用态”；在此基础上按上面的补强落地（尤其是Agent别名化、API与Stage唯一化、SSM参数化与数据迁移），就能成为“长期稳态”的解决方案，避免后续反复踩坑。