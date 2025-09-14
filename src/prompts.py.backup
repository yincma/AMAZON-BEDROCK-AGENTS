"""
提示词模板 - 用于生成PPT内容的Bedrock Claude提示词
"""

OUTLINE_PROMPT = """你是一个专业的演示文稿制作专家。请为以下主题创建一个{page_count}页的PPT大纲：

主题：{topic}

要求：
1. 第1页必须是标题页
2. 最后一页必须是总结页
3. 中间页面逻辑清晰，循序渐进
4. 每页都要有明确的主题

请以JSON格式返回大纲，格式如下：
{{
  "title": "{topic}",
  "slides": [
    {{
      "slide_number": 1,
      "title": "页面标题",
      "content": ["要点1", "要点2", "要点3"]
    }}
  ],
  "metadata": {{
    "total_slides": {page_count},
    "estimated_duration": "10-15分钟",
    "created_at": "时间戳"
  }}
}}

请确保JSON格式正确，可以直接解析。"""

CONTENT_PROMPT = """为以下PPT页面生成详细内容：

页面标题：{page_title}
页面目的：{page_purpose}
演示文稿主题：{topic}

要求：
1. 生成1个主标题
2. 生成3个核心要点，每个要点简洁明了（20-200字符）
3. 内容专业且易于理解
4. 生成演讲者备注（提供演讲提示）

请以JSON格式返回：
{{
  "slide_number": {slide_number},
  "title": "{page_title}",
  "bullet_points": ["要点1", "要点2", "要点3"],
  "speaker_notes": "演讲备注内容"
}}

请确保JSON格式正确，可以直接解析。"""