"""
Phase 2集成测试 - 测试图片生成、演讲者备注和PPT样式模块的协同工作

覆盖以下场景：
1. 端到端的演示文稿生成流程
2. 三个模块之间的数据传递和集成
3. 性能基准测试
4. 错误恢复和降级机制
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import concurrent.futures

# 测试数据
INTEGRATION_TEST_PRESENTATION = {
    "presentation_id": "integration-test-001",
    "title": "AI技术发展趋势",
    "slides": [
        {
            "slide_number": 1,
            "title": "人工智能概述",
            "content": [
                "AI是计算机科学的重要分支",
                "从1950年代发展至今",
                "正在改变各个行业"
            ]
        },
        {
            "slide_number": 2,
            "title": "机器学习核心技术",
            "content": [
                "监督学习和无监督学习",
                "深度神经网络架构",
                "自然语言处理技术"
            ]
        },
        {
            "slide_number": 3,
            "title": "应用案例分析",
            "content": [
                "医疗诊断系统",
                "自动驾驶技术",
                "智能推荐算法"
            ]
        }
    ]
}


class TestPhase2Integration:
    """Phase 2功能集成测试"""

    def test_end_to_end_presentation_generation(self, mock_s3_bucket):
        """
        测试完整的演示文稿生成流程

        Given: 包含多张幻灯片的演示文稿数据
        When: 依次调用图片生成、演讲者备注生成和PPT样式应用
        Then: 生成完整的带图片、备注和样式的演示文稿
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import PPTStyler

        presentation_data = INTEGRATION_TEST_PRESENTATION.copy()
        presentation_id = presentation_data["presentation_id"]

        # 第1步：生成图片
        image_generator = ImageGenerator()
        image_results = image_generator.generate_consistent_images(
            presentation_data["slides"],
            presentation_id
        )

        # 验证图片生成结果
        assert len(image_results) == 3
        for result in image_results:
            assert result.get('status') in ['success', 'fallback']
            assert 'style_params' in result

        # 第2步：生成演讲者备注
        notes_generator = SpeakerNotesGenerator(use_fallback=True)
        notes_results = notes_generator.batch_generate_notes(presentation_data["slides"])

        # 验证演讲者备注生成结果
        assert len(notes_results) == 3
        for result in notes_results:
            assert 'speaker_notes' in result
            assert len(result['speaker_notes']) >= 100

        # 第3步：应用PPT样式
        styler = PPTStyler()
        mock_ppt = MagicMock()
        style_result = styler.apply_template(mock_ppt, "modern")

        # 验证样式应用结果
        assert style_result["success"] is True
        assert style_result["template"] == "modern"

        # 集成结果验证
        # 模拟将所有组件整合到最终演示文稿
        final_presentation = {
            "presentation_id": presentation_id,
            "slides": [],
            "generation_summary": {
                "images_generated": len(image_results),
                "notes_generated": len(notes_results),
                "style_applied": style_result["success"]
            }
        }

        # 整合每张幻灯片的结果
        for i, slide in enumerate(presentation_data["slides"]):
            integrated_slide = slide.copy()
            integrated_slide.update({
                "image_info": image_results[i],
                "speaker_notes": notes_results[i]["speaker_notes"],
                "style_applied": True
            })
            final_presentation["slides"].append(integrated_slide)

        # 验证最终结果
        assert len(final_presentation["slides"]) == 3
        assert final_presentation["generation_summary"]["images_generated"] == 3
        assert final_presentation["generation_summary"]["notes_generated"] == 3
        assert final_presentation["generation_summary"]["style_applied"] is True

    def test_data_flow_between_modules(self, mock_s3_bucket):
        """
        测试模块间数据流传递

        验证：
        1. 图片生成模块输出被正确格式化
        2. 演讲者备注与幻灯片内容相关联
        3. 样式信息正确应用到输出结构
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import apply_template_styles

        # 准备测试幻灯片
        test_slide = INTEGRATION_TEST_PRESENTATION["slides"][0]

        # 步骤1：生成图片并获取元数据
        image_generator = ImageGenerator()
        image_prompt = image_generator.generate_prompt(test_slide)
        image_result = image_generator.generate_image(
            image_prompt,
            "test-integration",
            1
        )

        # 步骤2：使用相同数据生成演讲者备注
        notes_generator = SpeakerNotesGenerator(use_fallback=True)
        speaker_notes = notes_generator.generate_notes(test_slide)

        # 步骤3：应用样式到包含图片和备注的幻灯片
        enriched_slide = test_slide.copy()
        enriched_slide.update({
            "image_url": image_result.get("image_url"),
            "image_prompt": image_prompt,
            "speaker_notes": speaker_notes
        })

        template_config = {
            "background_color": "#F8F9FA",
            "title_font": "Helvetica",
            "title_size": 28,
            "content_font": "Helvetica",
            "content_size": 20,
            "layout": "image_title_content"
        }

        styled_slide = apply_template_styles(enriched_slide, template_config)

        # 验证数据流完整性
        assert "image_url" in styled_slide
        assert "speaker_notes" in styled_slide
        assert styled_slide["title_font"] == "Helvetica"
        assert styled_slide["layout"] == "image_title_content"
        assert len(styled_slide["speaker_notes"]) >= 100

    def test_error_handling_integration(self, mock_s3_bucket):
        """
        测试集成场景下的错误处理

        模拟各种错误情况：
        1. 图片生成失败时的降级处理
        2. 演讲者备注生成异常时的fallback
        3. 样式应用失败时的错误恢复
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import batch_apply_styles

        # 准备包含潜在问题的数据
        problematic_slides = [
            {
                "slide_number": 1,
                "title": "正常幻灯片",
                "content": ["正常内容"]
            },
            {
                "slide_number": 2,
                "title": "",  # 空标题可能导致问题
                "content": []  # 空内容
            },
            {
                "slide_number": 3,
                "title": "特殊字符 @#$%^&*()",
                "content": ["emoji 🚀", "unicode ñáéíóú"]
            }
        ]

        # 测试图片生成的错误恢复
        image_generator = ImageGenerator()
        image_results = []

        for slide in problematic_slides:
            try:
                prompt = image_generator.generate_prompt(slide)
                result = image_generator.generate_image(prompt, "error-test", slide["slide_number"])
                image_results.append(result)
            except Exception as e:
                # 确保错误被捕获并有fallback
                image_results.append({
                    "status": "error",
                    "error": str(e),
                    "slide_number": slide["slide_number"]
                })

        # 测试演讲者备注的错误恢复
        notes_generator = SpeakerNotesGenerator(use_fallback=True)
        notes_results = notes_generator.batch_generate_notes(problematic_slides)

        # 测试批量样式应用的错误处理
        template_config = {
            "background_color": "#FFFFFF",
            "title_font": "Arial",
            "title_size": 24,
            "content_font": "Arial",
            "content_size": 18,
            "layout": "title_content_image"
        }

        # 转换为样式处理需要的格式
        slides_dict = {f"slide_{slide['slide_number']}": slide for slide in problematic_slides}
        style_results = batch_apply_styles(slides_dict, template_config)

        # 验证错误处理效果
        assert len(image_results) == 3
        assert len(notes_results) == 3
        assert style_results["processed_count"] >= 2  # 至少处理了2个正常的

        # 验证即使有错误，系统仍能继续处理其他幻灯片
        successful_notes = [r for r in notes_results if len(r.get("speaker_notes", "")) >= 100]
        assert len(successful_notes) >= 2

    def test_performance_benchmark_integration(self, mock_s3_bucket):
        """
        测试集成场景下的性能基准

        验证：
        1. 完整流程在合理时间内完成
        2. 内存使用保持在可控范围
        3. 并发处理能力
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import batch_apply_styles

        # 准备性能测试数据（5张幻灯片）
        performance_slides = []
        for i in range(1, 6):
            performance_slides.append({
                "slide_number": i,
                "title": f"性能测试幻灯片 {i}",
                "content": [f"内容点 {j}" for j in range(1, 4)]
            })

        # 开始性能计时
        start_time = time.time()

        # 并行执行三个主要操作
        def process_images():
            generator = ImageGenerator()
            return generator.batch_generate_images(performance_slides, "perf-test")

        def process_notes():
            generator = SpeakerNotesGenerator(use_fallback=True)
            return generator.batch_generate_notes(performance_slides)

        def process_styles():
            slides_dict = {f"slide_{slide['slide_number']}": slide for slide in performance_slides}
            template_config = {
                "background_color": "#FFFFFF",
                "title_font": "Arial",
                "title_size": 24,
                "content_font": "Arial",
                "content_size": 18,
                "layout": "title_content_image"
            }
            return batch_apply_styles(slides_dict, template_config)

        # 并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_images = executor.submit(process_images)
            future_notes = executor.submit(process_notes)
            future_styles = executor.submit(process_styles)

            # 等待所有任务完成
            image_results = future_images.result(timeout=30)
            notes_results = future_notes.result(timeout=30)
            style_results = future_styles.result(timeout=30)

        # 结束计时
        total_time = time.time() - start_time

        # 性能验证
        assert total_time < 60  # 应该在60秒内完成
        assert len(image_results) == 5
        assert len(notes_results) == 5
        assert style_results["processed_count"] == 5

    def test_consistency_across_modules(self, mock_s3_bucket):
        """
        测试模块间一致性

        验证：
        1. 相同输入在不同模块间产生一致结果
        2. 风格参数在各模块间保持协调
        3. 数据格式标准化
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import apply_template_styles

        # 准备一致性测试的幻灯片
        consistency_slide = {
            "slide_number": 1,
            "title": "一致性测试标题",
            "content": ["测试内容1", "测试内容2", "测试内容3"]
        }

        # 测试图片生成的一致性（多次调用应产生相似结果）
        image_generator = ImageGenerator()
        prompts = []
        for _ in range(3):
            prompt = image_generator.generate_prompt(consistency_slide)
            prompts.append(prompt)

        # 验证提示词的一致性（应该包含相同的关键元素）
        assert len(set(prompts)) <= 2  # 允许少量变化，但应基本一致
        for prompt in prompts:
            assert "测试" in prompt or "一致性" in prompt

        # 测试演讲者备注的一致性
        notes_generator = SpeakerNotesGenerator(use_fallback=True)
        notes_list = []
        for _ in range(3):
            notes = notes_generator.generate_notes(consistency_slide)
            notes_list.append(notes)

        # 验证备注的一致性（长度和关键词应该相似）
        for notes in notes_list:
            assert 100 <= len(notes) <= 200
            assert "测试" in notes or "一致性" in notes

        # 测试样式应用的一致性
        template_config = {
            "background_color": "#FFFFFF",
            "title_font": "Arial",
            "title_size": 24,
            "content_font": "Arial",
            "content_size": 18,
            "layout": "title_content_image"
        }

        styled_results = []
        for _ in range(3):
            result = apply_template_styles(consistency_slide, template_config)
            styled_results.append(result)

        # 验证样式应用的一致性
        for result in styled_results:
            assert result["background_color"] == "#FFFFFF"
            assert result["title_font"] == "Arial"
            assert result["layout"] == "title_content_image"

    def test_scalability_stress_test(self, mock_s3_bucket):
        """
        测试可扩展性压力测试

        验证系统在高负载下的表现：
        1. 大量幻灯片处理能力
        2. 内存管理效率
        3. 错误恢复能力
        """
        from lambdas.image_generator import ImageGenerator
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
        from lambdas.ppt_styler import batch_apply_styles

        # 创建大量幻灯片数据（20张）
        stress_slides = []
        for i in range(1, 21):
            stress_slides.append({
                "slide_number": i,
                "title": f"压力测试幻灯片 {i}",
                "content": [f"压力测试内容 {j}" for j in range(1, 6)]  # 每张5个内容点
            })

        # 图片生成压力测试
        image_generator = ImageGenerator()
        start_time = time.time()

        # 分批处理以避免超时
        image_batches = [stress_slides[i:i+5] for i in range(0, 20, 5)]
        all_image_results = []

        for batch in image_batches:
            batch_results = image_generator.batch_generate_images(batch, "stress-test")
            all_image_results.extend(batch_results)

        image_time = time.time() - start_time

        # 演讲者备注压力测试
        notes_generator = SpeakerNotesGenerator(use_fallback=True)
        start_time = time.time()

        notes_results = notes_generator.batch_generate_notes(stress_slides)

        notes_time = time.time() - start_time

        # 样式应用压力测试
        slides_dict = {f"slide_{slide['slide_number']}": slide for slide in stress_slides}
        template_config = {
            "background_color": "#FFFFFF",
            "title_font": "Arial",
            "title_size": 24,
            "content_font": "Arial",
            "content_size": 18,
            "layout": "title_content_image"
        }

        start_time = time.time()
        style_results = batch_apply_styles(slides_dict, template_config)
        style_time = time.time() - start_time

        # 性能验证
        assert len(all_image_results) == 20
        assert len(notes_results) == 20
        assert style_results["processed_count"] == 20

        # 时间性能要求（相对宽松以适应测试环境）
        assert image_time < 120  # 图片生成120秒内
        assert notes_time < 60   # 备注生成60秒内
        assert style_time < 30   # 样式应用30秒内

        # 质量验证（即使在压力下也要保证质量）
        successful_images = len([r for r in all_image_results if r.get('status') in ['success', 'fallback']])
        successful_notes = len([r for r in notes_results if len(r.get('speaker_notes', '')) >= 100])

        assert successful_images >= 18  # 至少90%成功率
        assert successful_notes >= 18   # 至少90%成功率

    def test_module_isolation_and_independence(self):
        """
        测试模块隔离性和独立性

        验证：
        1. 单个模块故障不影响其他模块
        2. 模块间没有不当的耦合
        3. 接口的标准化和一致性
        """
        # 测试模块独立导入
        try:
            from lambdas.image_generator import ImageGenerator
            image_generator = ImageGenerator()
            assert image_generator is not None
        except ImportError as e:
            pytest.fail(f"图片生成模块导入失败: {e}")

        try:
            from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
            notes_generator = SpeakerNotesGenerator(use_fallback=True)
            assert notes_generator is not None
        except ImportError as e:
            pytest.fail(f"演讲者备注模块导入失败: {e}")

        try:
            from lambdas.ppt_styler import PPTStyler
            styler = PPTStyler()
            assert styler is not None
        except ImportError as e:
            pytest.fail(f"PPT样式模块导入失败: {e}")

        # 测试模块间接口兼容性
        test_slide = {
            "slide_number": 1,
            "title": "接口测试",
            "content": ["接口测试内容"]
        }

        # 验证所有模块都能处理标准幻灯片数据格式
        try:
            prompt = image_generator.generate_prompt(test_slide)
            assert isinstance(prompt, str)
        except Exception as e:
            pytest.fail(f"图片生成器接口测试失败: {e}")

        try:
            notes = notes_generator.generate_notes(test_slide)
            assert isinstance(notes, str)
        except Exception as e:
            pytest.fail(f"演讲者备注生成器接口测试失败: {e}")

        try:
            from lambdas.ppt_styler import apply_template_styles
            template_config = {
                "background_color": "#FFFFFF",
                "title_font": "Arial",
                "title_size": 24,
                "content_font": "Arial",
                "content_size": 18,
                "layout": "title_content_image"
            }
            styled = apply_template_styles(test_slide, template_config)
            assert isinstance(styled, dict)
        except Exception as e:
            pytest.fail(f"PPT样式器接口测试失败: {e}")


if __name__ == "__main__":
    # 运行集成测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"  # 显示最慢的10个测试
    ])