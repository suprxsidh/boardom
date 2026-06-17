from __future__ import annotations

import json
import logging
import random
import re
import requests
from typing import Any

_log = logging.getLogger(__name__)

from yt_automator.models import ContentPackage
from yt_automator.utils.text import normalize_script, sentence_split


class ContentGenerator:
    def __init__(
        self,
        gemini_api_key: str | None,
        ollama_model: str | None = None,
        ollama_base_url: str = "http://localhost:11434",
        gemini_model: str = "gemini-2.0-flash-lite",
    ):
        self.gemini_api_key = gemini_api_key
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.gemini_model = gemini_model
        self._client = None
        if gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=gemini_api_key)
            except Exception as exc:
                _log.warning("google-genai import failed, Gemini disabled: %s", exc)
                self._client = None

    def generate(
        self,
        channel_config: dict[str, Any],
        strategy_key: str,
        strategy_data: dict[str, Any],
        history: list[str],
        reddit_context: dict[str, str] | None = None,
    ) -> ContentPackage:
        prompt_profile = channel_config["prompt_profile"]
        theme = strategy_data["theme"]

        history_text = ""
        if history:
            latest = ", ".join(f'"{t}"' for t in history[-40:])
            history_text = f"Do not repeat these already covered topics: [{latest}]"

        reddit_text = ""
        if reddit_context:
            reddit_text = (
                "Incorporate this community story context while transforming it into an "
                "original narrative. Avoid direct copying. "
                f"Story title: {reddit_context.get('title', '')}. "
                f"Story summary: {reddit_context.get('summary', '')}."
            )

        structure_variant = random.choice([
            ("hook_first", "Open with the single most shocking specific fact (6-10 words, no preamble) → explain the mechanism → close with a personal consequence."),
            ("cold_open", "Drop the listener into the middle of the most dramatic moment — as if it's already happening — then pull back to explain what it is and why it matters."),
            ("jump_to_value", "Lead immediately with the useful/surprising takeaway, then build the evidence backward — explain WHY that takeaway is true, then close with one implication that raises new questions."),
        ])

        prompt = f"""You are a viral narrator — conversational, surprising, ruthlessly specific. You write like someone who just found out something that broke their model of reality and can't stop talking about it. Direct, punchy, never vague, never safe.

Channel: {channel_config['channel_name']}
Theme: {theme}
Strategy key: {strategy_key}
{history_text}
{reddit_text}

BEFORE writing the script, mentally complete these steps:
1. Find ONE counterintuitive fact that contradicts what most people assume
2. Identify the single most surprising micro-detail or mechanism
3. Choose ONE specific number, measurement, or timeframe to anchor the script
4. Only then write the narration

Script rules:
{prompt_profile['script_rules']}

THIS VIDEO'S STRUCTURE — use "{structure_variant[0]}":
{structure_variant[1]}

BAD EXAMPLE (never write like this):
"Scientists have discovered something amazing about cells. Recent research shows they are very complex and interesting. Experts believe this could be important."
→ Vague, passive, hollow. Zero specifics. Reads like a Wikipedia summary.

GOOD EXAMPLE (write like this):
"Your gut bacteria outnumber your cells ten to one — and they produce 90% of your serotonin before your brain ever does. When you feel anxious, your gut fires signals upward through the vagus nerve. You're not just thinking with your brain. You never were."
→ Specific number. Active verb. Short punch then longer reveal. Personal close.

MANDATORY PATTERNS:
- At least ONE specific number, stat, or measurement
- At least ONE high-impact active verb: triggers, fires, rewires, collapses, flips, pulses, costs, seizes, detonates
- Use "turns out" OR "here's the thing" OR "counterintuitive" once — naturally mid-script, not as an opener
- Sentence rhythm: alternate short punches (6-10 words) with medium reveals (12-16 words)
- End with a line the listener will think about later — not a generic CTA

BANNED PHRASES (instant disqualifiers — if any appear, rewrite):
- very, basically, essentially, interesting, complex, fascinating, remarkable, amazing, incredible
- "it is believed", "it was discovered", "scientists have found" (passive voice)
- "in today's world", "in the modern era", "throughout history"
- "notable", "serves as", "aims to", "offers", "features" (AI marketing verbs)
- any sentence starting with "This" followed by a vague noun

For the "title" field: write a YouTube Shorts title — punchy, under 60 characters, capitalise the most shocking word or phrase (e.g. "The Fish That EATS BONE From Inside"). No clickbait that the script doesn't deliver. No full-sentence SEO titles.
For the "description" field: 1-2 sentences max, plain language, no marketing fluff.
For "tags": 8-10 specific topic tags (no generic ones like "video" or "youtube").

Return strict JSON object with keys:
topic, script, title, description, video_query, tags, source_links, scene_queries

For "scene_queries": exactly 5 Pexels video search queries, one per major beat of the script.
Rules: 2-4 concrete words each (nouns + adjectives, no verbs), portrait/vertical footage, visually distinct from each other.
Pattern: beat-1 = establishing environment, beat-2 = main subject/organism/object, beat-3 = mechanism or close-up detail, beat-4 = consequence or scale, beat-5 = final image that matches the emotional close.
Examples of good queries: "dark ocean floor", "glowing anglerfish close up", "bioluminescent bacteria microscope", "deep sea pressure crush", "ocean surface light beam"
Examples of bad queries: "interesting facts", "amazing science", "educational content"

HARD RULES for the "script" field:
1. Raw spoken narration only — exactly what the narrator says out loud, nothing else.
2. No structural labels: no "Hook:", "CTA:", "Intro:", "Outro:", section headers, or the words "hook", "CTA", "call to action" inside the script.
3. No visual references: plays over generic stock footage. Never write "look at this", "as you can see", "notice here", "in this image", "on screen", "what you're seeing". Eyes-closed rule: every sentence must make complete sense to a blind listener.
4. No -ly adverbs. Show the surprise through specific facts, not adjectives.
5. No passive voice constructions.""".strip()

        if self.ollama_model:
            try:
                payload = self._generate_with_ollama(prompt)
                return self._to_package(payload)
            except Exception as exc:
                _log.warning("Ollama generation failed, trying next backend: %s", exc)

        if self._client is not None:
            try:
                from google.genai import types as _gtypes
                response = self._client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config=_gtypes.GenerateContentConfig(
                        temperature=1.1,
                        top_p=0.95,
                    ),
                )
                payload = self._parse_json(response.text)
                return self._to_package(payload)
            except Exception as exc:
                _log.warning("Gemini generation failed, using fallback: %s", exc)

        return self._fallback_package(channel_config, strategy_data, reddit_context)

    def _generate_with_ollama(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("response", "{}").strip()
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in LLM response: {cleaned[:200]!r}")
        return json.loads(match.group())

    @staticmethod
    def _to_package(payload: dict[str, Any]) -> ContentPackage:
        script = normalize_script(payload.get("script", ""))
        script = " ".join(sentence_split(script))

        description = str(payload.get("description", "")).strip()
        if "#Shorts" not in description and "#shorts" not in description:
            description = description + "\n\n#Shorts"

        tags = [str(item) for item in payload.get("tags", [])][:11]
        if not any(t.lower() == "shorts" for t in tags):
            tags.append("shorts")

        video_query = str(payload.get("video_query", "interesting visuals")).strip()
        raw_scene_queries = payload.get("scene_queries", [])
        scene_queries = [
            str(q).strip()[:80] for q in raw_scene_queries
            if str(q).strip()
        ][:6]
        if not scene_queries:
            scene_queries = [video_query] * 5

        return ContentPackage(
            topic=str(payload.get("topic", "Untitled topic")).strip(),
            script=script,
            title=str(payload.get("title", "Untitled short")).strip(),
            description=description,
            video_query=video_query,
            tags=tags,
            source_links=[str(item) for item in payload.get("source_links", [])][:8],
            style_variant=str(payload.get("style_variant", "default")),
            scene_queries=scene_queries,
        )

    @staticmethod
    def _fallback_package(
        channel_config: dict[str, Any],
        strategy_data: dict[str, Any],
        reddit_context: dict[str, str] | None,
    ) -> ContentPackage:
        topic = strategy_data["theme"]
        script = (
            f"Quick deep dive on {topic}. "
            "This starts with a claim almost everyone gets wrong. "
            "Most people miss this crucial detail, but it completely changes the entire story. "
            "The middle of this story is where the explanation gets counterintuitive, "
            "because the obvious answer fails when you look at real evidence. "
            "Scientists and researchers have documented this for decades, "
            "yet it rarely makes it into mainstream education or popular discussion. "
            "By the end, one small detail flips the conclusion and makes the whole topic "
            "easier to understand and remember. "
            "Follow for the next short if you want more high-signal facts without the fluff."
        )
        fallback_query = strategy_data.get("default_query", "cinematic vertical background")
        return ContentPackage(
            topic=topic,
            script=normalize_script(script),
            title=f"{channel_config['channel_name'].title()} short: {topic[:48]}",
            description=(
                f"{topic}. Built for quick learning and retention. "
                f"#{channel_config['channel_name']} #shorts #learn"
            ),
            video_query=fallback_query,
            tags=[channel_config["channel_name"], "shorts", "education", "viral"],
            source_links=[],
            style_variant="fallback",
            scene_queries=[fallback_query] * 5,
        )
