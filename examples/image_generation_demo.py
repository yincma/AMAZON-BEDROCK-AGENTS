#!/usr/bin/env python3
"""
图片生成服务演示脚本

此脚本演示如何使用ImageProcessingService生成AI图片，
包括基本用法、缓存功能和错误处理。
"""

import os
import sys
import time
import logging
from PIL import Image
import io

# 添加lambdas目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service import ImageProcessingService
from image_exceptions import NovaServiceError, ImageProcessingError


def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 启用调试日志查看缓存行为
    logging.getLogger('lambdas.image_processing_service').setLevel(logging.DEBUG)


def demo_basic_usage():
    """演示基本用法"""
    print("\n=== 基本用法演示 ===")

    # 创建服务实例
    service = ImageProcessingService(enable_caching=True)

    # 定义幻灯片内容
    slide_content = {
        "title": "人工智能技术发展",
        "content": [
            "机器学习算法优化",
            "深度学习模型训练",
            "自然语言处理应用",
            "计算机视觉技术"
        ]
    }

    try:
        # 生成提示词
        prompt = service.generate_prompt(slide_content, "business")
        print(f"生成的提示词: {prompt}")

        # 生成图片
        print("正在生成图片...")
        start_time = time.time()

        image_data = service.call_image_generation(prompt)

        generation_time = time.time() - start_time
        print(f"图片生成完成! 耗时: {generation_time:.2f}秒")
        print(f"图片大小: {len(image_data)} 字节")

        # 保存图片
        output_path = "demo_ai_technology.png"
        with open(output_path, "wb") as f:
            f.write(image_data)

        # 验证图片
        image = Image.open(io.BytesIO(image_data))
        print(f"图片信息: {image.width}x{image.height}, 格式: {image.format}")
        print(f"图片已保存到: {output_path}")

    except Exception as e:
        print(f"生成失败: {str(e)}")


def demo_different_audiences():
    """演示不同受众类型的图片生成"""
    print("\n=== 不同受众风格演示 ===")

    service = ImageProcessingService(enable_caching=True)

    # 基础内容
    slide_content = {
        "title": "数据分析报告",
        "content": ["市场趋势分析", "用户行为研究", "业务增长预测"]
    }

    audiences = {
        "business": "商务专业风格",
        "academic": "学术严谨风格",
        "creative": "创意艺术风格",
        "technical": "技术文档风格"
    }

    for audience_type, description in audiences.items():
        try:
            print(f"\n生成 {description} 图片...")

            # 生成提示词
            prompt = service.generate_prompt(slide_content, audience_type)
            print(f"提示词: {prompt[:100]}...")

            # 生成图片
            start_time = time.time()
            image_data = service.call_image_generation(prompt)
            generation_time = time.time() - start_time

            # 保存图片
            output_path = f"demo_{audience_type}_style.png"
            with open(output_path, "wb") as f:
                f.write(image_data)

            print(f"  ✓ 生成成功: {generation_time:.2f}秒, 保存到 {output_path}")

        except Exception as e:
            print(f"  ✗ 生成失败: {str(e)}")


def demo_cache_functionality():
    """演示缓存功能"""
    print("\n=== 缓存功能演示 ===")

    service = ImageProcessingService(enable_caching=True)
    prompt = "现代商务办公环境，简洁专业设计风格，高质量4K分辨率"

    # 第一次调用（应该调用API）
    print("第一次调用（无缓存）...")
    start_time = time.time()
    image_data_1 = service.call_image_generation(prompt)
    first_call_time = time.time() - start_time

    print(f"第一次调用耗时: {first_call_time:.2f}秒")

    # 检查缓存状态
    stats = service.get_cache_stats()
    print(f"缓存统计: {stats}")

    # 第二次调用（应该使用缓存）
    print("\n第二次调用（使用缓存）...")
    start_time = time.time()
    image_data_2 = service.call_image_generation(prompt)
    second_call_time = time.time() - start_time

    print(f"第二次调用耗时: {second_call_time:.2f}秒")

    # 验证缓存效果
    if image_data_1 == image_data_2:
        print("✓ 缓存工作正常 - 两次调用返回相同数据")
        if second_call_time < first_call_time:
            speed_up = first_call_time / second_call_time
            print(f"✓ 速度提升: {speed_up:.1f}倍")
    else:
        print("✗ 缓存可能未工作 - 两次调用返回不同数据")

    # 更新缓存统计
    stats = service.get_cache_stats()
    print(f"更新后缓存统计: {stats}")


def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")

    service = ImageProcessingService(enable_caching=False)

    # 测试各种边界情况
    test_cases = [
        ("空提示词", ""),
        ("过长提示词", "非常长的提示词" * 50),
        ("特殊字符", "测试!@#$%^&*()图片生成"),
        ("正常提示词", "专业商务图表，现代设计风格")
    ]

    for case_name, prompt in test_cases:
        try:
            print(f"\n测试 {case_name}...")
            image_data = service.call_image_generation(prompt)

            # 验证返回的数据
            if image_data and len(image_data) > 0:
                image = Image.open(io.BytesIO(image_data))
                print(f"  ✓ 成功: 返回 {image.width}x{image.height} {image.format} 图片")
            else:
                print("  ✗ 失败: 无有效图片数据")

        except NovaServiceError as e:
            print(f"  ⚠ Nova服务错误: {str(e)}")
        except ImageProcessingError as e:
            print(f"  ⚠ 图片处理错误: {str(e)}")
        except Exception as e:
            print(f"  ✗ 未知错误: {str(e)}")


def demo_model_fallback():
    """演示模型fallback机制"""
    print("\n=== 模型Fallback演示 ===")

    service = ImageProcessingService(enable_caching=False)

    print("支持的模型列表:")
    for i, model in enumerate(service.supported_models, 1):
        print(f"  {i}. {model}")

    # 测试无效模型（触发fallback）
    prompt = "科技感强烈的未来城市背景"

    try:
        print(f"\n使用无效模型首选项生成图片...")
        image_data = service.call_image_generation(
            prompt,
            model_preference="invalid-model-id"
        )

        if image_data and len(image_data) > 0:
            print("✓ Fallback机制工作正常 - 成功生成图片")
        else:
            print("✗ Fallback失败")

    except Exception as e:
        print(f"✗ Fallback机制失败: {str(e)}")


def demo_performance_benchmark():
    """演示性能基准测试"""
    print("\n=== 性能基准测试 ===")

    service = ImageProcessingService(enable_caching=False)  # 禁用缓存获取真实性能

    test_prompts = [
        "简单商务背景",
        "复杂的数据可视化图表，包含多个维度的统计分析结果",
        "高质量科技感未来主义设计，包含抽象几何元素和现代配色方案"
    ]

    results = []

    for i, prompt in enumerate(test_prompts, 1):
        try:
            print(f"\n测试 {i}/3: 提示词长度 {len(prompt)} 字符")
            print(f"提示词: {prompt}")

            start_time = time.time()
            image_data = service.call_image_generation(prompt)
            generation_time = time.time() - start_time

            if image_data:
                image = Image.open(io.BytesIO(image_data))
                results.append({
                    'prompt_length': len(prompt),
                    'generation_time': generation_time,
                    'image_size': len(image_data),
                    'resolution': f"{image.width}x{image.height}"
                })

                print(f"  ✓ 成功: {generation_time:.2f}秒")
                print(f"  图片: {image.width}x{image.height}, {len(image_data)} 字节")
            else:
                print(f"  ✗ 生成失败")

        except Exception as e:
            print(f"  ✗ 错误: {str(e)}")

    # 分析结果
    if results:
        print(f"\n=== 性能分析 ===")
        avg_time = sum(r['generation_time'] for r in results) / len(results)
        avg_size = sum(r['image_size'] for r in results) / len(results)

        print(f"平均生成时间: {avg_time:.2f}秒")
        print(f"平均图片大小: {avg_size/1024:.1f} KB")

        # 性能评估
        if avg_time < 10:
            print("✓ 性能评级: 优秀")
        elif avg_time < 20:
            print("⚠ 性能评级: 良好")
        else:
            print("⚠ 性能评级: 需要优化")


def main():
    """主函数"""
    print("🎨 图片生成服务演示")
    print("=" * 50)

    # 设置日志
    setup_logging()

    # 创建输出目录
    os.makedirs("demo_output", exist_ok=True)
    os.chdir("demo_output")

    try:
        # 运行各种演示
        demo_basic_usage()
        demo_different_audiences()
        demo_cache_functionality()
        demo_error_handling()
        demo_model_fallback()
        demo_performance_benchmark()

        print("\n" + "=" * 50)
        print("🎉 演示完成! 检查当前目录中的生成图片。")

    except KeyboardInterrupt:
        print("\n\n⚠ 演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中出现错误: {str(e)}")
    finally:
        print("\n感谢使用图片生成服务演示!")


if __name__ == "__main__":
    main()