import os
import gradio as gr
import asyncio
from typing import Tuple, AsyncGenerator
import logging
import markdown
import json
import traceback
from datetime import datetime

import trafilatura
from duckduckgo_search import DDGS
from googleapiclient.discovery import build

from chat_assistant import ChatAssistant
from pmem.async_pmem import PersistentMemory

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


prompt_analyze_keyword = """
# 命令
ユーザーの入力を以下の要素で分析して処理します。
コメントや補足は不要です。

1. 省略されていると思われる内容を推測して補い、完全な問い合わせ文章を作成する
2. 解決に近づけそうな検索用のキーワード案（文言の言い換えなども含む）を ___search_word_count___ 個
3. 検索キーワードの英語訳

# 出力例
```json
{
"fulltext question": "question",
"search words": ["search word1", "search word2"],
"search words english translation": ["search word1", "search word2"]
}
```
"""

prompt_page_analyze = """
問い合わせ内容を検索して記事を見つけました。

1. 問い合わせ内容および関連キーワードと、記事の関連性を10段階 (0 - 10)で評価してください。
2. 問い合わせを解決するために追加調査すべきキーワードがあれば、そのキーワードを優先度の高い順に ___search_word_count___ 個抽出してください。
3. 参考にすべきリンクがあれば、そのリンクを優先度の高い順に ___search_word_count___ 個抽出してください。
4. 問い合わせへの回答作成に参考になる文面を抜粋してください。文字数に限らず、問い合わせおよびキーワードに対する説明および回答作成に参考になる文面を抜粋してください。

出力にコメントや補足は不要です。

回答フォーマット：
```json
{"Relevance rating": x (0 - 10),
"Related links to explore":
[
"https://...",
"https://..."
],
"Keywords to research":
[
"keyword1",
"keyword2"
],
"Excerpted articles":
[
"Excerpted article 1",
"Excerpted article 2",
"Excerpted article 3"
]
}
```

問い合わせ内容：
```question
___question___
```

詳しく知りたい関連キーワード：
```question
___keyword___
```

検索した記事：
```article
URL: ___URL___
___article___
```
"""

prompt_generate_answer = """
問い合わせ内容を検索して記事を見つけました。

問い合わせ内容と記事の内容を良く読み、関連性をよく考慮して、詳細な情報の回答を作成してください。
参考にした際には、引用元のURLを明記してください。

問い合わせ内容：
___question___

記事の内容：
___articles___
"""


class QueryAnalyzeResult:
    def __init__(self, result, original_query) -> None:
        self.original_query = original_query
        self.fulltext_question = result.get('fulltext question', "")
        self.search_words = result.get('search words', [])
        self.search_words_english = result.get('search words english translation', [])


class ArticleAnalyzeResult:
    def __init__(self, result) -> None:
        self.relevance_rating = result.get('Relevance rating', 0)
        self.related_links = result.get('Related links to explore', [])
        self.keywords = result.get('Keywords to research', [])
        self.excerpted_articles = result.get('Excerpted articles', [])
        self.question = result.get('question', "")
        self.url = result.get('url', "")
        self.article = result.get('article', "")
        self.keyword = result.get('keyword', "")


class SearchEngine:
    """検索エンジンのクラス"""

    def __init__(self, engine: str) -> None:
        self.engine = engine.strip().lower()
        self.assistant = ChatAssistant()
        self.memory = PersistentMemory("search_cache.db")

    async def answer(self, question: str, articles: list[ArticleAnalyzeResult]) -> str:

        average_score = sum([article.relevance_rating for article in articles]) / len(articles)

        article_text = ""
        for article in articles:
            article_text += f"URL: {article.url}\n{article.excerpted_articles}\n\n"
        
        logger.info(f"Answering: {question}")
        logger.info(f"Articles: {article_text}")

        result = await self.assistant.chat(
            "", 
            prompt_generate_answer.replace('___question___', question).replace('___articles___', article_text), 
            json_mode=False)
        
        return result

    async def analyze_keyword(self, query: str, keywords_count:int=3) -> QueryAnalyzeResult:
        result = await self.assistant.chat(prompt_analyze_keyword.replace('___search_word_count___', str(keywords_count)), query, json_mode=True)
        return QueryAnalyzeResult(result, query)
    
    async def analyze(self, question: str, article_url: str, keyword:str, keywords_count:int=3) -> ArticleAnalyzeResult:
        article_text = await self.page_to_text(article_url)
        if article_text is None:
            return None
        result = await self.assistant.chat(prompt_page_analyze
            .replace('___question___', question)
            .replace('___search_word_count___', str(keywords_count))
            .replace('___article___', article_text)
            .replace('___keyword___', keyword)
            .replace('___URL___', article_url), 
            article_url, json_mode=True)
        result["question"] = question
        result["url"] = article_url
        result["article"] = article_text
        result["keyword"] = keyword
        return ArticleAnalyzeResult(result)

    async def page_to_text(self, url:str) -> str:
        logger.info(f"Fetching: {url}")
        text = await self.memory.load(url)
        if text is not None:
            return text
        
        loop = asyncio.get_event_loop()
        downloaded = await loop.run_in_executor(None, 
                                                trafilatura.fetch_url,
                                                url)
        text = await loop.run_in_executor(None, 
                                            trafilatura.extract,
                                            downloaded,   # filecontent: Any,
                                            url,          # url: Any | None = None,
                                            None,     # record_id: Any | None = None,
                                            False,    # no_fallback: bool = False,
                                            False,    # favor_precision: bool = False,
                                            False,    # favor_recall: bool = False,
                                            True,     # include_comments: bool = True,
                                            "markdown",   # output_format: str = "txt",
                                            False,    # tei_validation: bool = False,
                                            None,    # target_language: Any | None = None,
                                            True,    # include_tables: bool = True,
                                            False,    # include_images: bool = False, 
                                            False,    # include_formatting: bool = False,
                                            True,    # include_links: bool = False,
                                            False,    # deduplicate: bool = False,
                                            None,    # date_extraction_params: Any | None = None,
                                            True,    # with_metadata: bool = False,
                                            )

        
        await self.memory.save(url, text)
        return text

    async def search(self, query:str, max_results:int=3) -> list[dict[str, str]]:
        logger.info(f"Searching: {query}")
        key = f"search_{query}_{max_results}_{self.engine}"
        query = query.strip()
        results = await self.memory.load(key)
        if results is not None:
            logger.info(f"Search results found in memory: {query}")
            return results
        
        def ddg_search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    keywords=query,
                    region='wt-wt',
                    safesearch='off',
                    timelimit=None,
                    max_results=max_results
                ))
        
        def ggl_search():
            service = build(
                "customsearch", "v1", developerKey=os.getenv("GOOGLE_SEARCH_API_KEY")
            )

            res = (
                service.cse().list(
                    fields="items(title,snippet,link)",
                    q=query,
                    cx=os.getenv("GOOGLE_SEARCH_ENGUINE_ID"),
                ).execute()
            )

            return res.get('items', [])
        
        loop = asyncio.get_event_loop()

        results = []
        if self.engine == "duckduckgo":
            results = await loop.run_in_executor(None, ddg_search)
        elif self.engine == "google":
            results = await loop.run_in_executor(None, ggl_search)
        else:
            logger.error(f"Unknown search engine: {self.engine}")
        
        results = results[:max_results]
        
        await self.memory.save(key, results)
        logger.info(f"Search results saved to memory: {query}")
        return results


class ProgressTracker:
    """進捗追跡クラス"""
    def __init__(self):
        self.progress = 0
        self.status = ""

    def update(self, progress: float, status: str):
        self.progress = progress
        self.status = status


class SearchInterface:
    def __init__(self):
        self.search_engine = None
        self.progress_tracker = ProgressTracker()

    async def process_search(
        self, query: str, 
        keywords_count: int, 
        max_depth: int, 
        max_threads: int, 
        max_articles: int, 
        article_quality: int, 
        model: str,
        engine: str
    ) -> AsyncGenerator[Tuple[float, str, str], None]:
        
        self.search_engine = SearchEngine(engine)

        try:
            yield 0.0, "検索を開始します...", ""
            await asyncio.sleep(0.1)

            # モデルの変更
            yield 0.0, f"使用AIモデル: {model}", ""
            self.search_engine.assistant.model_manager.change_model(model)
            
            yield 0.1, "検索キーワードを解析...", ""
            analyze_user = await self.search_engine.analyze_keyword(query, keywords_count)
            yield 0.1, "検索キーワードを解析完了", ""

            yield 0.1, f"分析結果 : {analyze_user.fulltext_question}", ""
            yield 0.1, f"検索キーワード : {analyze_user.search_words + analyze_user.search_words_english}", ""

            search_semaphore = asyncio.Semaphore(max_threads)
            analyze_semaphore = asyncio.Semaphore(max_threads)

            # async analyze article results
            articles = []

            async def search_and_analyze(keyword, depth):
                await asyncio.sleep(0.1)
                if depth > max_depth:
                    return
                if len(articles) >= max_articles:
                    return

                yield 0.2 + (len(articles) / max_articles / 2), f"検索中: {keyword} (深さ: {depth})", ""

                async with search_semaphore:
                    results = await self.search_engine.search(keyword)

                yield 0.2 + (len(articles) / max_articles / 2), f"検索完了: {keyword} - {len(results)}件の結果", ""

                for search_result in results:
                    url = search_result.get('href', search_result.get('link', ""))
                    async for progress, status, result in analyze_and_follow(url, keyword, depth+1):
                        yield progress, status, result

            async def analyze_and_follow(url, keyword, depth):
                await asyncio.sleep(0.1)
                if depth > max_depth:
                    return
                if len(articles) >= max_articles:
                    return

                yield 0.3 + (len(articles) / max_articles / 2), f"記事を解析中: {url} (深さ: {depth})", ""

                async with analyze_semaphore:
                    try:
                        analyzed_url = await self.search_engine.analyze(analyze_user.fulltext_question, url, keyword)
                        if analyzed_url is not None:
                            if analyzed_url.relevance_rating >= article_quality:
                                articles.append(analyzed_url)
                            yield 0.3 + (len(articles) / max_articles / 2), f"記事の解析完了: {url}\nスコア ( {analyzed_url.relevance_rating} / 10 )", ""
                            if len(articles) >= max_articles:
                                return
                        else:
                            logger.error(f"url none: {url}")
                            yield 0.3 + (len(articles) / max_articles / 2), f"記事の解析失敗: {url}", ""
                            return
                    except Exception as e:
                        logger.error(f"記事の解析でエラーが発生: {str(e)}")
                        yield 0.3 + (len(articles) / max_articles / 2), f"記事の解析エラー: {url} - {str(e)}", ""
                        return

                for keyword in analyzed_url.keywords:
                    async for progress, status, result in search_and_analyze(keyword, depth+1):
                        yield progress, status, result
                for link in analyzed_url.related_links:
                    async for progress, status, result in analyze_and_follow(link, keyword, depth+1):
                        yield progress, status, result

            # 初期のキーワードで検索と解析を開始
            for keyword in (analyze_user.search_words + analyze_user.search_words_english):
                async for progress, status, result in search_and_analyze(keyword, 1):
                    yield progress, status, result

            yield 0.8, "集計中...", ""
            yield 0.8, f"検索記事数: {len(articles)}", ""

            yield 0.9, "検索結果を整理中...", ""
            result = await self.search_engine.answer(analyze_user.fulltext_question, articles)

            # 完了
            yield 1.0, "検索完了!", result

        except Exception as e:
            logger.error(f"検索処理でエラーが発生: {str(e)}")
            yield 0.0, f"エラーが発生しました: {str(e)}", ""
            logger.error(traceback.format_exc())


async def search(
        query: str, 
        keywords_count: int, 
        depth: int, 
        threads: int, 
        articles: int, 
        article_quality: int, 
        model: str,
        search_engine: str,
        output_format:str="html"
        ) -> AsyncGenerator[list, None]:

    search_interface = SearchInterface()

    outputs = []
    status_log = []
    async for progress, status, result in search_interface.process_search(
        query, keywords_count, depth, threads, articles, article_quality, model, search_engine):
        status_log.append(status)
        if output_format == "html":
            output_data = "<hr />" + markdown.markdown(result) + "<hr />"
        else:
            output_data = result
        outputs = [
            max(0, min(100, progress * 100)),  # progress_bar の値
            '\n'.join(status_log),         # progress_text の値
            output_data  # result_output の値
        ]
        yield outputs


async def search_simple(query:str, model="openai/gpt-4o-2024-08-06", output_format="html") -> str:
    async for data in search(
        query=query, 
        keywords_count=3, 
        depth=3, 
        threads=2, 
        articles=3, 
        article_quality=7, 
        model=model, 
        search_engine="DuckDuckGo",
        output_format=output_format):
        pass
    
    return data[2]


async def main(query:str):
    result = await search_simple(query=query, output_format="makrdown")
    print("-----------------")
    print(result)


if __name__ == "__main__":
    asyncio.run(main("Pythonについて教えて"))


