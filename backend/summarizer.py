# =============================================================================
# backend/summarizer.py - 智慧文字摘要與轉錄最佳化模組
# =============================================================================
# 本模組是 AI-Video-Transcriber 專案的核心文字處理元件，專門處理影片轉錄文本的智慧最佳化和摘要產生。
#
# 主要功能：
# 1. 多語言轉錄文本最佳化
#    - 智慧修正錯別字和語法
#    - 重組不完整句子
#    - 按語意重新分段
#
# 2. AI摘要產生
#    - 支援多種語言的智慧摘要
#    - 長文本分塊處理
#    - 保留原文語境和關鍵資訊
#
# 3. 轉錄文本處理策略
#    - 支援不同語言的文本處理
#    - 智慧分塊和上下文保留
#    - 處理多語言轉錄的複雜性
#
# 依賴：
#    - OpenAI API（GPT-3.5/GPT-4o）
#    - 支援多種語言的自然語言處理技術
#
# 設計原則：
#    - 保持原文意圖和語境
#    - 最大程度保留說話者原始表達
#    - 智慧且人性化的文本最佳化
# =============================================================================

import os
import openai
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Summarizer:
    """文字摘要器，使用OpenAI API產生多語言摘要"""

    def __init__(self):
        """
        初始化摘要器。

        從環境變數獲取OpenAI API設定，如果未設定API金鑰則無法使用摘要功能。
        """
        # 從環境變數獲取OpenAI API設定
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if not api_key:
            logger.warning("未設定OPENAI_API_KEY環境變數，將無法使用摘要功能")

        if api_key:
            if base_url:
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
                logger.info(f"OpenAI客戶端已初始化，使用自訂端點: {base_url}")
            else:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI客戶端已初始化，使用預設端點")
        else:
            self.client = None

        # 從環境變數讀取模型，預設為 gpt-4o-mini
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.optimization_model = os.getenv("OPENAI_OPTIMIZATION_MODEL", "gpt-3.5-turbo")
        logger.info(f"使用 OpenAI 摘要模型: {self.model}")
        logger.info(f"使用 OpenAI 最佳化模型: {self.optimization_model}")

        # 支援的語言對應
        self.language_map = {
            "en": "English",
            "zh": "中文（繁體）",
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
        最佳化轉錄文本：修正錯別字，按語意分段
        支援長文本分塊處理

        Args:
            raw_transcript: 原始轉錄文本

        Returns:
            最佳化後的轉錄文本（Markdown格式）
        """
        try:
            if not self.client:
                logger.warning("OpenAI API不可用，返回原始轉錄")
                return raw_transcript

            # 預處理：僅移除時間戳與元資訊，保留全部口語/重複內容
            preprocessed = self._remove_timestamps_and_meta(raw_transcript)
            # 使用JS策略：按字元長度分塊（更貼近tokens上限，避免估算誤差）
            detected_lang_code = self._detect_transcript_language(preprocessed)
            max_chars_per_chunk = 4000  # 對齊JS：每塊最大約4000字元

            if len(preprocessed) > max_chars_per_chunk:
                logger.info(f"文本較長({len(preprocessed)} chars)，啟用分塊最佳化")
                return await self._format_long_transcript_in_chunks(preprocessed, detected_lang_code, max_chars_per_chunk)
            else:
                return await self._format_single_chunk(preprocessed, detected_lang_code)

        except Exception as e:
            logger.error(f"最佳化轉錄文本失敗: {str(e)}")
            logger.info("返回原始轉錄文本")
            return raw_transcript

    def _estimate_tokens(self, text: str) -> int:
        """
        改進的token數量估算演算法
        更保守的估算，考量系統prompt和格式化開銷
        """
        # 更保守的估算：考量實際使用中的token膨脹
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in text.split()
                            if word.isascii() and word.isalpha()])

        # 計算基礎tokens
        base_tokens = chinese_chars * 1.5 + english_words * 1.3

        # 考量markdown格式、時間戳等開銷（約30%額外開銷）
        format_overhead = len(text) * 0.15

        # 考量系統prompt開銷（約2000-3000 tokens）
        system_prompt_overhead = 2500

        total_estimated = int(
            base_tokens + format_overhead + system_prompt_overhead)

        return total_estimated

    async def _optimize_single_chunk(self, raw_transcript: str) -> str:
        """
        最佳化單個文本塊
        """
        detected_lang = self._detect_transcript_language(raw_transcript)
        lang_instruction = self._get_language_instruction(detected_lang)

        system_prompt = f"""你是一個專業的文字編輯專家。請對提供的影片轉錄文字進行最佳化處理。

特別注意：這可能是訪談、對話或演講，如果包含多個說話者，必須保持每個說話者的原始視角。

要求：
1. **嚴格保持原始語言({lang_instruction})，絕對不要翻譯成其他語言**
2. **完全移除所有時間戳標記（如 [00:00 - 00:05]）**
3. **智慧識別和重組被時間戳拆分的完整句子**，語法上不完整的句子片段需要與上下文合併
4. 修正明顯的錯別字和語法錯誤
5. 將重組後的完整句子按照語意和邏輯含意分成自然的段落
6. 段落之間用空行分隔
7. **嚴格保持原意不變，不要新增或刪除實際內容**
8. **絕對不要改變人稱代詞（如I/我、you/你、he/他、she/她等）**
9. **保持每個說話者的原始視角和語境**
10. **識別對話結構：訪談者用"you"，受訪者用"I/we"，絕不混淆**
11. 確保每個句子語法完整，語言流暢自然

處理策略：
- 優先識別不完整的句子片段（如以介詞、連接詞、形容詞結尾）
- 檢視相鄰的文本片段，合併形成完整句子
- 重新斷句，確保每句話語法完整
- 按主題和邏輯重新分段

分段要求：
- 按主題和邏輯含意分段，每段包含1-8個相關句子
- 單段長度不超過400字元
- 避免過多的短段落，合併相關內容
- 當一個完整想法或觀點表達後分段

輸出格式：
- 純文本段落，無時間戳或格式標記
- 每個句子結構完整
- 每個段落討論一個主要話題
- 段落之間用空行分隔

重要提醒：這是{lang_instruction}內容，請完全用{lang_instruction}進行最佳化，重點解決句子被時間戳拆分導致的不連貫問題！務必進行合理的分段，避免出現超長段落！

**關鍵要求：這可能是訪談對話，絕對不要改變任何人稱代詞或說話者視角！訪談者用"you"，受訪者用"I/we"，必須嚴格保持！**"""

        user_prompt = f"""請將以下{lang_instruction}影片轉錄文本最佳化為流暢的段落文本：

{raw_transcript}

重點任務：
1. 移除所有時間戳標記
2. 識別並重組被拆分的完整句子
3. 確保每個句子語法完整、語意連貫
4. 按語意重新分段，段落間空行分隔
5. 保持{lang_instruction}語言不變

分段指導：
- 按主題和邏輯含意分段，每段包含1-8個相關句子
- 單段長度不超過400字元
- 避免過多的短段落，合併相關內容
- 確保段落之間有明確的空行

請特別注意修復因時間戳分割導致的句子不完整問題，並進行合理的段落劃分！"""

        response = self.client.chat.completions.create(
            model=self.optimization_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4000,  # 對齊JS：最佳化/格式化階段最大tokens≈4000
            temperature=0.1
        )

        return response.choices[0].message.content

    async def _optimize_with_chunks(self, raw_transcript: str, max_tokens: int) -> str:
        """
        分塊最佳化長文本
        """
        detected_lang = self._detect_transcript_language(raw_transcript)
        lang_instruction = self._get_language_instruction(detected_lang)

        # 按段落分割原始轉錄（保留時間戳作為分割參考）
        chunks = self._split_into_chunks(raw_transcript, max_tokens)
        logger.info(f"分割為 {len(chunks)} 個塊進行處理")

        optimized_chunks = []

        for i, chunk in enumerate(chunks):
            logger.info(f"正在最佳化第 {i+1}/{len(chunks)} 塊...")

            system_prompt = f"""你是專業的文本編輯專家。請對這段轉錄文本片段進行簡單最佳化。

這是完整轉錄的第{i+1}部分，共{len(chunks)}部分。

簡單最佳化要求：
1. **嚴格保持原始語言({lang_instruction})**，絕對不翻譯
2. **僅修正明顯的錯別字和語法錯誤**
3. **稍微調整句子流暢度**，但不大幅改寫
4. **保持原文結構和長度**，不做複雜的段落重組
5. **保持原意100%不變**

注意：這只是初步清理，不要做複雜的重寫或重新組織。"""

            user_prompt = f"""簡單最佳化以下{lang_instruction}文本片段（僅修錯別字和語法）：

{chunk}

輸出清理後的文本，保持原文結構。"""

            try:
                response = self.client.chat.completions.create(
                    model=self.optimization_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1200,  # 適應4000 tokens總限制
                    temperature=0.1
                )

                optimized_chunk = response.choices[0].message.content
                optimized_chunks.append(optimized_chunk)

            except Exception as e:
                logger.error(f"最佳化第 {i+1} 塊失敗: {e}")
                # 失敗時使用基本清理
                cleaned_chunk = self._basic_transcript_cleanup(chunk)
                optimized_chunks.append(cleaned_chunk)

        # 合併所有最佳化後的塊
        merged_text = "\n\n".join(optimized_chunks)

        # 對合併後的文本進行二次段落整理
        logger.info("正在進行最終段落整理...")
        final_result = await self._final_paragraph_organization(merged_text, lang_instruction)

        logger.info("分塊最佳化完成")
        return final_result

    # ===== JS openaiService.js 移植：分塊/上下文/去重/格式化 =====

    def _ensure_markdown_paragraphs(self, text: str) -> str:
        """確保Markdown段落空行、標題後空行、壓縮多餘空行。"""
        if not text:
            return text
        formatted = text.replace("\r\n", "\n")
        import re
        # 標題後加空行
        formatted = re.sub(
            r"(^#{1,6}\s+.*)\n([^\n#])", r"\1\n\n\2", formatted, flags=re.M)
        # 壓縮≥3個換行為2個
        formatted = re.sub(r"\n{3,}", "\n\n", formatted)
        # 去首尾空行
        formatted = re.sub(r"^\n+", "", formatted)
        formatted = re.sub(r"\n+$", "", formatted)
        return formatted

    async def _format_single_chunk(self, chunk_text: str, transcript_language: str = 'zh') -> str:
        """單塊最佳化（修正+格式化），遵循4000 tokens 限制。"""
        # 建構與JS版一致的系統/使用者提示
        if transcript_language == 'zh':
            prompt = (
                "請對以下音訊轉錄文本進行智慧最佳化和格式化，要求：\n\n"
                "**內容最佳化（正確性優先）：**\n"
                "1. 錯誤修正（轉錄錯誤/錯別字/同音字/專有名詞）\n"
                "2. 適度改善語法，補全不完整句子，保持原意和語言不變\n"
                "3. 口語處理：保留自然口語與重複表達，不要刪減內容，僅新增必要標點\n"
                "4. **絕對不要改變人稱代詞（I/我、you/你等）和說話者視角**\n\n"
                "**分段規則：**\n"
                "- 按主題和邏輯含意分段，每段包含1-8個相關句子\n"
                "- 單段長度不超過400字元\n"
                "- 避免過多的短段落，合併相關內容\n\n"
                "**格式要求：**Markdown 段落，段落間空行\n\n"
                f"原始轉錄文本：\n{chunk_text}"
            )
            system_prompt = (
                "你是專業的音訊轉錄文本最佳化助手，修正錯誤、改善通順度和排版格式，"
                "必須保持原意，不得刪減口語/重複/細節；僅移除時間戳或元資訊。"
                "絕對不要改變人稱代詞或說話者視角。這可能是訪談對話，訪談者用'you'，受訪者用'I/we'。"
            )
        else:
            prompt = (
                "Please intelligently optimize and format the following audio transcript text:\n\n"
                "Content Optimization (Accuracy First):\n"
                "1. Error Correction (typos, homophones, proper nouns)\n"
                "2. Moderate grammar improvement, complete incomplete sentences, keep original language/meaning\n"
                "3. Speech processing: keep natural fillers and repetitions, do NOT remove content; only add punctuation if needed\n"
                "4. **NEVER change pronouns (I, you, he, she, etc.) or speaker perspective**\n\n"
                "Segmentation Rules: Group 1-8 related sentences per paragraph by topic/logic; paragraph length NOT exceed 400 characters; avoid too many short paragraphs\n\n"
                "Format: Markdown paragraphs with blank lines between paragraphs\n\n"
                f"Original transcript text:\n{chunk_text}"
            )
            system_prompt = (
                "You are a professional transcript formatting assistant. Fix errors and improve fluency "
                "without changing meaning or removing any content; only timestamps/meta may be removed; keep Markdown paragraphs with blank lines. "
                "NEVER change pronouns or speaker perspective. This may be an interview: interviewer uses 'you', interviewee uses 'I/we'."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.optimization_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,  # 對齊JS：最佳化/格式化階段最大tokens≈4000
                temperature=0.1
            )
            optimized_text = response.choices[0].message.content or ""
            # 移除諸如 "# Transcript" / "## Transcript" 等標題
            optimized_text = self._remove_transcript_heading(optimized_text)
            enforced = self._enforce_paragraph_max_chars(
                optimized_text.strip(), max_chars=400)
            return self._ensure_markdown_paragraphs(enforced)
        except Exception as e:
            logger.error(f"單塊文本最佳化失敗: {e}")
            return self._apply_basic_formatting(chunk_text)

    def _smart_split_long_chunk(self, text: str, max_chars_per_chunk: int) -> list:
        """在句子/空格邊界處安全切分超長文本。"""
        chunks = []
        pos = 0
        while pos < len(text):
            end = min(pos + max_chars_per_chunk, len(text))
            if end < len(text):
                # 優先句子邊界
                sentence_endings = ['。', '！', '？', '.', '!', '?']
                best = -1
                for ch in sentence_endings:
                    idx = text.rfind(ch, pos, end)
                    if idx > best:
                        best = idx
                if best > pos + int(max_chars_per_chunk * 0.7):
                    end = best + 1
                else:
                    # 次選：空格邊界
                    space_idx = text.rfind(' ', pos, end)
                    if space_idx > pos + int(max_chars_per_chunk * 0.8):
                        end = space_idx
            chunks.append(text[pos:end].strip())
            pos = end
        return [c for c in chunks if c]

    def _find_safe_cut_point(self, text: str) -> int:
        """找到安全的切割點（段落>句子>片語）。"""
        import re
        # 段落
        p = text.rfind("\n\n")
        if p > 0:
            return p + 2
        # 句子
        last_sentence_end = -1
        for m in re.finditer(r"[。！？\.!?]\s*", text):
            last_sentence_end = m.end()
        if last_sentence_end > 20:
            return last_sentence_end
        # 片語
        last_phrase_end = -1
        for m in re.finditer(r"[，；,;]\s*", text):
            last_phrase_end = m.end()
        if last_phrase_end > 20:
            return last_phrase_end
        return len(text)

    def _find_overlap_between_texts(self, text1: str, text2: str) -> str:
        """偵測相鄰兩段的重疊內容，用於去重。"""
        max_len = min(len(text1), len(text2))
        # 逐步從長到短嘗試
        for length in range(max_len, 19, -1):
            suffix = text1[-length:]
            prefix = text2[:length]
            if suffix == prefix:
                cut = self._find_safe_cut_point(prefix)
                if cut > 20:
                    return prefix[:cut]
                return suffix
        return ""

    def _apply_basic_formatting(self, text: str) -> str:
        """當AI失敗時的回退：按句子拼段，段落≤250字元，雙換行分隔。"""
        if not text or not text.strip():
            return text
        import re
        parts = re.split(r"([。！？\.!?]+\s*)", text)
        sentences = []
        current = ""
        for i, part in enumerate(parts):
            if i % 2 == 0:
                current += part
            else:
                current += part
                if current.strip():
                    sentences.append(current.strip())
                    current = ""
        if current.strip():
            sentences.append(current.strip())
        paras = []
        cur = ""
        sentence_count = 0
        for s in sentences:
            candidate = (cur + " " + s).strip() if cur else s
            sentence_count += 1
            # 改進的分段邏輯：考量句子數量和長度
            should_break = False
            if len(candidate) > 400 and cur:  # 段落過長
                should_break = True
            elif len(candidate) > 200 and sentence_count >= 3:  # 中等長度且句子數足夠
                should_break = True
            elif sentence_count >= 6:  # 句子數過多
                should_break = True

            if should_break:
                paras.append(cur.strip())
                cur = s
                sentence_count = 1
            else:
                cur = candidate
        if cur.strip():
            paras.append(cur.strip())
        return self._ensure_markdown_paragraphs("\n\n".join(paras))

    async def _format_long_transcript_in_chunks(self, raw_transcript: str, transcript_language: str, max_chars_per_chunk: int) -> str:
        """智慧分塊+上下文+去重 合成最佳化文本（JS策略移植）。"""
        import re
        # 先按句子切分，組裝不超過max_chars_per_chunk的塊
        parts = re.split(r"([。！？\.!?]+\s*)", raw_transcript)
        sentences = []
        buf = ""
        for i, part in enumerate(parts):
            if i % 2 == 0:
                buf += part
            else:
                buf += part
                if buf.strip():
                    sentences.append(buf.strip())
                    buf = ""
        if buf.strip():
            sentences.append(buf.strip())

        chunks = []
        cur = ""
        for s in sentences:
            candidate = (cur + " " + s).strip() if cur else s
            if len(candidate) > max_chars_per_chunk and cur:
                chunks.append(cur.strip())
                cur = s
            else:
                cur = candidate
        if cur.strip():
            chunks.append(cur.strip())

        # 對仍然過長的塊二次安全切分
        final_chunks = []
        for c in chunks:
            if len(c) <= max_chars_per_chunk:
                final_chunks.append(c)
            else:
                final_chunks.extend(
                    self._smart_split_long_chunk(c, max_chars_per_chunk))

        logger.info(f"文本分為 {len(final_chunks)} 塊處理")

        optimized = []
        for i, c in enumerate(final_chunks):
            chunk_with_context = c
            if i > 0:
                prev_tail = final_chunks[i - 1][-100:]
                marker = f"[上文續：{prev_tail}]" if transcript_language == 'zh' else f"[Context continued: {prev_tail}]"
                chunk_with_context = marker + "\n\n" + c
            try:
                oc = await self._format_single_chunk(chunk_with_context, transcript_language)
                # 移除上下文標記
                oc = re.sub(
                    r"^[(上文續|Context continued)：?:?.*?]\s*", "", oc, flags=re.S)
                optimized.append(oc)
            except Exception as e:
                logger.warning(f"第 {i+1} 塊最佳化失敗，使用基礎格式化: {e}")
                optimized.append(self._apply_basic_formatting(c))

        # 鄰接塊去重
        deduped = []
        for i, c in enumerate(optimized):
            cur_txt = c
            if i > 0 and deduped:
                prev = deduped[-1]
                overlap = self._find_overlap_between_texts(
                    prev[-200:], cur_txt[:200])
                if overlap:
                    cur_txt = cur_txt[len(overlap):].lstrip()
                    if not cur_txt:
                        continue
            if cur_txt.strip():
                deduped.append(cur_txt)

        merged = "\n\n".join(deduped)
        merged = self._remove_transcript_heading(merged)
        enforced = self._enforce_paragraph_max_chars(merged, max_chars=400)
        return self._ensure_markdown_paragraphs(enforced)

    def _remove_timestamps_and_meta(self, text: str) -> str:
        """僅移除時間戳行與明顯元資訊（標題、偵測語言等），保留原文口語/重複。"""
        lines = text.split('\n')
        kept = []
        for line in lines:
            s = line.strip()
            # 跳過時間戳與元資訊
            if (s.startswith('**[') and s.endswith(']**')):
                continue
            if s.startswith('# '):
                # 跳過頂級標題（通常是影片標題，可在最終加回）
                continue
            if s.startswith('**偵測語言:**') or s.startswith('**語言機率:**'):
                continue
            kept.append(line)
        # 規範空行
        cleaned = '\n'.join(kept)
        return cleaned

    def _enforce_paragraph_max_chars(self, text: str, max_chars: int = 400) -> str:
        """按段落拆分並確保每段不超過max_chars，必要時按句子邊界拆為多段。"""
        if not text:
            return text
        import re
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p is not None]
        new_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if len(para) <= max_chars:
                new_paragraphs.append(para)
                continue
            # 句子切分
            parts = re.split(r"([。！？\.!?]+\s*)", para)
            sentences = []
            buf = ""
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    buf += part
                else:
                    buf += part
                    if buf.strip():
                        sentences.append(buf.strip())
                        buf = ""
            if buf.strip():
                sentences.append(buf.strip())
            cur = ""
            for s in sentences:
                candidate = (cur + (" " if cur else "") + s).strip()
                if len(candidate) > max_chars and cur:
                    new_paragraphs.append(cur)
                    cur = s
                else:
                    cur = candidate
            if cur:
                new_paragraphs.append(cur)
        return "\n\n".join([p.strip() for p in new_paragraphs if p is not None])

    def _remove_transcript_heading(self, text: str) -> str:
        """移除開頭或段落中的以 Transcript 為標題的行（任意級別#），不改變正文。"""
        if not text:
            return text
        import re
        # 移除形如 '## Transcript'、'# Transcript Text'、'### transcript' 的標題行
        lines = text.split('\n')
        filtered = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^#{1,6}\s*transcript(\s+text)?\s*$", stripped, flags=re.I):
                continue
            filtered.append(line)
        return '\n'.join(filtered)

    def _split_into_chunks(self, text: str, max_tokens: int) -> list:
        """
        將原始轉錄文本智慧分割成合適大小的塊
        策略：先提取純文本，按句子和段落自然分割
        """
        import re

        # 1. 先提取純文本內容（移除時間戳、標題等）
        pure_text = self._extract_pure_text(text)

        # 2. 按句子分割，保持句子完整性
        sentences = self._split_into_sentences(pure_text)

        # 3. 按token限制組裝成塊
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # 檢查是否能加入目前塊
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # 目前塊已滿，儲存並開始新塊
                chunks.append(self._join_sentences(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # 新增到目前塊
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # 新增最後一塊
        if current_chunk:
            chunks.append(self._join_sentences(current_chunk))

        return chunks

    def _extract_pure_text(self, raw_transcript: str) -> str:
        """
        從原始轉錄中提取純文本，移除時間戳和元數據
        """
        lines = raw_transcript.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()
            # 跳過時間戳、標題、元數據
            if (line.startswith('**[') and line.endswith(']**') or
                line.startswith('#') or
                line.startswith('**偵測語言:**') or
                line.startswith('**語言機率:**') or
                    not line):
                continue
            text_lines.append(line)

        return ' '.join(text_lines)

    def _split_into_sentences(self, text: str) -> list:
        """
        按句子分割文本，考量中英文差異
        """
        import re

        # 中英文句子結束符
        sentence_endings = r'[.!?。！？;；]+'

        # 分割句子，保留句號
        parts = re.split(f'({sentence_endings})', text)

        sentences = []
        current = ""

        for i, part in enumerate(parts):
            if re.match(sentence_endings, part):
                # 這是句子結束符，加到目前句子
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            else:
                # 這是句子內容
                current += part

        # 處理最後沒有句號的部分
        if current.strip():
            sentences.append(current.strip())

        return [s for s in sentences if s.strip()]

    def _join_sentences(self, sentences: list) -> str:
        """
        重新組合句子為段落
        """
        return ' '.join(sentences)

    def _basic_transcript_cleanup(self, raw_transcript: str) -> str:
        """
        基本的轉錄文本清理：移除時間戳和標題資訊
        當GPT最佳化失敗時的後備方案
        """
        lines = raw_transcript.split('\n')
        cleaned_lines = []

        for line in lines:
            # 跳過時間戳行
            if line.strip().startswith('**[') and line.strip().endswith(']**'):
                continue
            # 跳過標題行
            if line.strip().startswith('# ') or line.strip().startswith('## '):
                continue
            # 跳過偵測語言等元資訊行
            if line.strip().startswith('**偵測語言:**') or line.strip().startswith('**語言機率:**'):
                continue
            # 保留非空文本行
            if line.strip():
                cleaned_lines.append(line.strip())

        # 將句子重新組合並智慧分段
        text = ' '.join(cleaned_lines)

        # 更智慧的分句處理，考量中英文差異
        import re

        # 按句號、問號、驚嘆號分句
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        paragraphs = []
        current_paragraph = []

        for i, sentence in enumerate(sentences):
            if sentence:
                current_paragraph.append(sentence)

                # 智慧分段條件：
                # 1. 每3個句子一段（基本規則）
                # 2. 遇到話題轉換詞彙時強制分段
                # 3. 避免超長段落
                topic_change_keywords = [
                    '首先', '其次', '然後', '接下來', '另外', '此外', '最後', '總之',
                    'first', 'second', 'third', 'next', 'also', 'however', 'finally',
                    '現在', '那麼', '所以', '因此', '但是', '然而',
                    'now', 'so', 'therefore', 'but', 'however'
                ]

                should_break = False

                # 檢查是否需要分段
                if len(current_paragraph) >= 3:  # 基本長度條件
                    should_break = True
                elif len(current_paragraph) >= 2:  # 較短但遇到話題轉換
                    for keyword in topic_change_keywords:
                        if sentence.lower().startswith(keyword.lower()):
                            should_break = True
                            break

                if should_break or len(current_paragraph) >= 4:  # 最大長度限制
                    # 組合目前段落
                    paragraph_text = '. '.join(current_paragraph)
                    if not paragraph_text.endswith('.'):
                        paragraph_text += '.'
                    paragraphs.append(paragraph_text)
                    current_paragraph = []

        # 新增剩餘的句子
        if current_paragraph:
            paragraph_text = '. '.join(current_paragraph)
            if not paragraph_text.endswith('.'):
                paragraph_text += '.'
            paragraphs.append(paragraph_text)

        return '\n\n'.join(paragraphs)

    async def _final_paragraph_organization(self, text: str, lang_instruction: str) -> str:
        """
        對合併後的文本進行最終的段落整理
        使用改進的prompt和工程驗證
        """
        try:
            # 估算文本長度，如果太長則分塊處理
            estimated_tokens = self._estimate_tokens(text)
            if estimated_tokens > 3000:  # 對於很長的文本，分塊處理
                return await self._organize_long_text_paragraphs(text, lang_instruction)

            system_prompt = f"""你是專業的{lang_instruction}文本段落整理專家。你的任務是按照語意和邏輯重新組織段落。

🎯 **核心原則**：
1. **嚴格保持原始語言({lang_instruction})**，絕不翻譯
2. **保持所有內容完整**，不刪除不新增任何資訊
3. **按語意邏輯分段**：每段圍繞一個完整的思想或話題
4. **嚴格控制段落長度**：每段絕不超過250詞
5. **保持自然流暢**：段落間應有邏輯連接

📏 **分段標準**：
- **語意完整性**：每段講述一個完整概念或事件
- **適中長度**：3-7個句子，每段絕不超過250詞
- **邏輯邊界**：在話題轉換、時間轉換、觀點轉換處分段
- **自然斷點**：遵循說話者的自然停頓和邏輯

⚠️ **嚴禁**：
- 創造超過250詞的巨型段落
- 強行合併不相關的內容
- 打斷完整的故事或論述

輸出格式：段落間用空行分隔。"""

            user_prompt = f"""請重新整理以下{lang_instruction}文本的段落結構。嚴格按照語意和邏輯進行分段，確保每段不超過200詞：

{text}

重新分段後的文本："""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,  # 對齊JS：段落整理階段最大tokens≈4000
                temperature=0.05  # 降低溫度，提高一致性
            )

            organized_text = response.choices[0].message.content

            # 工程驗證：檢查段落長度
            validated_text = self._validate_paragraph_lengths(organized_text)

            return validated_text

        except Exception as e:
            logger.error(f"最終段落整理失敗: {e}")
            # 失敗時使用基礎分段處理
            return self._basic_paragraph_fallback(text)

    async def _organize_long_text_paragraphs(self, text: str, lang_instruction: str) -> str:
        """
        對於很長的文本，分塊進行段落整理
        """
        try:
            # 按現有段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            organized_chunks = []

            current_chunk = []
            current_tokens = 0
            max_chunk_tokens = 2500  # 適應4000 tokens總限制的chunk大小

            for para in paragraphs:
                para_tokens = self._estimate_tokens(para)

                if current_tokens + para_tokens > max_chunk_tokens and current_chunk:
                    # 處理目前chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    organized_chunk = await self._organize_single_chunk(chunk_text, lang_instruction)
                    organized_chunks.append(organized_chunk)

                    current_chunk = [para]
                    current_tokens = para_tokens
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens

            # 處理最後一個chunk
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                organized_chunk = await self._organize_single_chunk(chunk_text, lang_instruction)
                organized_chunks.append(organized_chunk)

            return '\n\n'.join(organized_chunks)

        except Exception as e:
            logger.error(f"長文本段落整理失敗: {e}")
            return self._basic_paragraph_fallback(text)

    async def _organize_single_chunk(self, text: str, lang_instruction: str) -> str:
        """
        整理單個文本塊的段落
        """
        system_prompt = f"""You are a {lang_instruction} paragraph organization expert. Reorganize paragraphs by semantics, ensuring each paragraph does not exceed 200 words.

Core requirements:
1. Strictly maintain the original {lang_instruction} language
2. Organize by semantic logic, one theme per paragraph
3. Each paragraph must not exceed 250 words
4. Separate paragraphs with blank lines
5. Keep content complete, do not reduce information"""

        user_prompt = f"""Re-paragraph the following text in {lang_instruction}, ensuring each paragraph does not exceed 200 words:

{text}"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1200,  # 適應4000 tokens總限制
            temperature=0.05
        )

        return response.choices[0].message.content

    def _validate_paragraph_lengths(self, text: str) -> str:
        """
        驗證段落長度，如果有超長段落則嘗試分割
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        validated_paragraphs = []

        for para in paragraphs:
            word_count = len(para.split())

            if word_count > 300:  # 如果段落超過300詞
                logger.warning(f"偵測到超長段落({word_count}詞)，嘗試分割")
                # 嘗試按句子分割長段落
                split_paras = self._split_long_paragraph(para)
                validated_paragraphs.extend(split_paras)
            else:
                validated_paragraphs.append(para)

        return '\n\n'.join(validated_paragraphs)

    def _split_long_paragraph(self, paragraph: str) -> list:
        """
        分割過長的段落
        """
        import re

        # 按句子分割
        sentences = re.split(r'[.!?。！？]\s+', paragraph)
        sentences = [s.strip() + '.' for s in sentences if s.strip()]

        split_paragraphs = []
        current_para = []
        current_words = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_words + sentence_words > 200 and current_para:
                # 目前段落達到長度限制
                split_paragraphs.append(' '.join(current_para))
                current_para = [sentence]
                current_words = sentence_words
            else:
                current_para.append(sentence)
                current_words += sentence_words

        # 新增最後一段
        if current_para:
            split_paragraphs.append(' '.join(current_para))

        return split_paragraphs

    def _basic_paragraph_fallback(self, text: str) -> str:
        """
        基礎分段fallback機制
        當GPT整理失敗時，使用簡單的規則分段
        """
        import re

        # 移除多餘的空行
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        basic_paragraphs = []

        for para in paragraphs:
            word_count = len(para.split())

            if word_count > 250:
                # 長段落按句子分割
                split_paras = self._split_long_paragraph(para)
                basic_paragraphs.extend(split_paras)
            elif word_count < 30 and basic_paragraphs:
                # 短段落與上一段合併（如果合併後不超過200詞）
                last_para = basic_paragraphs[-1]
                combined_words = len(last_para.split()) + word_count

                if combined_words <= 200:
                    basic_paragraphs[-1] = last_para + ' ' + para
                else:
                    basic_paragraphs.append(para)
            else:
                basic_paragraphs.append(para)

        return '\n\n'.join(basic_paragraphs)

    async def summarize(self, transcript: str, target_language: str = "zh", video_title: str = None) -> str:
        """
        產生影片轉錄的摘要

        Args:
            transcript: 轉錄文本
            target_language: 目標語言代碼
            video_title: 影片標題

        Returns:
            摘要文本（Markdown格式）
        """
        try:
            if not self.client:
                logger.warning("OpenAI API不可用，產生備用摘要")
                return self._generate_fallback_summary(transcript, target_language, video_title)

            # 估算轉錄文本長度，決定是否需要分塊摘要
            estimated_tokens = self._estimate_tokens(transcript)
            max_summarize_tokens = 4000  # 提高限制，優先使用單文本處理以獲得更好的總結品質

            if estimated_tokens <= max_summarize_tokens:
                # 短文本直接摘要
                return await self._summarize_single_text(transcript, target_language, video_title)
            else:
                # 長文本分塊摘要
                logger.info(f"文本較長({estimated_tokens} tokens)，啟用分塊摘要")
                return await self._summarize_with_chunks(transcript, target_language, video_title, max_summarize_tokens)

        except Exception as e:
            logger.error(f"產生摘要失敗: {str(e)}")
            return self._generate_fallback_summary(transcript, target_language, video_title)

    async def _summarize_single_text(self, transcript: str, target_language: str, video_title: str = None) -> str:
        """
        對單個文本進行摘要

        Args:
            transcript: 轉錄文本
            target_language: 目標語言
            video_title: 影片標題
        """
        # 獲取目標語言名稱
        language_name = self.language_map.get(target_language, "中文（繁體）")

        # 建構英文提示詞，適用於所有目標語言
        system_prompt = f"""You are a professional content analyst. Please generate a well-structured summary in {language_name} for the following text.

Summary Requirements:
1. Extract the main topics and core viewpoints from the text
2. Maintain clear logical structure, highlighting the core arguments
3. Include important discussions, viewpoints, and conclusions
4. Use concise and clear language
5. Appropriately preserve the speaker's expression style and key opinions

Paragraph Organization Requirements (Core):
1. **Organize by semantic and logical themes** - Start a new paragraph whenever the topic shifts, discussion focus changes, or when transitioning from one viewpoint to another
2. **Each paragraph should focus on one main point or theme**
3. **Paragraphs must be separated by blank lines (double line breaks \n\n)**
4. **Consider the logical flow of content and reasonably divide paragraph boundaries**

Format Requirements:
1. Use Markdown format with double line breaks between paragraphs
2. Each paragraph should be a complete logical unit
3. Write entirely in {language_name}"""

        user_prompt = f"""Based on the following content, write a well-structured summary in {language_name}:

{transcript}

Requirements:
- Focus on natural paragraphs, avoiding decorative headings
- Cover all key ideas and arguments, prioritize the most important content
- Ensure balanced coverage of both early and later content
- Use clear and concise language
- Organize content logically with proper paragraph breaks"""

        logger.info(f"正在產生{language_name}摘要...")

        # 呼叫OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3500,
            temperature=0.3
        )

        summary = response.choices[0].message.content

        return self._format_summary_with_meta(summary, target_language, video_title)

    async def _summarize_with_chunks(self, transcript: str, target_language: str, video_title: str, max_tokens: int) -> str:
        """
        分塊摘要長文本

        Args:
            transcript: 轉錄文本
            target_language: 目標語言
            video_title: 影片標題
            max_tokens: 分塊處理的最大token數
        """
        language_name = self.language_map.get(target_language, "中文（繁體）")

        # 使用JS策略：按字元進行智慧分塊（段落>句子）
        chunks = self._smart_chunk_text(transcript, max_chars_per_chunk=4000)
        logger.info(f"分割為 {len(chunks)} 個塊進行摘要")

        chunk_summaries = []

        # 每塊產生局部摘要
        for i, chunk in enumerate(chunks):
            logger.info(f"正在摘要第 {i+1}/{len(chunks)} 塊...")

            system_prompt = f"""You are a summarization expert. Please write a high-density summary for this text chunk in {language_name}.

This is part {i+1} of {len(chunks)} of the complete content (Part {i+1}/{len(chunks)}).

Output preferences: Focus on natural paragraphs, use minimal bullet points if necessary; highlight new information and its relationship to the main narrative; avoid vague repetition and formatted headings; moderate length (suggested 120-220 words)."""

            user_prompt = f"""[Part {i+1}/{len(chunks)}] Summarize the key points of the following text in {language_name} (natural paragraphs preferred, minimal bullet points, 120-220 words):

{chunk}

Avoid using any subheadings or decorative separators, output content only."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,  # 提升分塊摘要容量以涵蓋更多細節
                    temperature=0.3
                )

                chunk_summary = response.choices[0].message.content
                chunk_summaries.append(chunk_summary)

            except Exception as e:
                logger.error(f"摘要第 {i+1} 塊失敗: {e}")
                # 失敗時產生簡單摘要
                simple_summary = f"第{i+1}部分內容概述：" + chunk[:200] + "..."
                chunk_summaries.append(simple_summary)

        # 合併所有局部摘要（帶編號），如分塊較多則分層整合（不引入小標題）
        combined_summaries = "\n\n".join(
            [f"[Part {idx+1}]\n" + s for idx, s in enumerate(chunk_summaries)])

        logger.info("正在整合最終摘要...")
        if len(chunk_summaries) > 10:
            final_summary = await self._integrate_hierarchical_summaries(chunk_summaries, target_language)
        else:
            final_summary = await self._integrate_chunk_summaries(combined_summaries, target_language)

        return self._format_summary_with_meta(final_summary, target_language, video_title)

    def _smart_chunk_text(self, text: str, max_chars_per_chunk: int = 3500) -> list:
        """智慧分塊（先段落後句子），按字元上限切分。"""
        chunks = []
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        cur = ""
        for p in paragraphs:
            candidate = (cur + "\n\n" + p).strip() if cur else p
            if len(candidate) > max_chars_per_chunk and cur:
                chunks.append(cur.strip())
                cur = p
            else:
                cur = candidate
        if cur.strip():
            chunks.append(cur.strip())

        # 二次按句子切分過長塊
        import re
        final_chunks = []
        for c in chunks:
            if len(c) <= max_chars_per_chunk:
                final_chunks.append(c)
            else:
                sentences = [s.strip()
                             for s in re.split(r"[。！？\.!?]+", c) if s.strip()]
                scur = ""
                for s in sentences:
                    candidate = (scur + '。' + s).strip() if scur else s
                    if len(candidate) > max_chars_per_chunk and scur:
                        final_chunks.append(scur.strip())
                        scur = s
                    else:
                        scur = candidate
                if scur.strip():
                    final_chunks.append(scur.strip())
        return final_chunks

    async def _integrate_chunk_summaries(self, combined_summaries: str, target_language: str) -> str:
        """
        整合分塊摘要為最終連貫摘要
        """
        language_name = self.language_map.get(target_language, "中文（繁體）")

        try:
            system_prompt = f"""You are a content integration expert. Please integrate multiple segmented summaries into a complete, coherent summary in {language_name}.

Integration Requirements:
1. Remove duplicate content and maintain clear logic
2. Reorganize content by themes or chronological order
3. Each paragraph must be separated by double line breaks
4. Ensure output is in Markdown format with double line breaks between paragraphs
5. Use concise and clear language
6. Form a complete content summary
7. Cover all parts comprehensively without omission"""

            user_prompt = f"""Please integrate the following segmented summaries into a complete, coherent summary in {language_name}:

{combined_summaries}

Requirements:
- Remove duplicate content and maintain clear logic
- Reorganize content by themes or chronological order
- Each paragraph must be separated by double line breaks
- Ensure output is in Markdown format with double line breaks between paragraphs
- Use concise and clear language
- Form a complete content summary"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,  # 控制輸出規模，兼顧上下文安全
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"整合摘要失敗: {e}")
            # 失敗時直接合併
            return combined_summaries

    def _format_summary_with_meta(self, summary: str, target_language: str, video_title: str = None) -> str:
        """
        為摘要加入標題和元資訊
        """
        # 不加任何小標題/免責聲明，可保留影片標題作為一級標題
        if video_title:
            prefix = f"# {video_title}\n\n"
        else:
            prefix = ""
        return prefix + summary

    def _generate_fallback_summary(self, transcript: str, target_language: str, video_title: str = None) -> str:
        """
        產生備用摘要（當OpenAI API不可用時）

        Args:
            transcript: 轉錄文本
            video_title: 影片標題
            target_language: 目標語言代碼

        Returns:
            備用摘要文本
        """
        language_name = self.language_map.get(target_language, "中文（繁體）")

        # 簡單的文本處理，提取關鍵資訊
        lines = transcript.split('\n')
        content_lines = [line for line in lines if line.strip(
        ) and not line.startswith('#') and not line.startswith('**')]

        # 計算大概的長度
        total_chars = sum(len(line) for line in content_lines)

        # 使用目標語言的標籤
        meta_labels = self._get_summary_labels(target_language)
        fallback_labels = self._get_fallback_labels(target_language)

        # 直接使用影片標題作為主標題
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

<p style=\"color: #888; font-style: italic; text-align: center; margin-top: 16px;"><em>{fallback_labels['fallback_disclaimer']}</em></p>"""

        return summary

    def _get_current_time(self) -> str:
        """獲取目前時間字串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_supported_languages(self) -> dict:
        """
        獲取支援的語言列表

        Returns:
            語言代碼到語言名稱的對應
        """
        return self.language_map.copy()

    def _detect_transcript_language(self, transcript: str) -> str:
        """
        偵測轉錄文本的主要語言

        Args:
            transcript: 轉錄文本

        Returns:
            偵測到的語言代碼
        """
        # 簡單的語言偵測邏輯：尋找轉錄文本中的語言標記
        if "**偵測語言:**" in transcript:
            # 從Whisper轉錄中提取偵測到的語言
            lines = transcript.split('\n')
            for line in lines:
                if "**偵測語言:**" in line:
                    # 提取語言代碼，例如: "**偵測語言:** en"
                    lang = line.split(":")[-1].strip()
                    return lang

        # 如果沒有找到語言標記，使用簡單的字元偵測
        # 計算英文字元、中文字元等的比例
        total_chars = len(transcript)
        if total_chars == 0:
            return "en"  # 預設英文

        # 統計中文字元
        chinese_chars = sum(
            1 for char in transcript if '\u4e00' <= char <= '\u9fff')
        chinese_ratio = chinese_chars / total_chars

        # 統計英文字母
        english_chars = sum(
            1 for char in transcript if char.isascii() and char.isalpha())
        english_ratio = english_chars / total_chars

        # 根據比例判斷
        if chinese_ratio > 0.3:
            return "zh"
        elif english_ratio > 0.3:
            return "en"
        else:
            return "en"  # 預設英文

    def _get_language_instruction(self, lang_code: str) -> str:
        """
        根據語言代碼獲取最佳化指令中使用的語言名稱

        Args:
            lang_code: 語言代碼

        Returns:
            語言名稱
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
        獲取摘要頁面的多語言標籤

        Args:
            lang_code: 語言代碼

        Returns:
            標籤字典
        """
        labels = {
            "en": {
                "language_label": "Summary Language",
                "disclaimer": "This summary is automatically generated by AI for reference only"
            },
            "zh": {
                "language_label": "摘要語言",
                "disclaimer": "本摘要由AI自動產生，僅供參考"
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
        獲取備用摘要的多語言標籤

        Args:
            lang_code: 語言代碼

        Returns:
            標籤字典
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
                "api_unavailable": "由於OpenAI API不可用，這是一個簡化的摘要",
                "overview_title": "轉錄概覽",
                "content_length": "內容長度",
                "about": "約",
                "characters": "字元",
                "paragraph_count": "段落數量",
                "paragraphs": "段",
                "main_content": "主要內容",
                "content_description": "轉錄文本包含了完整的影片語音內容。由於目前無法產生智慧摘要，建議您：",
                "suggestions_intro": "為獲取詳細資訊，建議您：",
                "suggestion_1": "檢視完整的轉錄文本以獲取詳細資訊",
                "suggestion_2": "關注時間戳標記的重要段落",
                "suggestion_3": "手動提取關鍵觀點和要點",
                "recommendations": "建議",
                "recommendation_1": "設定OpenAI API金鑰以獲得更好的摘要功能",
                "recommendation_2": "或者使用其他AI服務進行文本總結",
                "fallback_disclaimer": "本摘要為自動產生的備用版本"
            }
        }
        return labels.get(lang_code, labels["en"])

    def is_available(self) -> bool:
        """
        檢查摘要服務是否可用

        Returns:
            如果已設定 OpenAI API 則為 True，否則為 False
        """
        return self.client is not None
