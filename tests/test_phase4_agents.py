"""
Phase 4 Agent Tests - TDD开发测试套件
测试Amazon Bedrock Agents的第四阶段功能
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestOrchestratorAgent:
    """主调度Agent测试"""

    def test_analyze_request_type(self):
        """测试请求类型分析"""
        # Given: 不同类型的请求
        doc_request = {
            "action": "convert_document",
            "document_path": "s3://bucket/document.pdf"
        }
        batch_request = {
            "action": "batch_generate",
            "topics": ["AI技术", "云计算", "大数据"]
        }
        single_request = {
            "action": "generate",
            "topic": "机器学习基础"
        }

        from agents.orchestrator import OrchestratorAgent
        agent = OrchestratorAgent()

        # When: 分析请求类型
        doc_type = agent.analyze_request(doc_request)
        batch_type = agent.analyze_request(batch_request)
        single_type = agent.analyze_request(single_request)

        # Then: 返回正确的类型
        assert doc_type == "document_conversion"
        assert batch_type == "batch_generation"
        assert single_type == "single_generation"

    def test_dispatch_to_agents(self):
        """测试任务分发到子Agent"""
        # Given: 一个文档转换请求
        request = {
            "action": "convert_document",
            "document_path": "s3://bucket/report.pdf",
            "page_count": 10
        }

        from agents.orchestrator import OrchestratorAgent
        agent = OrchestratorAgent()

        # When: 分发任务
        result = agent.dispatch_task(request)

        # Then: 正确调用Document Analyzer
        assert result["agent_called"] == "document-analyzer-agent"
        assert result["status"] == "dispatched"
        assert "task_id" in result

    def test_manage_shared_context(self):
        """测试共享上下文管理"""
        # Given: 初始化上下文
        from agents.orchestrator import OrchestratorAgent
        agent = OrchestratorAgent()

        # When: 创建和更新上下文
        context = agent.create_context("session_123", "user_456")
        context = agent.update_context(context, "document_analysis", {
            "page_count": 10,
            "key_points": ["point1", "point2"]
        })

        # Then: 上下文正确维护
        assert context["session_id"] == "session_123"
        assert context["document_analysis"]["page_count"] == 10
        assert len(context["document_analysis"]["key_points"]) == 2


class TestDocumentAnalyzerAgent:
    """文档分析Agent测试"""

    def test_parse_pdf_document(self):
        """测试PDF文档解析"""
        # Given: PDF文档内容
        mock_pdf_content = {
            "text": "这是一份关于AI技术的报告...",
            "pages": 20,
            "charts": 5
        }

        from agents.document_analyzer import DocumentAnalyzerAgent
        agent = DocumentAnalyzerAgent()

        # When: 解析文档
        with patch('agents.document_analyzer.extract_pdf_content', return_value=mock_pdf_content):
            result = agent.parse_document("s3://bucket/report.pdf")

        # Then: 提取关键信息
        assert result["total_pages"] == 20
        assert result["chart_count"] == 5
        assert "outline" in result
        assert len(result["outline"]["slides"]) <= 10  # 不超过原文档20%

    def test_extract_key_points(self):
        """测试关键点提取"""
        # Given: 文档内容
        content = """
        第一章：AI概述
        人工智能是计算机科学的一个分支...

        第二章：机器学习
        机器学习是AI的核心技术...

        第三章：深度学习
        深度学习使用神经网络...
        """

        from agents.document_analyzer import DocumentAnalyzerAgent
        agent = DocumentAnalyzerAgent()

        # When: 提取关键点
        key_points = agent.extract_key_points(content)

        # Then: 返回结构化的关键点
        assert len(key_points) == 3
        assert key_points[0]["title"] == "AI概述"
        assert "关键内容" in key_points[0]

    def test_generate_ppt_outline(self):
        """测试PPT大纲生成"""
        # Given: 分析后的文档数据
        analysis = {
            "key_points": [
                {"title": "AI概述", "content": "..."},
                {"title": "机器学习", "content": "..."},
                {"title": "深度学习", "content": "..."}
            ],
            "suggested_pages": 8
        }

        from agents.document_analyzer import DocumentAnalyzerAgent
        agent = DocumentAnalyzerAgent()

        # When: 生成PPT大纲
        outline = agent.generate_outline(analysis)

        # Then: 大纲符合要求
        assert outline["page_count"] == 8
        assert len(outline["slides"]) == 8
        assert outline["slides"][0]["type"] == "title"
        assert outline["slides"][-1]["type"] == "conclusion"


class TestContentGeneratorAgent:
    """内容生成Agent测试"""

    def test_generate_slide_content(self):
        """测试幻灯片内容生成"""
        # Given: 大纲中的一页
        slide_outline = {
            "title": "什么是机器学习",
            "key_points": ["定义", "应用场景", "基本原理"],
            "page_number": 2
        }

        from agents.content_generator import ContentGeneratorAgent
        agent = ContentGeneratorAgent()

        # When: 生成内容
        content = agent.generate_slide_content(slide_outline)

        # Then: 内容完整
        assert content["title"] == "什么是机器学习"
        assert len(content["bullet_points"]) == 3
        assert len(content["speaker_notes"]) > 100  # 演讲备注100-200字
        assert content["suggested_image_type"] in ["diagram", "photo", "chart"]

    def test_batch_content_generation(self):
        """测试批量内容生成"""
        # Given: 多页大纲
        outline = {
            "slides": [
                {"title": "标题页", "type": "title"},
                {"title": "概述", "type": "content"},
                {"title": "详情", "type": "content"}
            ]
        }

        from agents.content_generator import ContentGeneratorAgent
        agent = ContentGeneratorAgent()

        # When: 批量生成
        results = agent.batch_generate(outline)

        # Then: 所有页面都生成
        assert len(results) == 3
        assert all("content" in slide for slide in results)
        assert all("speaker_notes" in slide for slide in results)


class TestVisualDesignerAgent:
    """视觉设计Agent测试"""

    def test_generate_image_prompt(self):
        """测试图片提示词生成"""
        # Given: 幻灯片内容
        slide = {
            "title": "机器学习应用",
            "content": "机器学习在医疗、金融、交通等领域的应用",
            "suggested_image_type": "diagram"
        }

        from agents.visual_designer import VisualDesignerAgent
        agent = VisualDesignerAgent()

        # When: 生成图片提示词
        prompt = agent.generate_image_prompt(slide)

        # Then: 提示词质量
        assert "diagram" in prompt.lower()
        assert "machine learning" in prompt.lower()
        assert len(prompt) > 50

    def test_apply_template(self):
        """测试模板应用"""
        # Given: PPT内容和模板
        content = {
            "slides": [{"title": "Test", "content": "..."}],
            "template": "modern"
        }

        from agents.visual_designer import VisualDesignerAgent
        agent = VisualDesignerAgent()

        # When: 应用模板
        styled_content = agent.apply_template(content)

        # Then: 样式正确应用
        assert styled_content["template_applied"] == "modern"
        assert "styles" in styled_content
        assert styled_content["styles"]["font_family"] == "Arial"

    def test_layout_optimization(self):
        """测试布局优化"""
        # Given: 带图片的幻灯片
        slide = {
            "title": "标题",
            "content": ["点1", "点2", "点3"],
            "image_url": "s3://bucket/image.png"
        }

        from agents.visual_designer import VisualDesignerAgent
        agent = VisualDesignerAgent()

        # When: 优化布局
        optimized = agent.optimize_layout(slide)

        # Then: 布局合理
        assert optimized["layout_type"] == "two_column"
        assert optimized["image_position"] == "right"
        assert optimized["text_position"] == "left"


class TestQualityCheckerAgent:
    """质量检查Agent测试"""

    def test_check_content_completeness(self):
        """测试内容完整性检查"""
        # Given: PPT内容
        presentation = {
            "slides": [
                {"title": "标题", "content": "..."},
                {"title": "", "content": "..."},  # 缺少标题
                {"title": "结论", "content": ""}   # 缺少内容
            ]
        }

        from agents.quality_checker import QualityCheckerAgent
        agent = QualityCheckerAgent()

        # When: 检查完整性
        issues = agent.check_completeness(presentation)

        # Then: 发现问题
        assert len(issues) == 2
        assert issues[0]["slide"] == 2
        assert issues[0]["issue"] == "missing_title"
        assert issues[1]["slide"] == 3
        assert issues[1]["issue"] == "missing_content"

    def test_evaluate_visual_quality(self):
        """测试视觉质量评估"""
        # Given: 带图片的PPT
        presentation = {
            "slides": [
                {"title": "Slide 1", "image_url": "s3://bucket/img1.png"},
                {"title": "Slide 2", "image_url": None},
                {"title": "Slide 3", "image_url": "s3://bucket/img3.png"}
            ]
        }

        from agents.quality_checker import QualityCheckerAgent
        agent = QualityCheckerAgent()

        # When: 评估视觉质量
        score = agent.evaluate_visual_quality(presentation)

        # Then: 返回评分
        assert 0 <= score["overall_score"] <= 100
        assert score["image_coverage"] == 2/3  # 66.7%的页面有图片
        assert "suggestions" in score

    def test_coherence_check(self):
        """测试内容连贯性检查"""
        # Given: PPT内容
        presentation = {
            "slides": [
                {"title": "AI介绍", "content": "人工智能..."},
                {"title": "量子计算", "content": "量子..."},  # 跳跃太大
                {"title": "总结", "content": "综上..."}
            ]
        }

        from agents.quality_checker import QualityCheckerAgent
        agent = QualityCheckerAgent()

        # When: 检查连贯性
        coherence = agent.check_coherence(presentation)

        # Then: 识别不连贯
        assert coherence["score"] < 80
        assert len(coherence["issues"]) > 0
        assert coherence["issues"][0]["between_slides"] == [1, 2]


class TestBatchProcessing:
    """批量处理功能测试"""

    def test_batch_request_validation(self):
        """测试批量请求验证"""
        # Given: 批量请求
        valid_batch = {
            "batch_size": 5,
            "requests": [{"topic": f"Topic {i}"} for i in range(5)]
        }
        invalid_batch = {
            "batch_size": 15,  # 超过最大限制10
            "requests": [{"topic": f"Topic {i}"} for i in range(15)]
        }

        from agents.batch_processor import BatchProcessor
        processor = BatchProcessor()

        # When: 验证请求
        valid_result = processor.validate_batch(valid_batch)
        invalid_result = processor.validate_batch(invalid_batch)

        # Then: 正确验证
        assert valid_result["valid"] is True
        assert invalid_result["valid"] is False
        assert invalid_result["error"] == "batch_size_exceeded"

    def test_batch_execution_strategy(self):
        """测试批量执行策略"""
        # Given: 不同大小的批量
        small_batch = [{"id": i} for i in range(3)]
        medium_batch = [{"id": i} for i in range(6)]
        large_batch = [{"id": i} for i in range(10)]

        from agents.batch_processor import BatchProcessor
        processor = BatchProcessor()

        # When: 确定执行策略
        small_strategy = processor.get_execution_strategy(small_batch)
        medium_strategy = processor.get_execution_strategy(medium_batch)
        large_strategy = processor.get_execution_strategy(large_batch)

        # Then: 策略正确
        assert small_strategy == "parallel"
        assert medium_strategy == "grouped"
        assert large_strategy == "sequential"

    def test_batch_progress_tracking(self):
        """测试批量进度跟踪"""
        # Given: 批量任务
        batch_id = "batch_123"
        tasks = [{"id": f"task_{i}", "status": "pending"} for i in range(5)]

        from agents.batch_processor import BatchProcessor
        processor = BatchProcessor()

        # When: 更新进度
        processor.init_batch(batch_id, tasks)
        processor.update_task_status(batch_id, "task_0", "completed")
        processor.update_task_status(batch_id, "task_1", "completed")
        processor.update_task_status(batch_id, "task_2", "processing")

        progress = processor.get_batch_progress(batch_id)

        # Then: 进度正确
        assert progress["total"] == 5
        assert progress["completed"] == 2
        assert progress["processing"] == 1
        assert progress["pending"] == 2
        assert progress["percentage"] == 40  # 2/5 = 40%


class TestIntegration:
    """集成测试"""

    @pytest.mark.integration
    def test_document_conversion_flow(self):
        """测试完整的文档转换流程"""
        # Given: PDF文档
        request = {
            "action": "convert_document",
            "document_path": "s3://test-bucket/sample.pdf",
            "user_id": "test_user",
            "output_format": "pptx"
        }

        from agents.integration import process_request

        # When: 处理请求
        with patch('agents.document_analyzer.extract_pdf_content'):
            with patch('agents.content_generator.generate_with_bedrock'):
                result = process_request(request)

        # Then: 成功生成PPT
        assert result["status"] == "completed"
        assert "presentation_url" in result
        assert result["page_count"] <= 10

    @pytest.mark.integration
    def test_batch_generation_flow(self):
        """测试批量生成流程"""
        # Given: 批量请求
        batch_request = {
            "action": "batch_generate",
            "topics": ["AI基础", "机器学习", "深度学习"],
            "template": "modern",
            "user_id": "test_user"
        }

        from agents.integration import process_batch_request

        # When: 处理批量请求
        with patch('agents.content_generator.generate_with_bedrock'):
            results = process_batch_request(batch_request)

        # Then: 所有请求都处理
        assert len(results) == 3
        assert all(r["status"] in ["completed", "failed"] for r in results)
        success_count = sum(1 for r in results if r["status"] == "completed")
        assert success_count >= 2  # 至少2个成功


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])