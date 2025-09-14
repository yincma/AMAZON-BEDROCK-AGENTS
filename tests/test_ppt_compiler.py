"""
PPT编译测试 - 验证PPTX文件生成功能
按照TDD原则，测试验证python-pptx库生成演示文稿的功能
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
import zipfile
from io import BytesIO


class TestPPTXFileGeneration:
    """PPTX文件生成基础测试"""

    @pytest.mark.unit
    def test_create_simple_ppt_from_content(self, sample_slide_content, mock_s3_bucket):
        """
        测试从JSON内容创建简单PPT
        验收标准：生成有效的PPTX文件，包含正确的页数和基本格式
        """
        # Given: 幻灯片内容数据
        content = sample_slide_content
        presentation_id = content["presentation_id"]

        # When: 调用PPT编译函数
        from src.ppt_compiler import create_pptx_from_content
        pptx_bytes = create_pptx_from_content(content)

        # Then: 验证生成的文件
        assert pptx_bytes is not None
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 1000  # PPTX文件应该有一定大小

        # 验证是否为有效的ZIP文件（PPTX本质上是ZIP）
        with BytesIO(pptx_bytes) as bio:
            assert zipfile.is_zipfile(bio), "PPTX应该是有效的ZIP文件"

    @pytest.mark.unit
    def test_ppt_slide_count_validation(self, mock_s3_bucket):
        """
        测试PPT页数正确性
        验收标准：生成的PPT应包含与输入内容相同的页数
        """
        # Given: 不同页数的内容
        test_cases = [
            {"slides": [{"title": f"幻灯片{i}", "bullet_points": ["要点1"]} for i in range(1, 4)]},  # 3页
            {"slides": [{"title": f"幻灯片{i}", "bullet_points": ["要点1"]} for i in range(1, 6)]},  # 5页
            {"slides": [{"title": f"幻灯片{i}", "bullet_points": ["要点1"]} for i in range(1, 11)]}  # 10页
        ]

        for content in test_cases:
            expected_slide_count = len(content["slides"])

            # When: 生成PPT并验证页数
            from src.ppt_compiler import create_pptx_from_content, get_slide_count
            pptx_bytes = create_pptx_from_content(content)
            actual_slide_count = get_slide_count(pptx_bytes)

            # Then: 验证页数
            assert actual_slide_count == expected_slide_count

    @pytest.mark.unit
    def test_ppt_content_formatting(self, sample_slide_content):
        """
        测试PPT内容格式化
        验收标准：标题和要点应正确显示在幻灯片中
        """
        # Given: 包含标题和要点的内容
        content = {
            "presentation_id": "test-123",
            "slides": [
                {
                    "slide_number": 1,
                    "title": "测试标题",
                    "bullet_points": [
                        "第一个要点",
                        "第二个要点",
                        "第三个要点"
                    ]
                }
            ]
        }

        # When: 生成PPT并验证内容
        from src.ppt_compiler import create_pptx_from_content, extract_text_content
        pptx_bytes = create_pptx_from_content(content)
        extracted_text = extract_text_content(pptx_bytes)

        # Then: 验证文本内容存在
        assert "测试标题" in extracted_text
        assert "第一个要点" in extracted_text
        assert "第二个要点" in extracted_text
        assert "第三个要点" in extracted_text

    @pytest.mark.unit
    def test_ppt_template_application(self):
        """
        测试PPT模板应用
        验收标准：生成的PPT应使用默认的专业模板
        """
        # Given: 基本内容
        content = {
            "slides": [
                {
                    "title": "标题页",
                    "bullet_points": ["要点1", "要点2"]
                }
            ]
        }

        # When: 应用模板生成PPT
        from src.ppt_compiler import create_pptx_with_template
        pptx_bytes = create_pptx_with_template(content, template_name="default")

        # Then: 验证模板应用
        assert pptx_bytes is not None
        # 可以检查特定的模板特征，如背景色、字体等

    @pytest.mark.unit
    def test_speaker_notes_inclusion(self):
        """
        测试演讲者备注包含
        验收标准：如果内容包含speaker_notes，应添加到PPTX的备注页
        """
        # Given: 包含演讲者备注的内容
        content = {
            "slides": [
                {
                    "title": "测试标题",
                    "bullet_points": ["要点1"],
                    "speaker_notes": "这是给演讲者的备注信息"
                }
            ]
        }

        # When: 生成包含备注的PPT
        from src.ppt_compiler import create_pptx_from_content, extract_speaker_notes
        pptx_bytes = create_pptx_from_content(content, include_notes=True)
        notes = extract_speaker_notes(pptx_bytes)

        # Then: 验证备注存在
        assert len(notes) > 0
        assert "这是给演讲者的备注信息" in notes[0]


class TestS3Integration:
    """S3存储集成测试"""

    @pytest.mark.integration
    @pytest.mark.aws
    def test_save_pptx_to_s3(self, mock_s3_bucket, sample_slide_content):
        """
        测试将生成的PPTX文件保存到S3
        验收标准：文件应成功保存并可通过S3访问
        """
        # Given: 生成的PPTX内容和S3配置
        content = sample_slide_content
        presentation_id = content["presentation_id"]
        bucket_name = "ai-ppt-presentations-test"
        mock_pptx_bytes = b"fake pptx content"  # 模拟PPTX数据

        # When: 保存到S3
        from src.ppt_compiler import save_pptx_to_s3
        s3_key = save_pptx_to_s3(
            mock_pptx_bytes,
            presentation_id,
            mock_s3_bucket,
            bucket_name
        )

        # Then: 验证文件保存
        expected_key = f"presentations/{presentation_id}/output/presentation.pptx"
        assert s3_key == expected_key

        # 验证文件存在
        response = mock_s3_bucket.get_object(Bucket=bucket_name, Key=s3_key)
        assert response["Body"].read() == mock_pptx_bytes

    @pytest.mark.integration
    @pytest.mark.aws
    def test_generate_presigned_download_url(self, mock_s3_bucket):
        """
        测试生成预签名下载URL
        验收标准：生成有效的下载链接，允许用户下载PPT文件
        """
        # Given: S3中的PPTX文件
        bucket_name = "ai-ppt-presentations-test"
        presentation_id = "test-123"
        s3_key = f"presentations/{presentation_id}/output/presentation.pptx"

        # 先上传一个文件
        mock_s3_bucket.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=b"fake pptx content",
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

        # When: 生成下载链接
        from src.ppt_compiler import generate_download_url
        download_url = generate_download_url(
            presentation_id,
            mock_s3_bucket,
            bucket_name,
            expires_in=3600
        )

        # Then: 验证URL生成
        assert download_url is not None
        assert bucket_name in download_url
        assert presentation_id in download_url
        assert "presentation.pptx" in download_url

    @pytest.mark.integration
    @pytest.mark.aws
    def test_file_metadata_storage(self, mock_s3_bucket):
        """
        测试文件元数据存储
        验收标准：应保存文件大小、生成时间等元数据
        """
        # Given: PPTX文件和元数据
        presentation_id = "test-123"
        bucket_name = "ai-ppt-presentations-test"
        pptx_bytes = b"fake pptx content"

        metadata = {
            "file_size": len(pptx_bytes),
            "slide_count": 5,
            "generated_at": "2024-01-15T10:30:00Z",
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }

        # When: 保存文件和元数据
        from src.ppt_compiler import save_pptx_with_metadata
        result = save_pptx_with_metadata(
            pptx_bytes,
            metadata,
            presentation_id,
            mock_s3_bucket,
            bucket_name
        )

        # Then: 验证元数据保存
        metadata_key = f"presentations/{presentation_id}/metadata.json"
        metadata_obj = mock_s3_bucket.get_object(Bucket=bucket_name, Key=metadata_key)
        saved_metadata = json.loads(metadata_obj["Body"].read().decode())
        assert saved_metadata["file_size"] == len(pptx_bytes)
        assert saved_metadata["slide_count"] == 5


class TestPPTXValidation:
    """PPTX文件验证测试"""

    @pytest.mark.unit
    def test_validate_pptx_file_integrity(self):
        """
        测试PPTX文件完整性验证
        验收标准：生成的文件应为有效的PPTX格式
        """
        # Given: 有效和无效的PPTX数据
        valid_pptx = b"PK\x03\x04"  # ZIP文件头
        invalid_pptx = b"invalid data"

        # When: 验证文件完整性
        from src.ppt_validator import validate_pptx_integrity
        # 为了通过测试，我们需要实际的PPTX内容
        from src.ppt_compiler import create_pptx_from_content

        # 创建一个真实的PPTX用于测试
        test_content = {"slides": [{"title": "测试", "bullet_points": ["测试要点"]}]}
        real_pptx = create_pptx_from_content(test_content)

        valid_result = validate_pptx_integrity(real_pptx)
        invalid_result = validate_pptx_integrity(invalid_pptx)

        # Then: 验证结果
        assert valid_result
        assert not invalid_result

    @pytest.mark.unit
    def test_validate_slide_content_completeness(self, sample_slide_content):
        """
        测试幻灯片内容完整性验证
        验收标准：所有输入的内容都应在生成的PPT中
        """
        # Given: 输入内容
        input_content = sample_slide_content

        # 模拟生成的PPTX
        mock_pptx_bytes = b"fake pptx with content"

        # When: 验证内容完整性
        from src.ppt_validator import validate_content_completeness
        from src.ppt_compiler import create_pptx_from_content

        # 使用真实的PPTX文件进行测试
        real_pptx_bytes = create_pptx_from_content(input_content)
        is_complete = validate_content_completeness(input_content, real_pptx_bytes)

        # Then: 验证结果
        assert is_complete

    @pytest.mark.unit
    def test_validate_pptx_accessibility(self):
        """
        测试PPTX可访问性验证
        验收标准：生成的PPT应符合基本的可访问性标准
        """
        # Given: 生成的PPTX文件
        mock_pptx_bytes = b"fake pptx content"

        # When: 验证可访问性（预期失败）
        with pytest.raises(ImportError):
            from src.ppt_validator import validate_accessibility
            accessibility_score = validate_accessibility(mock_pptx_bytes)

        # Then: 验证可访问性得分（实现后启用）
        # assert accessibility_score >= 0.8  # 80%以上的可访问性得分

    @pytest.mark.unit
    def test_validate_file_size_limits(self):
        """
        测试文件大小限制验证
        验收标准：生成的PPT文件大小应在合理范围内
        """
        # Given: 不同大小的文件
        small_file = b"x" * (100 * 1024)  # 100KB
        large_file = b"x" * (50 * 1024 * 1024)  # 50MB
        huge_file = b"x" * (200 * 1024 * 1024)  # 200MB

        # When: 验证文件大小（预期失败）
        with pytest.raises(ImportError):
            from src.ppt_validator import validate_file_size
            small_valid = validate_file_size(small_file)
            large_valid = validate_file_size(large_file)
            huge_valid = validate_file_size(huge_file)

        # Then: 验证大小限制（实现后启用）
        # assert small_valid
        # assert large_valid
        # assert not huge_valid  # 200MB应该超过限制


class TestPPTCompilerPerformance:
    """PPT编译性能测试"""

    @pytest.mark.slow
    @pytest.mark.performance
    def test_large_presentation_generation(self, performance_thresholds):
        """
        测试大型演示文稿生成性能
        验收标准：20页PPT应在合理时间内生成完成
        """
        import time

        # Given: 大型演示文稿内容
        large_content = {
            "presentation_id": "large-test",
            "slides": [
                {
                    "slide_number": i + 1,
                    "title": f"幻灯片 {i + 1}",
                    "bullet_points": [f"要点{i + 1}.{j + 1}" for j in range(5)]
                } for i in range(20)
            ]
        }

        # When: 生成大型PPT并计时（预期失败）
        start_time = time.time()

        with pytest.raises(ImportError):
            from src.ppt_compiler import create_pptx_from_content
            pptx_bytes = create_pptx_from_content(large_content)

        generation_time = time.time() - start_time

        # Then: 验证生成时间（实现后启用）
        max_generation_time = performance_thresholds["max_generation_time"]
        # assert generation_time < max_generation_time
        # assert len(pptx_bytes) > 10000  # 应该有合理的文件大小

    @pytest.mark.slow
    @pytest.mark.performance
    def test_concurrent_ppt_generation(self, performance_thresholds):
        """
        测试并发PPT生成性能
        验收标准：多个PPT并发生成不应超过时间限制
        """
        import time
        import concurrent.futures

        # Given: 多个演示文稿内容
        presentations = [
            {
                "presentation_id": f"concurrent-test-{i}",
                "slides": [
                    {
                        "title": f"演示文稿{i} - 幻灯片{j}",
                        "bullet_points": [f"要点{j}.1", f"要点{j}.2"]
                    } for j in range(5)
                ]
            } for i in range(5)
        ]

        # When: 并发生成PPT（预期失败）
        start_time = time.time()

        with pytest.raises(ImportError):
            from src.ppt_compiler import create_pptx_from_content

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(create_pptx_from_content, content)
                    for content in presentations
                ]
                results = [future.result() for future in futures]

        total_time = time.time() - start_time

        # Then: 验证并发性能（实现后启用）
        max_concurrent_time = performance_thresholds["max_generation_time"] * 2
        # assert total_time < max_concurrent_time
        # assert len(results) == len(presentations)

    @pytest.mark.performance
    def test_memory_usage_during_compilation(self):
        """
        测试PPT编译过程中的内存使用
        验收标准：编译过程中内存使用应保持稳定
        """
        import psutil
        import os

        # Given: 内容和内存监控
        content = {
            "slides": [
                {
                    "title": f"幻灯片 {i}",
                    "bullet_points": [f"要点{i}.{j}" for j in range(10)]
                } for i in range(15)
            ]
        }

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # When: 生成PPT并监控内存（预期失败）
        with pytest.raises(ImportError):
            from src.ppt_compiler import create_pptx_from_content
            pptx_bytes = create_pptx_from_content(content)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Then: 验证内存使用（实现后启用）
        max_memory_increase = 100  # MB
        # assert memory_increase < max_memory_increase


class TestErrorHandling:
    """PPT编译错误处理测试"""

    @pytest.mark.unit
    def test_invalid_content_format_handling(self):
        """
        测试无效内容格式处理
        验收标准：应优雅处理无效或损坏的输入内容
        """
        # Given: 无效的内容格式
        invalid_contents = [
            None,
            {},
            {"invalid": "format"},
            {"slides": []},  # 空幻灯片
            {"slides": [{"no_title": "test"}]}  # 缺少必需字段
        ]

        for invalid_content in invalid_contents:
            # When: 尝试生成PPT（预期失败）
            with pytest.raises(ImportError):  # 实现后应该是ValueError
                from src.ppt_compiler import create_pptx_from_content
                pptx_bytes = create_pptx_from_content(invalid_content)

    @pytest.mark.unit
    def test_s3_upload_failure_handling(self, mock_s3_bucket):
        """
        测试S3上传失败处理
        验收标准：S3上传失败时应提供有用的错误信息
        """
        from botocore.exceptions import ClientError

        # Given: S3客户端会失败
        mock_s3_bucket.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "PutObject"
        )

        # When: 尝试保存到S3（预期失败）
        with pytest.raises(ImportError):  # 实现后应该是ClientError
            from src.ppt_compiler import save_pptx_to_s3
            s3_key = save_pptx_to_s3(
                b"fake content",
                "test-123",
                mock_s3_bucket,
                "nonexistent-bucket"
            )

    @pytest.mark.unit
    def test_template_loading_failure(self):
        """
        测试模板加载失败处理
        验收标准：模板不可用时应使用默认模板或提供错误信息
        """
        # Given: 不存在的模板名称
        content = {"slides": [{"title": "测试", "bullet_points": ["要点1"]}]}

        # When: 使用不存在的模板（预期失败）
        with pytest.raises(ImportError):  # 实现后应该是FileNotFoundError或自定义异常
            from src.ppt_compiler import create_pptx_with_template
            pptx_bytes = create_pptx_with_template(content, template_name="nonexistent_template")


if __name__ == "__main__":
    # 运行测试的快速方法
    pytest.main([__file__, "-v", "-m", "not slow"])