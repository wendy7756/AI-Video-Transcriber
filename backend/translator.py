# =============================================================================
# backend/translator.py - 文字翻譯器
# =============================================================================
# 此檔案包含文字翻譯器類別，負責使用GPT-4o進行高品質翻譯。
# 主要功能包括文字翻譯、語言檢測、分塊處理等。
# 依賴：OpenAI API等
# =============================================================================

import logging
from openai import OpenAI
from typing import Optional
import re

logger = logging.getLogger(__name__)

class Translator:
    """文字翻譯器，使用GPT-4o進行高品質翻譯"""

    def __init__(self):
        """
        初始化翻譯器。

        設定OpenAI客戶端和語言映射。
        """
        self.client = None
        self._init_openai_client()

        # 語言映射
        self.language_map = {
            "zh": "中文（簡體）",
            "zh-tw": "中文（繁體）",
            "en": "English",
            "ja": "日本語",
            "ko": "한국어",
            "fr": "Français",
            "de": "Deutsch",
            "es": "Español",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "ar": "العربية",
            "hi": "हिन्दी"
        }
    
    def _init_openai_client(self):
        """
        初始化OpenAI客戶端。

        從環境變數獲取API金鑰和基礎URL來初始化OpenAI客戶端。
        """
        try:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

            if not api_key:
                logger.warning("未設置OPENAI_API_KEY環境變數")
                return

            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            logger.info("OpenAI客戶端初始化成功")

        except Exception as e:
            logger.error(f"初始化OpenAI客戶端失敗: {str(e)}")
            self.client = None

    def _detect_source_language(self, text: str) -> str:
        """
        檢測源文字語言。

        Args:
            text: 要檢測語言的文字

        Returns:
            str: 檢測到的語言代碼
        """
        # 簡單的語言檢測邏輯
        if "**檢測語言:**" in text:
            lines = text.split('\n')
            for line in lines:
                if "**檢測語言:**" in line:
                    lang = line.split(":")[-1].strip()
                    return lang

        # 基於字符統計的簡單檢測
        total_chars = len(text)
        if total_chars == 0:
            return "en"

        # 統計中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        chinese_ratio = chinese_chars / total_chars

        # 統計日文字符
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        japanese_ratio = japanese_chars / total_chars

        # 統計韓文字符
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        korean_ratio = korean_chars / total_chars

        if chinese_ratio > 0.1:
            return "zh"
        elif japanese_ratio > 0.05:
            return "ja"
        elif korean_ratio > 0.05:
            return "ko"
        else:
            return "en"

    def _smart_chunk_text(self, text: str, max_chars_per_chunk: int = 4000) -> list:
        """
        智慧分塊文字用於翻譯。

        Args:
            text: 要分塊的文字
            max_chars_per_chunk: 每個塊的最大字符數

        Returns:
            list: 分塊後的文字列表
        """
        chunks = []

        # 首先按段落分割
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        current_chunk = ""

        for paragraph in paragraphs:
            # 如果當前段落加上現有塊超過限制
            if len(current_chunk) + len(paragraph) + 2 > max_chars_per_chunk and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # 添加最後一塊
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 如果某個塊仍然太長，按句子進一步分割
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chars_per_chunk:
                final_chunks.append(chunk)
            else:
                # 按句子分割
                sentences = re.split(r'[.!?。！？]\s+', chunk)
                current_sub_chunk = ""

                for sentence in sentences:
                    if len(current_sub_chunk) + len(sentence) + 2 > max_chars_per_chunk and current_sub_chunk:
                        final_chunks.append(current_sub_chunk.strip())
                        current_sub_chunk = sentence
                    else:
                        if current_sub_chunk:
                            current_sub_chunk += ". " + sentence
                        else:
                            current_sub_chunk = sentence

                if current_sub_chunk.strip():
                    final_chunks.append(current_sub_chunk.strip())

        return final_chunks
    
    async def translate_text(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """
        翻譯文字到目標語言。

        Args:
            text: 要翻譯的文字
            target_language: 目標語言代碼
            source_language: 源語言代碼（可選，會自動檢測）

        Returns:
            翻譯後的文字
        """
        try:
            if not self.client:
                logger.warning("OpenAI API不可用，無法翻譯")
                return text

            # 檢測源語言
            if not source_language:
                source_language = self._detect_source_language(text)

            # 如果源語言和目標語言相同，直接返回
            if source_language == target_language:
                return text

            source_lang_name = self.language_map.get(source_language, source_language)
            target_lang_name = self.language_map.get(target_language, target_language)

            logger.info(f"開始翻譯：{source_lang_name} -> {target_lang_name}")

            # 估算文字長度，決定是否需要分塊
            if len(text) > 3000:
                logger.info(f"文字較長({len(text)} chars)，啟用分塊翻譯")
                return await self._translate_with_chunks(text, target_lang_name, source_lang_name)
            else:
                return await self._translate_single_text(text, target_lang_name, source_lang_name)

        except Exception as e:
            logger.error(f"翻譯失敗: {str(e)}")
            return text

    async def _translate_single_text(self, text: str, target_lang_name: str, source_lang_name: str) -> str:
        """
        翻譯單個文字塊。

        Args:
            text: 要翻譯的文字
            target_lang_name: 目標語言名稱
            source_lang_name: 源語言名稱

        Returns:
            翻譯後的文字
        """
        system_prompt = f"""你是專業翻譯專家。請將{source_lang_name}文字準確翻譯為{target_lang_name}。

翻譯要求：
- 保持原文的格式和結構（包括段落分隔、標題等）
- 準確傳達原意，語言自然流暢
- 保留專業術語的準確性
- 不要添加解釋或註釋
- 如果遇到Markdown格式，請保持格式不變"""

        user_prompt = f"""請將以下{source_lang_name}文字翻譯為{target_lang_name}：

{text}

只返回翻譯結果，不要添加任何說明。"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"單文字翻譯失敗: {e}")
            return text

    async def _translate_with_chunks(self, text: str, target_lang_name: str, source_lang_name: str) -> str:
        """
        分塊翻譯長文字。

        Args:
            text: 要翻譯的文字
            target_lang_name: 目標語言名稱
            source_lang_name: 源語言名稱

        Returns:
            翻譯後的文字
        """
        chunks = self._smart_chunk_text(text, max_chars_per_chunk=4000)
        logger.info(f"分割為 {len(chunks)} 個塊進行翻譯")

        translated_chunks = []

        for i, chunk in enumerate(chunks):
            logger.info(f"正在翻譯第 {i+1}/{len(chunks)} 塊...")

            system_prompt = f"""你是專業翻譯專家。請將{source_lang_name}文字準確翻譯為{target_lang_name}。

這是完整文檔的第{i+1}部分，共{len(chunks)}部分。

翻譯要求：
- 保持原文的格式和結構
- 準確傳達原意，語言自然流暢
- 保留專業術語的準確性
- 不要添加解釋或註釋
- 保持與前後文的連貫性"""

            user_prompt = f"""請將以下{source_lang_name}文字翻譯為{target_lang_name}：

{chunk}

只返回翻譯結果。"""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=4000,
                    temperature=0.1
                )

                translated_chunk = response.choices[0].message.content
                translated_chunks.append(translated_chunk)

            except Exception as e:
                logger.error(f"翻譯第 {i+1} 塊失敗: {e}")
                # 失敗時保留原文
                translated_chunks.append(chunk)

        # 合併翻譯結果
        return "\n\n".join(translated_chunks)

    def should_translate(self, source_language: str, target_language: str) -> bool:
        """
        判斷是否需要翻譯。

        Args:
            source_language: 源語言代碼
            target_language: 目標語言代碼

        Returns:
            bool: 是否需要翻譯
        """
        if not source_language or not target_language:
            return False

        # 標準化語言代碼
        source_lang = source_language.lower().strip()
        target_lang = target_language.lower().strip()

        # 如果語言相同，不需要翻譯
        if source_lang == target_lang:
            return False

        # 處理中文的特殊情況
        chinese_variants = ["zh", "zh-cn", "zh-hans", "chinese"]
        if source_lang in chinese_variants and target_lang in chinese_variants:
            return False

        return True
