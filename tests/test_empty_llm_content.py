"""Regression tests for issue #52: HTTP 200 with empty message.content.

Run: venv/bin/python -m unittest discover tests
"""
import asyncio
import logging
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from llm_client import EmptyLLMResponse, complete_text  # noqa: E402
from summarizer import Summarizer  # noqa: E402
from translator import Translator  # noqa: E402

logging.disable(logging.CRITICAL)


def reply(content, finish_reason="stop", reasoning_content=None):
    message = SimpleNamespace(content=content, reasoning_content=reasoning_content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


EMPTY_LENGTH = reply("", finish_reason="length", reasoning_content="thinking...")
EMPTY_STOP = reply(None)


class ScriptedClient:
    """Returns the scripted replies in order; the last one repeats forever."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        index = min(len(self.calls), len(self.replies)) - 1
        return self.replies[index]


def make_summarizer(client):
    summarizer = Summarizer(api_key="test-key", model="test-model")
    summarizer.client = client
    return summarizer


def make_translator(client):
    translator = Translator(api_key="test-key", model="test-model")
    translator.client = client
    return translator


RAW_TRANSCRIPT = (
    "# Video Transcription\n\n"
    "**Detected Language:** en\n"
    "**Language Probability:** 1.00\n\n"
    "## Transcription Content\n\n"
    "**[00:00 - 00:05]**\n\n"
    "Hello everyone. Today we talk about teleprompters. They help you read a script.\n"
)


class CompleteTextTests(unittest.TestCase):
    def call(self, client, max_tokens=4000):
        return asyncio.run(complete_text(
            client, model="m", messages=[{"role": "user", "content": "hi"}],
            max_tokens=max_tokens, temperature=0.1,
        ))

    def test_returns_content(self):
        client = ScriptedClient(reply("  answer  "))
        self.assertEqual(self.call(client), "answer")
        self.assertEqual(len(client.calls), 1)

    def test_retries_with_larger_budget_when_reasoning_exhausts_tokens(self):
        client = ScriptedClient(EMPTY_LENGTH, reply("answer"))
        self.assertEqual(self.call(client, max_tokens=600), "answer")
        self.assertEqual([c["max_tokens"] for c in client.calls], [600, 1200])

    def test_retry_budget_is_capped(self):
        client = ScriptedClient(EMPTY_LENGTH, reply("answer"))
        self.call(client, max_tokens=6000)
        self.assertEqual([c["max_tokens"] for c in client.calls], [6000, 8192])

    def test_retries_with_same_budget_when_not_length(self):
        client = ScriptedClient(EMPTY_STOP, reply("answer"))
        self.assertEqual(self.call(client), "answer")
        self.assertEqual([c["max_tokens"] for c in client.calls], [4000, 4000])

    def test_raises_after_two_empty_replies(self):
        client = ScriptedClient(EMPTY_LENGTH)
        with self.assertRaises(EmptyLLMResponse):
            self.call(client)
        self.assertEqual(len(client.calls), 2)


    def test_slow_call_does_not_block_event_loop(self):
        """A slow LLM call must not freeze SSE progress updates / status requests."""
        client = ScriptedClient(reply("answer"))
        slow_create = client.chat.completions.create

        def create(**kwargs):
            time.sleep(0.5)
            return slow_create(**kwargs)

        client.chat.completions.create = create

        async def run():
            ticks = 0

            async def ticker():
                nonlocal ticks
                while True:
                    await asyncio.sleep(0.05)
                    ticks += 1

            task = asyncio.create_task(ticker())
            await complete_text(client, model="m", messages=[], max_tokens=10, temperature=0)
            task.cancel()
            return ticks

        self.assertGreaterEqual(asyncio.run(run()), 5)


class SummarizerEmptyContentTests(unittest.TestCase):
    def test_optimize_falls_back_to_local_formatting(self):
        summarizer = make_summarizer(ScriptedClient(EMPTY_LENGTH))
        script = asyncio.run(summarizer.optimize_transcript(RAW_TRANSCRIPT))
        self.assertIn("Hello everyone.", script)
        self.assertIn("teleprompters", script)

    def test_optimize_uses_retry_result(self):
        summarizer = make_summarizer(ScriptedClient(EMPTY_LENGTH, reply("Polished transcript.")))
        script = asyncio.run(summarizer.optimize_transcript(RAW_TRANSCRIPT))
        self.assertEqual(script.strip(), "Polished transcript.")

    def test_optimize_long_transcript_keeps_every_chunk(self):
        summarizer = make_summarizer(ScriptedClient(EMPTY_LENGTH))
        sentences = [f"Sentence number {i} is about topic {i}." for i in range(300)]
        script = asyncio.run(summarizer.optimize_transcript(" ".join(sentences)))
        self.assertIn("Sentence number 0 ", script)
        self.assertIn("Sentence number 299 ", script)

    def test_optimize_never_returns_empty_for_real_speech(self):
        summarizer = make_summarizer(ScriptedClient(reply("ok")))

        async def empty_format(*args, **kwargs):
            return ""

        summarizer._format_single_chunk = empty_format
        script = asyncio.run(summarizer.optimize_transcript(RAW_TRANSCRIPT))
        self.assertIn("Hello everyone.", script)

    def test_summary_falls_back_instead_of_empty(self):
        summarizer = make_summarizer(ScriptedClient(EMPTY_LENGTH))
        summary = asyncio.run(summarizer.summarize("Hello everyone. " * 20, "en", "Title"))
        expected = summarizer._generate_fallback_summary("Hello everyone. " * 20, "en", "Title")
        self.assertEqual(summary, expected)
        self.assertTrue(summary.strip())

    def test_chunked_summary_falls_back_per_chunk_and_on_integration(self):
        summarizer = make_summarizer(ScriptedClient(EMPTY_LENGTH))
        transcript = "\n\n".join(f"Paragraph {i}. " + "Some spoken words here. " * 40 for i in range(20))
        summary = asyncio.run(summarizer.summarize(transcript, "en", None))
        self.assertIn("Paragraph 0.", summary)
        self.assertIn("[Part 1]", summary)


class TranslatorEmptyContentTests(unittest.TestCase):
    def test_single_text_keeps_original(self):
        translator = make_translator(ScriptedClient(EMPTY_LENGTH))
        result = asyncio.run(translator.translate_text("Hello world.", "zh", "en"))
        self.assertEqual(result, "Hello world.")

    def test_chunks_keep_original_chunk(self):
        translator = make_translator(ScriptedClient(reply("第一块译文"), EMPTY_LENGTH))
        text = "\n\n".join(f"Paragraph {i}. " + "Some spoken words here. " * 40 for i in range(6))
        result = asyncio.run(translator.translate_text(text, "zh", "en"))
        self.assertGreater(len(translator.client.calls), 1)
        self.assertTrue(result.startswith("第一块译文"))
        self.assertIn("Paragraph 5.", result)


if __name__ == "__main__":
    unittest.main()
