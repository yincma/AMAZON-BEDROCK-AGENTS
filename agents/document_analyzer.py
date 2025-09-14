"""
Document Analyzer Agent - 文档分析器
负责解析文档、提取关键内容、生成PPT大纲
"""
import json
import re
from typing import Dict, Any, List
import boto3
from botocore.config import Config
import PyPDF2
from io import BytesIO

# 统一使用的模型
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"  # inference profile


class DocumentAnalyzerAgent:
    """文档分析Agent"""

    def __init__(self):
        """初始化Document Analyzer Agent"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            config=Config(read_timeout=30, retries={'max_attempts': 3})
        )
        self.s3_client = boto3.client('s3')
        self.textract_client = boto3.client('textract', region_name='us-east-1')

    def parse_document(self, document_path: str) -> Dict[str, Any]:
        """
        解析文档

        Args:
            document_path: S3文档路径

        Returns:
            解析结果
        """
        # 解析S3路径
        bucket, key = self._parse_s3_path(document_path)

        # 根据文件类型选择解析方法
        if key.endswith('.pdf'):
            content = self._extract_pdf_content(bucket, key)
        elif key.endswith('.docx'):
            content = self._extract_docx_content(bucket, key)
        else:
            content = self._extract_text_content(bucket, key)

        # 分析文档结构
        result = {
            "total_pages": content.get("pages", 1),
            "chart_count": content.get("charts", 0),
            "text_content": content.get("text", ""),
            "document_type": self._detect_document_type(content.get("text", "")),
            "outline": self._generate_outline_from_content(content)
        }

        return result

    def extract_key_points(self, content: str) -> List[Dict[str, Any]]:
        """
        提取关键点

        Args:
            content: 文档内容

        Returns:
            关键点列表
        """
        # 识别章节结构
        chapters = self._identify_chapters(content)

        key_points = []
        for chapter in chapters:
            # 使用Bedrock提取每章的关键内容
            prompt = f"""
            请从以下章节中提取最重要的3-5个关键点：

            {chapter['content'][:1000]}

            要求：
            1. 每个关键点不超过50字
            2. 保留核心信息
            3. 适合在PPT中展示

            返回JSON格式：{{"points": ["point1", "point2", ...]}}
            """

            response = self._call_bedrock(prompt)
            try:
                points_data = json.loads(response)
                key_points.append({
                    "title": chapter['title'],
                    "关键内容": points_data.get("points", [])
                })
            except:
                # 如果解析失败，使用简单提取
                key_points.append({
                    "title": chapter['title'],
                    "关键内容": self._simple_extract(chapter['content'])
                })

        return key_points

    def generate_outline(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成PPT大纲

        Args:
            analysis: 文档分析结果

        Returns:
            PPT大纲
        """
        key_points = analysis.get("key_points", [])
        suggested_pages = analysis.get("suggested_pages", 8)

        # 构建大纲
        outline = {
            "page_count": suggested_pages,
            "slides": []
        }

        # 添加标题页
        outline["slides"].append({
            "page_number": 1,
            "type": "title",
            "title": self._extract_title(analysis),
            "subtitle": "自动生成的演示文稿"
        })

        # 添加内容页
        page_num = 2
        for point in key_points[:suggested_pages-2]:  # 留出标题页和结论页
            outline["slides"].append({
                "page_number": page_num,
                "type": "content",
                "title": point["title"],
                "key_points": point.get("关键内容", [])
            })
            page_num += 1

        # 添加结论页
        outline["slides"].append({
            "page_number": page_num,
            "type": "conclusion",
            "title": "总结",
            "key_points": self._generate_conclusion(key_points)
        })

        return outline

    def _parse_s3_path(self, s3_path: str) -> tuple:
        """解析S3路径"""
        # s3://bucket/key -> (bucket, key)
        path = s3_path.replace("s3://", "")
        parts = path.split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

    def _extract_pdf_content(self, bucket: str, key: str) -> Dict[str, Any]:
        """提取PDF内容"""
        try:
            # 从S3下载PDF
            obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            pdf_content = obj['Body'].read()

            # 使用PyPDF2解析
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()

            return {
                "text": text,
                "pages": len(pdf_reader.pages),
                "charts": self._count_charts_in_text(text)
            }
        except:
            # 如果PyPDF2失败，使用Textract
            return self._extract_with_textract(bucket, key)

    def _extract_docx_content(self, bucket: str, key: str) -> Dict[str, Any]:
        """提取Word文档内容"""
        # 使用Textract处理Word文档
        return self._extract_with_textract(bucket, key)

    def _extract_text_content(self, bucket: str, key: str) -> Dict[str, Any]:
        """提取文本内容"""
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        text = obj['Body'].read().decode('utf-8')
        return {
            "text": text,
            "pages": 1,
            "charts": 0
        }

    def _extract_with_textract(self, bucket: str, key: str) -> Dict[str, Any]:
        """使用Textract提取内容"""
        try:
            response = self.textract_client.detect_document_text(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}}
            )

            text = ""
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text += block.get('Text', '') + "\n"

            return {
                "text": text,
                "pages": 1,
                "charts": 0
            }
        except:
            return {"text": "", "pages": 1, "charts": 0}

    def _identify_chapters(self, content: str) -> List[Dict[str, str]]:
        """识别章节结构"""
        chapters = []

        # 尝试识别常见的章节标记
        patterns = [
            r"第[一二三四五六七八九十\d]+章[：\s]*(.*?)(?=第[一二三四五六七八九十\d]+章|$)",
            r"Chapter\s+\d+[：\s]*(.*?)(?=Chapter\s+\d+|$)",
            r"\d+\.\s*(.*?)(?=\d+\.|$)",
            r"##\s*(.*?)(?=##|$)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                for i, match in enumerate(matches):
                    if isinstance(match, tuple):
                        title = match[0].strip()[:100]
                        content_text = match[1] if len(match) > 1 else ""
                    else:
                        title = f"章节 {i+1}"
                        content_text = match

                    chapters.append({
                        "title": title,
                        "content": content_text[:2000]  # 限制长度
                    })
                break

        # 如果没有识别到章节，按段落分割
        if not chapters:
            paragraphs = content.split("\n\n")
            for i, para in enumerate(paragraphs[:10]):  # 最多10个段落
                if len(para) > 50:
                    chapters.append({
                        "title": f"段落 {i+1}",
                        "content": para[:1000]
                    })

        return chapters

    def _detect_document_type(self, text: str) -> str:
        """检测文档类型"""
        text_lower = text.lower()

        if "report" in text_lower or "报告" in text:
            return "report"
        elif "proposal" in text_lower or "提案" in text:
            return "proposal"
        elif "analysis" in text_lower or "分析" in text:
            return "analysis"
        else:
            return "general"

    def _generate_outline_from_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """从内容生成大纲"""
        text = content.get("text", "")
        pages = content.get("pages", 1)

        # 计算建议的PPT页数（不超过原文档的20%）
        suggested_pages = min(max(5, pages // 5), 10)

        return {
            "slides": [],
            "suggested_pages": suggested_pages
        }

    def _count_charts_in_text(self, text: str) -> int:
        """统计文本中的图表数量"""
        chart_keywords = ["图", "表", "chart", "table", "figure", "graph"]
        count = 0
        for keyword in chart_keywords:
            count += text.lower().count(keyword)
        return min(count, 10)  # 最多返回10

    def _simple_extract(self, content: str) -> List[str]:
        """简单提取关键点"""
        sentences = content.split("。")
        key_points = []
        for sentence in sentences[:5]:
            if len(sentence) > 10:
                key_points.append(sentence.strip() + "。")
        return key_points

    def _extract_title(self, analysis: Dict[str, Any]) -> str:
        """提取标题"""
        if "key_points" in analysis and analysis["key_points"]:
            return analysis["key_points"][0].get("title", "演示文稿")
        return "演示文稿"

    def _generate_conclusion(self, key_points: List[Dict[str, Any]]) -> List[str]:
        """生成结论要点"""
        conclusions = []
        for point in key_points[:3]:
            if "关键内容" in point and point["关键内容"]:
                conclusions.append(f"关于{point['title']}的要点")

        if not conclusions:
            conclusions = ["主要内容总结", "关键发现", "下一步计划"]

        return conclusions

    def _call_bedrock(self, prompt: str) -> str:
        """调用Bedrock模型"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )

            result = json.loads(response['body'].read())
            return result.get("content", [{}])[0].get("text", "")
        except Exception as e:
            print(f"Bedrock调用失败: {e}")
            return "{}"


def extract_pdf_content(path: str) -> Dict[str, Any]:
    """辅助函数：提取PDF内容（用于测试mock）"""
    analyzer = DocumentAnalyzerAgent()
    bucket, key = analyzer._parse_s3_path(path)
    return analyzer._extract_pdf_content(bucket, key)