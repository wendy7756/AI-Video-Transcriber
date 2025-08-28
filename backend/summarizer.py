import os
import openai
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Summarizer:
    """文本总结器，使用OpenAI API生成多语言摘要"""
    
    def __init__(self):
        """初始化总结器"""
        # 从环境变量获取OpenAI API配置
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if not api_key:
            logger.warning("未设置OPENAI_API_KEY环境变量，将无法使用摘要功能")
        
        if api_key:
            if base_url:
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
                logger.info(f"OpenAI客户端已初始化，使用自定义端点: {base_url}")
            else:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI客户端已初始化，使用默认端点")
        else:
            self.client = None
        
        # 支持的语言映射
        self.language_map = {
            "en": "English",
            "zh": "中文（简体）",
            "es": "Español",
            "fr": "Français", 
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "ja": "日本語",
            "ko": "한국어",
            "ar": "العربية"
        }
    
    async def optimize_transcript(self, raw_transcript: str) -> str:
        """
        优化转录文本：修正错别字，按含义分段
        
        Args:
            raw_transcript: 原始转录文本
            
        Returns:
            优化后的转录文本（Markdown格式）
        """
        try:
            if not self.client:
                logger.warning("OpenAI API不可用，返回原始转录")
                return raw_transcript
            
            # 检测转录文本的主要语言
            detected_lang = self._detect_transcript_language(raw_transcript)
            lang_instruction = self._get_language_instruction(detected_lang)
            
            # 构建优化提示词
            system_prompt = f"""你是一个专业的文本编辑专家。请对提供的视频转录文本进行优化处理。

特别注意：视频转录中经常出现完整句子被时间戳拆分的情况，需要重新组合。

要求：
1. **严格保持原始语言({lang_instruction})，绝对不要翻译成其他语言**
2. **完全移除所有时间戳标记（如 [00:00 - 00:05]）**
3. **智能识别和重组被时间戳拆分的完整句子*，语法上不完整的句子片段需要与上下文合并
4. 修正明显的错别字和语法错误
5. 将重组后的完整句子按照语义和逻辑含义分成自然的段落
6. 段落之间用空行分隔
7. 保持原意不变，不要添加或删除实际内容
8. 确保每个句子语法完整，语言流畅自然

处理策略：
- 优先识别不完整的句子片段（如以介词、连词、形容词结尾）
- 查看相邻的文本片段，合并形成完整句子
- 重新断句，确保每句话语法完整
- 按主题和逻辑重新分段

分段要求：
- 每当话题转换时创建新段落
- 当一个想法或观点完整表达后分段
- 避免超长段落（每段不要超过250词）

输出格式：
- 纯文本段落，无时间戳或格式标记
- 每个句子结构完整
- 每个段落讨论一个主要话题
- 段落之间用空行分隔

重要提醒：这是{lang_instruction}内容，请完全用{lang_instruction}进行优化，重点解决句子被时间戳拆分导致的不连贯问题！务必进行合理的分段，避免出现超长段落！"""

            user_prompt = f"""请将以下{lang_instruction}视频转录文本优化为流畅的段落文本：

{raw_transcript}

重点任务：
1. 移除所有时间戳标记
2. 识别并重组被拆分的完整句子
3. 确保每个句子语法完整、意思连贯
4. 按含义重新分段，段落间空行分隔
5. 保持{lang_instruction}语言不变

分段指导：
- 当话题转换时必须分段
- 避免一个段落超过250个单词
- 确保段落之间有明确的空行

请特别注意修复因时间戳分割导致的句子不完整问题，并进行合理的段落划分！"""

            logger.info("正在优化转录文本...")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.1  # 略微提高温度以获得更好的分段
            )
            
            optimized_transcript = response.choices[0].message.content
            
            logger.info("转录文本优化完成")
            return optimized_transcript
            
        except Exception as e:
            logger.error(f"优化转录文本失败: {str(e)}")
            logger.info("返回原始转录文本")
            return raw_transcript

    async def summarize(self, transcript: str, target_language: str = "zh", video_title: str = None) -> str:
        """
        生成视频转录的摘要
        
        Args:
            transcript: 转录文本
            target_language: 目标语言代码
            
        Returns:
            摘要文本（Markdown格式）
        """
        try:
            if not self.client:
                return self._generate_fallback_summary(transcript, target_language)
            
            # 获取目标语言名称
            language_name = self.language_map.get(target_language, "中文（简体）")
            
            # 构建提示词
            system_prompt = f"""你是一个专业的内容总结专家。请为视频内容生成一个连贯、深度的总结。

要求：
1. 使用{language_name}进行总结
2. 生成连贯的段落式总结，避免简单的要点罗列
3. 将相关观点整合在一起，形成完整的论述
4. 保持逻辑层次，从整体到具体
5. 突出核心思想和关键洞察
6. 语言流畅自然，读起来像一篇完整的文章
7. 适当使用过渡句连接不同部分

格式要求：
- 使用自然的段落结构
- 每段专注一个主要方面
- 段落间有逻辑递进关系
- 避免简单的列表和要点
- 整体应该是一个完整、连贯的叙述"""

            user_prompt = f"""请为以下视频内容生成一个连贯的{language_name}总结：

{transcript}

要求：写成流畅的段落文章，整合相关观点，避免简单罗列，突出核心思想和逻辑脉络。"""

            logger.info(f"正在生成{language_name}摘要...")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            # 添加元信息 - 使用目标语言
            meta_labels = self._get_summary_labels(target_language)
            
            # 直接使用视频标题作为主标题
            title = video_title if video_title else "Summary"
            
            summary_with_meta = f"""# {title}

**{meta_labels['language_label']}:** {language_name}


{summary}


<br/>

<p style="color: #888; font-style: italic; text-align: center; margin-top: 24px;"><em>{meta_labels['disclaimer']}</em></p>"""
            
            logger.info("摘要生成完成")
            return summary_with_meta
            
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            return self._generate_fallback_summary(transcript, target_language)
    
    def _generate_fallback_summary(self, transcript: str, target_language: str) -> str:
        """
        生成备用摘要（当OpenAI API不可用时）
        
        Args:
            transcript: 转录文本
            target_language: 目标语言代码
            
        Returns:
            备用摘要文本
        """
        language_name = self.language_map.get(target_language, "中文（简体）")
        
        # 简单的文本处理，提取关键信息
        lines = transcript.split('\n')
        content_lines = [line for line in lines if line.strip() and not line.startswith('#') and not line.startswith('**')]
        
        # 计算大概的长度
        total_chars = sum(len(line) for line in content_lines)
        
        # 使用目标语言的标签
        meta_labels = self._get_summary_labels(target_language)
        fallback_labels = self._get_fallback_labels(target_language)
        
        # 直接使用视频标题作为主标题  
        title = video_title if video_title else "Summary"
        
        summary = f"""# {title}

**{meta_labels['language_label']}:** {language_name}
**{fallback_labels['notice']}:** {fallback_labels['api_unavailable']}



## {fallback_labels['overview_title']}

**{fallback_labels['content_length']}:** {fallback_labels['about']} {total_chars} {fallback_labels['characters']}
**{fallback_labels['paragraph_count']}:** {len(content_lines)} {fallback_labels['paragraphs']}

## {fallback_labels['main_content']}

{fallback_labels['content_description']}

{fallback_labels['suggestions_intro']}

1. {fallback_labels['suggestion_1']}
2. {fallback_labels['suggestion_2']}
3. {fallback_labels['suggestion_3']}

## {fallback_labels['recommendations']}

- {fallback_labels['recommendation_1']}
- {fallback_labels['recommendation_2']}


<br/>

<p style="color: #888; font-style: italic; text-align: center; margin-top: 16px;"><em>{fallback_labels['fallback_disclaimer']}</em></p>"""
        
        return summary
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_supported_languages(self) -> dict:
        """
        获取支持的语言列表
        
        Returns:
            语言代码到语言名称的映射
        """
        return self.language_map.copy()
    
    def _detect_transcript_language(self, transcript: str) -> str:
        """
        检测转录文本的主要语言
        
        Args:
            transcript: 转录文本
            
        Returns:
            检测到的语言代码
        """
        # 简单的语言检测逻辑：查找转录文本中的语言标记
        if "**检测语言:**" in transcript:
            # 从Whisper转录中提取检测到的语言
            lines = transcript.split('\n')
            for line in lines:
                if "**检测语言:**" in line:
                    # 提取语言代码，例如: "**检测语言:** en"
                    lang = line.split(":")[-1].strip()
                    return lang
        
        # 如果没有找到语言标记，使用简单的字符检测
        # 计算英文字符、中文字符等的比例
        total_chars = len(transcript)
        if total_chars == 0:
            return "en"  # 默认英文
            
        # 统计中文字符
        chinese_chars = sum(1 for char in transcript if '\u4e00' <= char <= '\u9fff')
        chinese_ratio = chinese_chars / total_chars
        
        # 统计英文字母
        english_chars = sum(1 for char in transcript if char.isascii() and char.isalpha())
        english_ratio = english_chars / total_chars
        
        # 根据比例判断
        if chinese_ratio > 0.3:
            return "zh"
        elif english_ratio > 0.3:
            return "en"
        else:
            return "en"  # 默认英文
    
    def _get_language_instruction(self, lang_code: str) -> str:
        """
        根据语言代码获取优化指令中使用的语言名称
        
        Args:
            lang_code: 语言代码
            
        Returns:
            语言名称
        """
        language_instructions = {
            "en": "English",
            "zh": "中文",
            "ja": "日本語",
            "ko": "한국어",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "ar": "العربية"
        }
        return language_instructions.get(lang_code, "English")
    

    def _get_summary_labels(self, lang_code: str) -> dict:
        """
        获取摘要页面的多语言标签
        
        Args:
            lang_code: 语言代码
            
        Returns:
            标签字典
        """
        labels = {
            "en": {
                "language_label": "Summary Language",
                "disclaimer": "This summary is automatically generated by AI for reference only"
            },
            "zh": {
                "language_label": "摘要语言",
                "disclaimer": "本摘要由AI自动生成，仅供参考"
            },
            "ja": {
                "language_label": "要約言語",
                "disclaimer": "この要約はAIによって自動生成されており、参考用です"
            },
            "ko": {
                "language_label": "요약 언어",
                "disclaimer": "이 요약은 AI에 의해 자동 생성되었으며 참고용입니다"
            },
            "es": {
                "language_label": "Idioma del Resumen",
                "disclaimer": "Este resumen es generado automáticamente por IA, solo para referencia"
            },
            "fr": {
                "language_label": "Langue du Résumé",
                "disclaimer": "Ce résumé est généré automatiquement par IA, à titre de référence uniquement"
            },
            "de": {
                "language_label": "Zusammenfassungssprache",
                "disclaimer": "Diese Zusammenfassung wird automatisch von KI generiert, nur zur Referenz"
            },
            "it": {
                "language_label": "Lingua del Riassunto",
                "disclaimer": "Questo riassunto è generato automaticamente dall'IA, solo per riferimento"
            },
            "pt": {
                "language_label": "Idioma do Resumo",
                "disclaimer": "Este resumo é gerado automaticamente por IA, apenas para referência"
            },
            "ru": {
                "language_label": "Язык резюме",
                "disclaimer": "Это резюме автоматически генерируется ИИ, только для справки"
            },
            "ar": {
                "language_label": "لغة الملخص",
                "disclaimer": "هذا الملخص تم إنشاؤه تلقائياً بواسطة الذكاء الاصطناعي، للمرجع فقط"
            }
        }
        return labels.get(lang_code, labels["en"])
    
    def _get_fallback_labels(self, lang_code: str) -> dict:
        """
        获取备用摘要的多语言标签
        
        Args:
            lang_code: 语言代码
            
        Returns:
            标签字典
        """
        labels = {
            "en": {
                "notice": "Notice",
                "api_unavailable": "OpenAI API is unavailable, this is a simplified summary",
                "overview_title": "Transcript Overview",
                "content_length": "Content Length",
                "about": "About",
                "characters": "characters",
                "paragraph_count": "Paragraph Count",
                "paragraphs": "paragraphs",
                "main_content": "Main Content",
                "content_description": "The transcript contains complete video speech content. Since AI summary cannot be generated currently, we recommend:",
                "suggestions_intro": "For detailed information, we suggest you:",
                "suggestion_1": "Review the complete transcript text for detailed information",
                "suggestion_2": "Focus on important paragraphs marked with timestamps",
                "suggestion_3": "Manually extract key points and takeaways",
                "recommendations": "Recommendations",
                "recommendation_1": "Configure OpenAI API key for better summary functionality",
                "recommendation_2": "Or use other AI services for text summarization",
                "fallback_disclaimer": "This is an automatically generated fallback summary"
            },
            "zh": {
                "notice": "注意",
                "api_unavailable": "由于OpenAI API不可用，这是一个简化的摘要",
                "overview_title": "转录概览",
                "content_length": "内容长度",
                "about": "约",
                "characters": "字符",
                "paragraph_count": "段落数量",
                "paragraphs": "段",
                "main_content": "主要内容",
                "content_description": "转录文本包含了完整的视频语音内容。由于当前无法生成智能摘要，建议您：",
                "suggestions_intro": "为获取详细信息，建议您：",
                "suggestion_1": "查看完整的转录文本以获取详细信息",
                "suggestion_2": "关注时间戳标记的重要段落",
                "suggestion_3": "手动提取关键观点和要点",
                "recommendations": "建议",
                "recommendation_1": "配置OpenAI API密钥以获得更好的摘要功能",
                "recommendation_2": "或者使用其他AI服务进行文本总结",
                "fallback_disclaimer": "本摘要为自动生成的备用版本"
            }
        }
        return labels.get(lang_code, labels["en"])
    
    def is_available(self) -> bool:
        """
        检查摘要服务是否可用
        
        Returns:
            True if OpenAI API is configured, False otherwise
        """
        return self.client is not None
