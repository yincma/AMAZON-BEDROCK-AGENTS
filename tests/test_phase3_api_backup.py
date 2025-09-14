"""
Phase 3 API集成测试
测试新增的API端点功能
"""

import json
import pytest
import requests
import uuid
import time
from typing import Dict, Any
import responses
from test_utils import MockAPIGateway, TestDataFactory, assert_response_structure


class TestPhase3API:
    """Phase 3 API测试套件"""

    # 测试配置
    BASE_URL = "https://api.ai-ppt-assistant.com/v2"
    API_KEY = "test-api-key"
    TEST_PRESENTATION_ID = "test-ppt-123"

    @pytest.fixture(autouse=True)
    def setup_responses(self):
        """设置HTTP Mock响应"""
        with MockAPIGateway.setup_responses() as rsps:
            # 添加额外的响应配置
            MockAPIGateway.add_etag_responses(rsps)
            MockAPIGateway.add_image_generation_responses(rsps)
            MockAPIGateway.add_regeneration_responses(rsps)
            MockAPIGateway.add_validation_error_responses(rsps)
            MockAPIGateway.add_rate_limiting_responses(rsps)
            yield rsps

    @pytest.fixture
    def test_presentation_id(self):
        """测试演示文稿ID"""
        return self.TEST_PRESENTATION_ID

    @classmethod
    def _get_headers(cls) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-API-Key": cls.API_KEY,
            "Content-Type": "application/json"
        }

    def _wait_for_completion(self, presentation_id: str, timeout: int = 60):
        """模拟等待演示文稿生成完成"""
        # 在测试环境中，立即返回完成状态
        response = requests.get(
            f"{self.BASE_URL}/presentations/{presentation_id}/status",
            headers=self._get_headers()
        )
        return response.status_code == 200

    def test_update_slide_content(self):
        """测试更新幻灯片内容"""
        # 更新第2页幻灯片
        response = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/2",
            headers=self._get_headers(),
            json={
                "title": "Updated Slide Title",
                "content": "This is the updated content for slide 2",
                "speaker_notes": "Remember to emphasize this point",
                "layout": "two_column"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["presentation_id"] == self.TEST_PRESENTATION_ID
        assert data["slide_number"] == 2
        assert "etag" in data
        assert "updated_at" in data
        assert "preview_url" in data

    def test_update_slide_with_etag(self):
        """测试使用ETag的乐观锁更新"""
        # 第一次更新获取ETag
        response1 = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/3",
            headers=self._get_headers(),
            json={"title": "First Update"}
        )
        assert response1.status_code == 200
        etag1 = response1.json()["etag"]

        # 使用正确的ETag更新
        headers = self._get_headers()
        headers["If-Match"] = etag1
        response2 = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/3",
            headers=headers,
            json={"title": "Second Update"}
        )
        assert response2.status_code == 200
        etag2 = response2.json()["etag"]
        assert etag1 != etag2

        # 使用过期的ETag更新（应该失败）
        headers["If-Match"] = etag1
        response3 = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/3",
            headers=headers,
            json={"title": "Third Update"}
        )
        assert response3.status_code == 412  # Precondition Failed

    def test_regenerate_slide_image(self):
        """测试重新生成幻灯片图片"""
        response = requests.post(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/1/image",
            headers=self._get_headers(),
            json={
                "prompt": "A futuristic technology concept with blue and purple gradients",
                "style": "abstract",
                "dimensions": {
                    "width": 1920,
                    "height": 1080
                }
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "processing"]
        assert "estimated_time" in data
        assert "status_url" in data

    def test_regenerate_presentation_slides(self):
        """测试重新生成指定幻灯片"""
        response = requests.post(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/regenerate",
            headers=self._get_headers(),
            json={
                "scope": "slides",
                "slide_numbers": [2, 4],
                "options": {
                    "preserve_style": True,
                    "preserve_images": False
                }
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["scope"] == "slides"
        assert data["affected_slides"] == [2, 4]
        assert "status_url" in data

    def test_regenerate_all_images(self):
        """测试重新生成所有图片"""
        response = requests.post(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/regenerate",
            headers=self._get_headers(),
            json={
                "scope": "images",
                "options": {
                    "new_prompt": "Modern minimalist style with geometric shapes"
                }
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert data["scope"] == "images"

    def test_delete_presentation(self):
        """测试删除演示文稿"""
        # 创建一个新的演示文稿用于删除测试
        create_response = requests.post(
            f"{self.BASE_URL}/presentations/generate",
            headers=self._get_headers(),
            json={
                "topic": "Temporary Presentation",
                "page_count": 3
            }
        )
        temp_id = create_response.json()["presentation_id"]

        # 等待生成完成
        self._wait_for_completion(temp_id)

        # 删除演示文稿
        delete_response = requests.delete(
            f"{self.BASE_URL}/presentations/{temp_id}",
            headers=self._get_headers()
        )
        assert delete_response.status_code == 204

        # 验证删除后无法访问
        status_response = requests.get(
            f"{self.BASE_URL}/presentations/{temp_id}/status",
            headers=self._get_headers()
        )
        assert status_response.status_code == 404

    def test_force_delete_processing_presentation(self):
        """测试强制删除处理中的演示文稿"""
        # 创建一个新的演示文稿
        create_response = requests.post(
            f"{self.BASE_URL}/presentations/generate",
            headers=self._get_headers(),
            json={
                "topic": "Processing Presentation",
                "page_count": 10
            }
        )
        temp_id = create_response.json()["presentation_id"]

        # 立即尝试删除（可能还在处理中）
        delete_response = requests.delete(
            f"{self.BASE_URL}/presentations/{temp_id}",
            headers=self._get_headers()
        )

        if delete_response.status_code == 409:
            # 如果冲突，使用强制删除
            force_delete_response = requests.delete(
                f"{self.BASE_URL}/presentations/{temp_id}",
                headers=self._get_headers(),
                params={"force": "true"}
            )
            assert force_delete_response.status_code == 204

    def test_validation_errors(self):
        """测试各种验证错误"""
        # 无效的演示文稿ID
        response = requests.patch(
            f"{self.BASE_URL}/presentations/invalid-id/slides/1",
            headers=self._get_headers(),
            json={"title": "Test"}
        )
        assert response.status_code == 400

        # 无效的幻灯片编号
        response = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/999",
            headers=self._get_headers(),
            json={"title": "Test"}
        )
        assert response.status_code == 400

        # 空请求体
        response = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/1",
            headers=self._get_headers(),
            json={}
        )
        assert response.status_code == 400

        # 超长内容
        response = requests.patch(
            f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/1",
            headers=self._get_headers(),
            json={"content": "x" * 3000}  # 超过2000字符限制
        )
        assert response.status_code == 400

    def test_concurrent_updates(self):
        """测试并发更新控制"""
        import threading
        results = []

        def update_slide(slide_num: int):
            try:
                response = requests.patch(
                    f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/{slide_num}",
                    headers=self._get_headers(),
                    json={"title": f"Concurrent Update {slide_num}"}
                )
                results.append((slide_num, response.status_code))
            except Exception as e:
                results.append((slide_num, str(e)))

        # 创建多个线程同时更新不同幻灯片
        threads = []
        for i in range(1, 4):
            thread = threading.Thread(target=update_slide, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有更新都成功
        for slide_num, status in results:
            assert status == 200, f"Slide {slide_num} update failed with status {status}"

    def test_rate_limiting(self):
        """测试API限流"""
        # 快速发送多个请求
        responses = []
        for i in range(20):
            response = requests.patch(
                f"{self.BASE_URL}/presentations/{self.TEST_PRESENTATION_ID}/slides/1",
                headers=self._get_headers(),
                json={"title": f"Rate Test {i}"}
            )
            responses.append(response.status_code)

            if response.status_code == 429:
                # 检查限流响应头
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers

                # 检查响应体
                data = response.json()
                assert data["error"] == "RATE_LIMITED"
                assert "retry_after" in data
                break

    def test_health_check(self):
        """测试健康检查端点"""
        response = requests.get(f"{self.BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])