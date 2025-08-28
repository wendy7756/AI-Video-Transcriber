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
        支持长文本自动分块处理
        
        Args:
            raw_transcript: 原始转录文本
            
        Returns:
            优化后的转录文本（Markdown格式）
        """
        try:
            if not self.client:
                logger.warning("OpenAI API不可用，返回原始转录")
                return raw_transcript
            
            # 粗略估算token数（中文按1.2倍，英文按4:1）
            estimated_tokens = self._estimate_tokens(raw_transcript)
            max_input_tokens = 90000  # 保守估计，为输出预留空间
            
            if estimated_tokens <= max_input_tokens:
                # 短文本直接处理
                return await self._optimize_single_chunk(raw_transcript)
            else:
                # 长文本分块处理
                logger.info(f"文本较长({estimated_tokens} tokens)，启用分块优化")
                return await self._optimize_with_chunks(raw_transcript, max_input_tokens)
            
        except Exception as e:
            logger.error(f"优化转录文本失败: {str(e)}")
            logger.info("返回原始转录文本")
            return raw_transcript

    def _estimate_tokens(self, text: str) -> int:
        """
        粗略估算文本的token数量
        """
        # 简单估算：中文字符*1.2，英文单词*1，其他字符/4
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in text.split() if word.isascii() and word.isalpha()])
        other_chars = len(text) - chinese_chars - sum(len(word) for word in text.split() if word.isascii())
        
        return int(chinese_chars * 1.2 + english_words + other_chars / 4)

    async def _optimize_single_chunk(self, raw_transcript: str) -> str:
        """
        优化单个文本块
        """
        detected_lang = self._detect_transcript_language(raw_transcript)
        lang_instruction = self._get_language_instruction(detected_lang)
        
        system_prompt = f"""你是一个专业的文本编辑专家。请对提供的视频转录文本进行优化处理。

特别注意：视频转录中经常出现完整句子被时间戳拆分的情况，需要重新组合。

要求：
1. **严格保持原始语言({lang_instruction})，绝对不要翻译成其他语言**
2. **完全移除所有时间戳标记（如 [00:00 - 00:05]）**
3. **智能识别和重组被时间戳拆分的完整句子**，语法上不完整的句子片段需要与上下文合并
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

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        return response.choices[0].message.content

    async def _optimize_with_chunks(self, raw_transcript: str, max_tokens: int) -> str:
        """
        分块优化长文本
        """
        detected_lang = self._detect_transcript_language(raw_transcript)
        lang_instruction = self._get_language_instruction(detected_lang)
        
        # 按段落分割原始转录（保留时间戳作为分割参考）
        chunks = self._split_into_chunks(raw_transcript, max_tokens)
        logger.info(f"分割为 {len(chunks)} 个块进行处理")
        
        optimized_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"正在优化第 {i+1}/{len(chunks)} 块...")
            
            system_prompt = f"""你是专业的文本编辑专家。请对这段转录文本片段进行简单优化。

这是完整转录的第{i+1}部分，共{len(chunks)}部分。

简单优化要求：
1. **严格保持原始语言({lang_instruction})**，绝对不翻译
2. **仅修正明显的错别字和语法错误**
3. **稍微调整句子流畅度**，但不大幅改写
4. **保持原文结构和长度**，不做复杂的段落重组
5. **保持原意100%不变**

注意：这只是初步清理，不要做复杂的重写或重新组织。"""

            user_prompt = f"""简单优化以下{lang_instruction}文本片段（仅修错别字和语法）：

{chunk}

输出清理后的文本，保持原文结构。"""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=3000,
                    temperature=0.1
                )
                
                optimized_chunk = response.choices[0].message.content
                optimized_chunks.append(optimized_chunk)
                
            except Exception as e:
                logger.error(f"优化第 {i+1} 块失败: {e}")
                # 失败时使用基本清理
                cleaned_chunk = self._basic_transcript_cleanup(chunk)
                optimized_chunks.append(cleaned_chunk)
        
        # 合并所有优化后的块
        merged_text = "\n\n".join(optimized_chunks)
        
        # 对合并后的文本进行二次段落整理
        logger.info("正在进行最终段落整理...")
        final_result = await self._final_paragraph_organization(merged_text, lang_instruction)
        
        logger.info("分块优化完成")
        return final_result

    def _split_into_chunks(self, text: str, max_tokens: int) -> list:
        """
        将原始转录文本智能分割成合适大小的块
        策略：先提取纯文本，按句子和段落自然分割
        """
        import re
        
        # 1. 先提取纯文本内容（移除时间戳、标题等）
        pure_text = self._extract_pure_text(text)
        
        # 2. 按句子分割，保持句子完整性
        sentences = self._split_into_sentences(pure_text)
        
        # 3. 按token限制组装成块
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            # 检查是否能加入当前块
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # 当前块已满，保存并开始新块
                chunks.append(self._join_sentences(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # 添加到当前块
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # 添加最后一块
        if current_chunk:
            chunks.append(self._join_sentences(current_chunk))
        
        return chunks
    
    def _extract_pure_text(self, raw_transcript: str) -> str:
        """
        从原始转录中提取纯文本，移除时间戳和元数据
        """
        lines = raw_transcript.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过时间戳、标题、元数据
            if (line.startswith('**[') and line.endswith(']**') or
                line.startswith('#') or
                line.startswith('**检测语言:**') or
                line.startswith('**语言概率:**') or
                not line):
                continue
            text_lines.append(line)
        
        return ' '.join(text_lines)
    
    def _split_into_sentences(self, text: str) -> list:
        """
        按句子分割文本，考虑中英文差异
        """
        import re
        
        # 中英文句子结束符
        sentence_endings = r'[.!?。！？;；]+'
        
        # 分割句子，保留句号
        parts = re.split(f'({sentence_endings})', text)
        
        sentences = []
        current = ""
        
        for i, part in enumerate(parts):
            if re.match(sentence_endings, part):
                # 这是句子结束符，加到当前句子
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            else:
                # 这是句子内容
                current += part
        
        # 处理最后没有句号的部分
        if current.strip():
            sentences.append(current.strip())
        
        return [s for s in sentences if s.strip()]
    

    
    def _join_sentences(self, sentences: list) -> str:
        """
        重新组合句子为段落
        """
        return ' '.join(sentences)

    def _basic_transcript_cleanup(self, raw_transcript: str) -> str:
        """
        基本的转录文本清理：移除时间戳和标题信息
        当GPT优化失败时的后备方案
        """
        lines = raw_transcript.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 跳过时间戳行
            if line.strip().startswith('**[') and line.strip().endswith(']**'):
                continue
            # 跳过标题行
            if line.strip().startswith('# ') or line.strip().startswith('## '):
                continue
            # 跳过检测语言等元信息行
            if line.strip().startswith('**检测语言:**') or line.strip().startswith('**语言概率:**'):
                continue
            # 保留非空文本行
            if line.strip():
                cleaned_lines.append(line.strip())
        
        # 将句子重新组合并智能分段
        text = ' '.join(cleaned_lines)
        
        # 更智能的分句处理，考虑中英文差异
        import re
        
        # 按句号、问号、感叹号分句
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        paragraphs = []
        current_paragraph = []
        
        for i, sentence in enumerate(sentences):
            if sentence:
                current_paragraph.append(sentence)
                
                # 智能分段条件：
                # 1. 每3个句子一段（基本规则）
                # 2. 遇到话题转换词汇时强制分段
                # 3. 避免超长段落
                topic_change_keywords = [
                    '首先', '其次', '然后', '接下来', '另外', '此外', '最后', '总之',
                    'first', 'second', 'third', 'next', 'also', 'however', 'finally',
                    '现在', '那么', '所以', '因此', '但是', '然而',
                    'now', 'so', 'therefore', 'but', 'however'
                ]
                
                should_break = False
                
                # 检查是否需要分段
                if len(current_paragraph) >= 3:  # 基本长度条件
                    should_break = True
                elif len(current_paragraph) >= 2:  # 较短但遇到话题转换
                    for keyword in topic_change_keywords:
                        if sentence.lower().startswith(keyword.lower()):
                            should_break = True
                            break
                
                if should_break or len(current_paragraph) >= 4:  # 最大长度限制
                    # 组合当前段落
                    paragraph_text = '. '.join(current_paragraph)
                    if not paragraph_text.endswith('.'):
                        paragraph_text += '.'
                    paragraphs.append(paragraph_text)
                    current_paragraph = []
        
        # 添加剩余的句子
        if current_paragraph:
            paragraph_text = '. '.join(current_paragraph)
            if not paragraph_text.endswith('.'):
                paragraph_text += '.'
            paragraphs.append(paragraph_text)
        
        return '\n\n'.join(paragraphs)

    async def _final_paragraph_organization(self, text: str, lang_instruction: str) -> str:
        """
        对合并后的文本进行最终的段落整理
        """
        try:
            system_prompt = f"""你是段落整理专家。请对已经过基础优化的{lang_instruction}文本进行段落重新组织。

要求：
1. **严格保持原始语言({lang_instruction})**
2. **不改变任何实际内容**，只调整段落结构
3. **按话题和逻辑重新分段**
4. **合并过短的段落**，拆分过长的段落
5. **确保段落间逻辑连贯**
6. **段落间用空行分隔**

段落标准：
- 每段3-6个句子
- 每段一个主要话题
- 段落长度适中（不超过250词）
- 段落间有逻辑过渡"""

            user_prompt = f"""重新组织以下{lang_instruction}文本的段落结构：

{text}

输出重新分段后的文本，保持内容不变。"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"最终段落整理失败: {e}")
            # 失败时返回合并的原文
            return text

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
                logger.warning("OpenAI API不可用，生成备用摘要")
                return self._generate_fallback_summary(transcript, target_language, video_title)
            
            # 估算转录文本长度，决定是否需要分块摘要
            estimated_tokens = self._estimate_tokens(transcript)
            max_summarize_tokens = 60000  # 摘要输入token限制更保守
            
            if estimated_tokens <= max_summarize_tokens:
                # 短文本直接摘要
                return await self._summarize_single_text(transcript, target_language, video_title)
            else:
                # 长文本分块摘要
                logger.info(f"文本较长({estimated_tokens} tokens)，启用分块摘要")
                return await self._summarize_with_chunks(transcript, target_language, video_title, max_summarize_tokens)
            
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            return self._generate_fallback_summary(transcript, target_language, video_title)

    async def _summarize_single_text(self, transcript: str, target_language: str, video_title: str = None) -> str:
        """
        对单个文本进行摘要
        """
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
        
        # 添加元信息和标题
        return self._format_summary_with_meta(summary, target_language, video_title)

    async def _summarize_with_chunks(self, transcript: str, target_language: str, video_title: str, max_tokens: int) -> str:
        """
        分块摘要长文本
        """
        language_name = self.language_map.get(target_language, "中文（简体）")
        
        # 将长文本分割为块
        chunks = self._split_into_chunks(transcript, max_tokens)
        logger.info(f"分割为 {len(chunks)} 个块进行摘要")
        
        chunk_summaries = []
        
        # 每块生成局部摘要
        for i, chunk in enumerate(chunks):
            logger.info(f"正在摘要第 {i+1}/{len(chunks)} 块...")
            
            system_prompt = f"""你是摘要专家。请为这段文本生成简洁的{language_name}摘要。

这是完整内容的第{i+1}部分，共{len(chunks)}部分。

要求：
1. 使用{language_name}
2. 抓住本段的核心要点
3. 保持简洁但完整
4. 为后续合并做准备"""

            user_prompt = f"""摘要以下文本的核心内容：

{chunk}

输出简洁的{language_name}摘要。"""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                
                chunk_summary = response.choices[0].message.content
                chunk_summaries.append(chunk_summary)
                
            except Exception as e:
                logger.error(f"摘要第 {i+1} 块失败: {e}")
                # 失败时生成简单摘要
                simple_summary = f"第{i+1}部分内容概述：" + chunk[:200] + "..."
                chunk_summaries.append(simple_summary)
        
        # 合并所有局部摘要
        combined_summaries = "\n\n".join(chunk_summaries)
        
        # 对合并的摘要进行最终整合
        logger.info("正在整合最终摘要...")
        final_summary = await self._integrate_chunk_summaries(combined_summaries, target_language)
        
        # 添加元信息和标题
        return self._format_summary_with_meta(final_summary, target_language, video_title)

    async def _integrate_chunk_summaries(self, combined_summaries: str, target_language: str) -> str:
        """
        整合分块摘要为最终连贯摘要
        """
        language_name = self.language_map.get(target_language, "中文（简体）")
        
        try:
            system_prompt = f"""你是内容整合专家。请将多个分段摘要整合为一个连贯完整的{language_name}总结。

要求：
1. 整合所有要点，消除重复
2. 建立逻辑联系和层次结构
3. 写成连贯的段落式文章
4. 突出核心主题和关键观点
5. 语言流畅自然，避免生硬拼接"""

            user_prompt = f"""请将以下分段摘要整合为一篇连贯的{language_name}总结文章：

{combined_summaries}

要求：整合所有内容，形成逻辑清晰、语言流畅的完整文章。"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"整合摘要失败: {e}")
            # 失败时直接合并
            return combined_summaries

    def _format_summary_with_meta(self, summary: str, target_language: str, video_title: str = None) -> str:
        """
        为摘要添加标题和元信息
        """
        language_name = self.language_map.get(target_language, "中文（简体）")
        meta_labels = self._get_summary_labels(target_language)
        
        # 直接使用视频标题作为主标题
        title = video_title if video_title else "Summary"
        
        summary_with_meta = f"""# {title}

**{meta_labels['language_label']}:** {language_name}


{summary}


<br/>

<p style="color: #888; font-style: italic; text-align: center; margin-top: 24px;"><em>{meta_labels['disclaimer']}</em></p>"""
        
        return summary_with_meta
    
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
