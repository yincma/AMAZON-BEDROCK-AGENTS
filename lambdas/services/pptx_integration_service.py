"""
PPTX集成服务
将演讲者备注集成到PowerPoint文件中
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PPTXIntegrationService:
    """PPTX集成服务类"""

    def __init__(self):
        """初始化服务"""
        pass

    def add_speaker_notes_to_slide(self, presentation, slide_index: int, speaker_notes: str):
        """
        将演讲者备注添加到指定幻灯片

        Args:
            presentation: python-pptx的Presentation对象
            slide_index: 幻灯片索引 (从0开始)
            speaker_notes: 演讲者备注内容
        """
        try:
            # 获取指定的幻灯片
            slide = presentation.slides[slide_index]

            # 确保幻灯片有notes slide
            if not slide.has_notes_slide:
                # 创建notes slide
                slide.notes_slide

            # 设置演讲者备注文本
            slide.notes_slide.notes_text_frame.text = speaker_notes

            logger.info(f"成功添加演讲者备注到幻灯片 {slide_index + 1}")

        except IndexError:
            logger.error(f"幻灯片索引 {slide_index} 超出范围")
            raise ValueError(f"幻灯片索引 {slide_index} 不存在")
        except Exception as e:
            logger.error(f"添加演讲者备注失败: {str(e)}")
            raise

    def add_notes_to_all_slides(self, presentation, notes_list: list):
        """
        为所有幻灯片批量添加演讲者备注

        Args:
            presentation: python-pptx的Presentation对象
            notes_list: 演讲者备注列表，与幻灯片一一对应
        """
        try:
            # 确保备注数量与幻灯片数量匹配
            slide_count = len(presentation.slides)
            notes_count = len(notes_list)

            if notes_count != slide_count:
                logger.warning(f"备注数量({notes_count})与幻灯片数量({slide_count})不匹配")

            # 添加备注到每张幻灯片
            for i, notes in enumerate(notes_list):
                if i < slide_count:
                    self.add_speaker_notes_to_slide(presentation, i, notes)
                else:
                    break

            logger.info(f"成功为 {min(notes_count, slide_count)} 张幻灯片添加演讲者备注")

        except Exception as e:
            logger.error(f"批量添加演讲者备注失败: {str(e)}")
            raise

    def get_speaker_notes_from_slide(self, presentation, slide_index: int) -> Optional[str]:
        """
        获取指定幻灯片的演讲者备注

        Args:
            presentation: python-pptx的Presentation对象
            slide_index: 幻灯片索引

        Returns:
            str: 演讲者备注内容，如果没有则返回None
        """
        try:
            slide = presentation.slides[slide_index]

            if slide.has_notes_slide:
                return slide.notes_slide.notes_text_frame.text
            else:
                return None

        except IndexError:
            logger.error(f"幻灯片索引 {slide_index} 超出范围")
            return None
        except Exception as e:
            logger.error(f"获取演讲者备注失败: {str(e)}")
            return None

    def update_speaker_notes(self, presentation, slide_index: int, new_notes: str):
        """
        更新指定幻灯片的演讲者备注

        Args:
            presentation: python-pptx的Presentation对象
            slide_index: 幻灯片索引
            new_notes: 新的演讲者备注内容
        """
        # 直接调用add方法，它会覆盖现有内容
        self.add_speaker_notes_to_slide(presentation, slide_index, new_notes)

    def clear_all_speaker_notes(self, presentation):
        """
        清除所有幻灯片的演讲者备注

        Args:
            presentation: python-pptx的Presentation对象
        """
        try:
            for i, slide in enumerate(presentation.slides):
                if slide.has_notes_slide:
                    slide.notes_slide.notes_text_frame.text = ""

            logger.info("已清除所有演讲者备注")

        except Exception as e:
            logger.error(f"清除演讲者备注失败: {str(e)}")
            raise

    def has_speaker_notes(self, presentation, slide_index: int) -> bool:
        """
        检查指定幻灯片是否有演讲者备注

        Args:
            presentation: python-pptx的Presentation对象
            slide_index: 幻灯片索引

        Returns:
            bool: 是否有演讲者备注
        """
        notes = self.get_speaker_notes_from_slide(presentation, slide_index)
        return notes is not None and len(notes.strip()) > 0