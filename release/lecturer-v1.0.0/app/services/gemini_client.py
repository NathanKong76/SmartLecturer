from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional, Tuple
import base64

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


@dataclass
class RateLimiter:
	max_rpm: int
	max_tpm: int
	max_rpd: int
	window_seconds: int = 60

	def __post_init__(self):
		self._req_timestamps: list[float] = []
		self._used_tokens: list[Tuple[float, int]] = []
		self._daily_requests: list[float] = []

	async def wait_for_slot(self, est_tokens: int) -> None:
		# 清理窗口
		now = time.time()
		self._req_timestamps = [t for t in self._req_timestamps if now - t < self.window_seconds]
		self._used_tokens = [(t, n) for (t, n) in self._used_tokens if now - t < self.window_seconds]
		# 清理每日请求（24小时窗口）
		self._daily_requests = [t for t in self._daily_requests if now - t < 86400]

		while True:
			now = time.time()
			self._req_timestamps = [t for t in self._req_timestamps if now - t < self.window_seconds]
			self._used_tokens = [(t, n) for (t, n) in self._used_tokens if now - t < self.window_seconds]
			self._daily_requests = [t for t in self._daily_requests if now - t < 86400]

			req_ok = len(self._req_timestamps) < self.max_rpm
			tokens_used = sum(n for _, n in self._used_tokens)
			tpm_ok = (tokens_used + est_tokens) <= self.max_tpm
			rpd_ok = len(self._daily_requests) < self.max_rpd

			if req_ok and tpm_ok and rpd_ok:
				break
			await asyncio.sleep(0.25)

		self._req_timestamps.append(time.time())
		self._used_tokens.append((time.time(), est_tokens))
		self._daily_requests.append(time.time())


def estimate_tokens(chinese_chars: int) -> int:
	# 粗估：中文约 2 字 ≈ 1 token，叠加指令开销 200
	return max(256, chinese_chars // 2 + 200)


class GeminiClient:
	def __init__(self, api_key: str, model_name: str, temperature: float, max_output_tokens: int,
				rpm_limit: int, tpm_budget: int, rpd_limit: int, logger=None) -> None:
		# Validate input parameters
		if not api_key or not isinstance(api_key, str):
			raise ValueError("api_key cannot be empty and must be a string")
		if not model_name or not isinstance(model_name, str):
			raise ValueError("model_name cannot be empty and must be a string")
		if not (0.0 <= temperature <= 1.0):
			raise ValueError(f"temperature must be between 0.0 and 1.0, got {temperature}")
		if not isinstance(max_output_tokens, int) or max_output_tokens < 1:
			raise ValueError(f"max_output_tokens must be a positive integer, got {max_output_tokens}")
		if not isinstance(rpm_limit, int) or rpm_limit < 1:
			raise ValueError(f"rpm_limit must be a positive integer, got {rpm_limit}")
		if not isinstance(tpm_budget, int) or tpm_budget < 1:
			raise ValueError(f"tpm_budget must be a positive integer, got {tpm_budget}")
		if not isinstance(rpd_limit, int) or rpd_limit < 1:
			raise ValueError(f"rpd_limit must be a positive integer, got {rpd_limit}")
		
		self.llm = ChatGoogleGenerativeAI(
			model=model_name,
			api_key=api_key,
			temperature=temperature,
			max_output_tokens=max_output_tokens,
		)
		self.ratelimiter = RateLimiter(max_rpm=rpm_limit, max_tpm=tpm_budget, max_rpd=rpd_limit)
		self.logger = logger

	async def explain_page(self, image_bytes: bytes, system_prompt: str) -> str:
		"""处理单页讲解（保持向后兼容）"""
		return await self.explain_pages_with_context([("当前页", image_bytes)], system_prompt)

	async def explain_pages_with_context(self, images_with_labels: list[Tuple[str, bytes]], system_prompt: str, context_prompt: Optional[str] = None) -> str:
		"""处理带上下文的页面讲解
		
		Args:
			images_with_labels: (标签, 图片字节) 元组列表，顺序为 [("前一页", bytes), ("当前页", bytes), ("后一页", bytes)]
			system_prompt: 用户自定义的系统提示词
			context_prompt: 独立的上下文说明提示词（可选）
			
		Returns:
			讲解文本
		"""
		# 估算输出 tokens（目标 800~1200字），考虑多图增加开销
		base_tokens = estimate_tokens(1200)
		image_overhead = len(images_with_labels) * 200  # 每张图片约增加200 tokens
		est = base_tokens + image_overhead
		await self.ratelimiter.wait_for_slot(est)

		# 构建完整提示词
		full_prompt = system_prompt
		if context_prompt:
			full_prompt = f"{context_prompt}\n\n{system_prompt}"

		# 将图片字节转为 data URL，每张图片前添加说明文本
		content = [{"type": "text", "text": full_prompt}]
		for label, img_bytes in images_with_labels:
			# 添加图片说明
			content.append({"type": "text", "text": f"【{label}】"})
			# 添加图片
			b64 = base64.b64encode(img_bytes).decode("utf-8")
			data_url = f"data:image/png;base64,{b64}"
			content.append({"type": "image_url", "image_url": data_url})

		backoff = 1.5
		delay = 1.0
		for attempt in range(5):
			try:
				resp = await asyncio.to_thread(self.llm.invoke, [HumanMessage(content=content)])
				text = resp.content if isinstance(resp.content, str) else resp.content[0].text
				return text.strip()
			except Exception as e:  # 捕获 429/5xx 等
				if attempt >= 4:
					raise
				if self.logger:
					self.logger(f"LLM 调用失败(第 {attempt+1} 次)：{e}")
				await asyncio.sleep(delay + random.uniform(0, 0.5))
				delay *= backoff
