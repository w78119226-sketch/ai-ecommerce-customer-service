import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kefu_clawbot.deepseek_provider import DeepSeekProvider
from kefu_clawbot.models import IncomingEvent


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "您好，请提供订单号。"}}]}).encode()


class DeepSeekProviderTest(unittest.TestCase):
    def event(self):
        return IncomingEvent(
            tenant_id="t", platform="douyin", store_id="s", store_name="店铺",
            platform_nickname="顾客", message_id="m", message_type="text", text="查询订单",
        )

    @patch("kefu_clawbot.deepseek_provider.urllib.request.urlopen", return_value=_Response())
    def test_openai_compatible_request_and_reply(self, mock_urlopen):
        provider = DeepSeekProvider(api_key="test-key", base_url="https://example.test/v1", model="deepseek-chat")
        result = provider.reply(self.event())
        self.assertEqual(result.text, "您好，请提供订单号。")
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertNotIn("test-key", request.data.decode())

    def test_required_configuration(self):
        with self.assertRaises(ValueError):
            DeepSeekProvider(api_key="", base_url="https://example.test", model="deepseek-chat")

    @patch("kefu_clawbot.deepseek_provider.urllib.request.urlopen", side_effect=TimeoutError())
    def test_timeout_has_explicit_error(self, _mock_urlopen):
        provider = DeepSeekProvider(api_key="test-key", base_url="https://example.test", model="deepseek-chat", timeout_sec=3)
        with self.assertRaisesRegex(RuntimeError, "deepseek_request_timeout"):
            provider.reply(self.event())
