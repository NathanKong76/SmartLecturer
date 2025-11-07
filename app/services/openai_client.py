from __future__ import annotations

import asyncio
import base64
import random
from typing import Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .gemini_client import RateLimiter, estimate_tokens


class OpenAIClient:
	def __init__(
		self,
		api_key: str,
		model_name: str,
		temperature: float,
		max_output_tokens: int,
		rpm_limit: int,
		tpm_budget: int,
		rpd_limit: int,
		api_base: Optional[str] = None,
		logger=None,
	) -> None:
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
		if api_base is not None and not isinstance(api_base, str):
			raise ValueError("api_base must be a string when provided")

		client_kwargs = {
			"model": model_name,
			"api_key": api_key,
			"temperature": temperature,
			"max_tokens": max_output_tokens,
		}
		if api_base:
			client_kwargs["base_url"] = api_base

		self.llm = ChatOpenAI(**client_kwargs)
		self.ratelimiter = RateLimiter(max_rpm=rpm_limit, max_tpm=tpm_budget, max_rpd=rpd_limit)
		self.logger = logger

	async def explain_page(self, image_bytes: bytes, system_prompt: str) -> str:
		return await self.explain_pages_with_context([("当前页", image_bytes)], system_prompt)

	async def explain_pages_with_context(
		self,
		images_with_labels: list[Tuple[str, bytes]],
		system_prompt: str,
		context_prompt: Optional[str] = None,
	) -> str:
		base_tokens = estimate_tokens(1200)
		image_overhead = len(images_with_labels) * 200
		est = base_tokens + image_overhead
		await self.ratelimiter.wait_for_slot(est)

		full_prompt = system_prompt
		if context_prompt:
			full_prompt = f"{context_prompt}\n\n{system_prompt}"

		content: list[dict] = [{"type": "text", "text": full_prompt}]
		for label, img_bytes in images_with_labels:
			content.append({"type": "text", "text": f"【{label}】"})
			b64 = base64.b64encode(img_bytes).decode("utf-8")
			content.append(
				{
					"type": "image_url",
					"image_url": {"url": f"data:image/png;base64,{b64}"},
				}
			)

		backoff = 1.5
		delay = 1.0
		for attempt in range(5):
			try:
				resp = await asyncio.to_thread(self.llm.invoke, [HumanMessage(content=content)])
				text = resp.content if isinstance(resp.content, str) else resp.content[0].text
				return text.strip()
			except Exception as e:
				if attempt >= 4:
					raise
				if self.logger:
					self.logger(f"LLM 调用失败(第 {attempt + 1} 次)：{e}")
				await asyncio.sleep(delay + random.uniform(0, 0.5))
				delay *= backoff


