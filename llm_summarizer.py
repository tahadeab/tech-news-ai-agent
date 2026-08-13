"""
llm_summarizer.py
-----------------
وحدة تلخيص المقالات باستخدام LLM API متوافق مع واجهة OpenAI.
- يدعم OpenAI API الرسمي وأي مزود متوافق (Groq, OpenRouter, Together, LM Studio...)
- يعمل عبر proxy API المدمج في بيئة التطوير عند عدم وجود مفتاح
- يلخص كل مقالة ثم يولّد مقدمة تحليلية للتقرير
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = {"Arabic": """أنت محرر تقني محترف. مهمتك تلخيص المقالات التقنية بلغة عربية سليمة وواضحة.
التزم بما يلي:
- التلخيص يجب أن يكون بالعربية الفصحى ما لم يُطلب غير ذلك
- لا تضف معلومات غير موجودة في المقال الأصلي
- احتفظ بالروابط والأسماء التقنية كما هي
- اكتب بأسلوب صحفي موجز ومفيد""", "English": """You are a professional tech editor. Your task is to summarize technical articles in clear, natural English.
Follow these rules:
- Write in clear, journalistic English
- Do not add information not present in the original article
- Keep links and technical names as they are
- Be concise and informative"""}

SUMMARY_PROMPT = {"Arabic": """لخّص المقال التالي في 2-3 جمل مركّزة بالعربية، مبرزة الفكرة الرئيسية والأهمية التقنية:

{article}""", "English": """Summarize the following article in 2-3 focused sentences in English, highlighting the main idea and its technical significance:

{article}"""}

INTRO_PROMPT = {"Arabic": """بناءً على المقالات التقنية التالية التي نُشرت اليوم، اكتب مقدمة تحليلية موجزة (3-5 جمل) للتقرير اليومي،
تبرز أبرز التوجهات والمواضيع التقنية التي طرأت اليوم:

{articles}""", "English": """Based on the following technical articles published today, write a brief analytical introduction (3-5 sentences) for the daily report,
highlighting the most notable trends and topics:

{articles}"""}


class LLMSummarizer:
    """ملخّص يعتمد على أي API متوافق مع واجهة OpenAI Chat Completions.
    يدعم العربية (Arabic) والإنجليزية (English) أو كليهما (both)."""

    def __init__(self, llm_config: dict, language: str = "both"):
        self.base_url = llm_config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        self.api_key = llm_config.get("api_key", "")
        self.model = llm_config.get("model", "gpt-4o-mini")
        self.max_tokens = llm_config.get("max_tokens", 2000)
        self.temperature = llm_config.get("temperature", 0.3)
        # إعداد اللغة: Arabic / English / both
        self.language = language
        if self.language == "both":
            self.languages = ["Arabic", "English"]
        else:
            self.languages = [self.language]

    def _prompts(self, lang: str) -> tuple[str, str, str]:
        return SYSTEM_PROMPT[lang], SUMMARY_PROMPT[lang], INTRO_PROMPT[lang]

    def _complete(self, system: str, user: str, retries: int = 3) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # ملاحظة: نرسل max_completion_tokens (متوافقة مع OpenAI)؛
        # المزودات الأخرى المتوافقة مع OpenAI تقبلها عادةً،
        # وإلا غيّرها إلى max_tokens في config عند الحاجة.
        payload = {
            "model": self.model,
            "max_completion_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content is None:
                    raise RuntimeError(f"استجابة فارغة (finish={data['choices'][0].get('finish_reason')})")
                return content.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"محاولة {attempt}/{retries} فشلت: {e}")
                time.sleep(2 * attempt)

        raise RuntimeError(f"فشل استدعاء LLM بعد {retries} محاولات: {last_error}")

    def summarize_article(self, article: dict, language: str = None) -> str:
        """تلخيص مقالة؛ إذا كانت اللغة both يعيد قاموس {'Arabic': ..., 'English': ...}."""
        lang = language or self.language
        article_text = (
            f"Source/المصدر: {article['source']}\n"
            f"Title/العنوان: {article['title']}\n"
            f"Description/الوصف: {article['description']}\n"
            f"Link/الرابط: {article['link']}"
        )

        if lang == "both":
            result = {}
            for l in self.languages:
                system, summary_prompt, _ = self._prompts(l)
                result[l] = self._complete(
                    system, summary_prompt.format(article=article_text)
                )
            return result
        system, summary_prompt, _ = self._prompts(lang)
        return self._complete(system, summary_prompt.format(article=article_text))

    def generate_report_intro(self, articles_with_summaries: list[dict],
                              language: str = None) -> str:
        """توليد مقدمة تحليلية للتقرير؛ إذا كانت اللغة both تعيد قاموساً."""
        lang = language or self.language

        def _block_for(l: str) -> str:
            def _summary(a: dict) -> str:
                s = a.get("summary", "")
                if isinstance(s, dict):
                    return s.get(l, "No summary available")
                return s or "No summary available"
            return "\n\n---\n".join(
                f"Title/العنوان: {a['title']}\nSummary/الملخص: {_summary(a)}"
                for a in articles_with_summaries[:15]
            )

        if lang == "both":
            result = {}
            for l in self.languages:
                system, _, intro_prompt = self._prompts(l)
                result[l] = self._complete(system, intro_prompt.format(articles=_block_for(l)))
            return result
        system, _, intro_prompt = self._prompts(lang)
        return self._complete(system, intro_prompt.format(articles=_block_for(lang)))


def summarize_all(summarizer: LLMSummarizer, articles: list[dict],
                  workers: int = 6) -> list[dict]:
    """تلخيص جميع المقالات بالتوازي (أسرع بكثير) وإضافة الملخص لكل مقالة."""

    def _fallback(article: dict) -> str | dict:
        lang = summarizer.language
        if lang == "both":
            snippet = article["description"][:200]
            return {"Arabic": f"[تعذر التلخيص — {snippet}]", "English": f"[Summary unavailable — {snippet}]"}
        return "[تعذر التلخيص — " + article["description"][:200] + "]" if lang == "Arabic" \
            else "[Summary unavailable — " + article["description"][:200] + "]"

    def _summarize(item: tuple[int, dict]) -> dict:
        idx, article = item
        try:
            article["summary"] = summarizer.summarize_article(article)
            logger.info(f"[{idx + 1}/{len(articles)}] ✓ {article['title']}")
        except Exception as e:
            logger.error(f"[{idx + 1}/{len(articles)}] ✗ Failed to summarize '{article['title']}': {e}")
            article["summary"] = _fallback(article)
        return article

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_summarize, enumerate(articles)))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = json.load(open("config.json", encoding="utf-8"))
    summarizer = LLMSummarizer(config["llm"])
    test_article = {
        "source": "TechCrunch",
        "title": "OpenAI announces new multimodal model",
        "description": "OpenAI today unveiled its latest multimodal model with improved reasoning capabilities...",
        "link": "https://example.com/article",
    }
    print(summarizer.summarize_article(test_article))
