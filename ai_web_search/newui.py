import os
import gradio as gr
import asyncio
from typing import Tuple, AsyncGenerator
import logging
import markdown
import json
import traceback
from datetime import datetime

from duckduckgo_search import DDGS
from googleapiclient.discovery import build

from pmem.sync_pmem import PersistentMemory
from pmem.async_pmem import PersistentMemory as AsyncPersistentMemory

from . import searcher


# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
mem = PersistentMemory("newui.db")
amem = AsyncPersistentMemory("newui.db")


def create_ui() -> gr.Interface:
    """Gradio UIの構築"""
    with gr.Blocks() as interface:
        with gr.Row():
            # 左カラム（進捗情報）
            with gr.Column(scale=1):
                models = json.load(open("models.json"))
                # drop down list
                model_dropdown = gr.Dropdown(
                    label="使用モデル",
                    choices=models,
                    value=mem.load("setting_current_model", models[0]),
                    interactive=True
                )

                engines = ["DuckDuckGo", ]
                if os.environ.get("GOOGLE_SEARCH_ENGUINE_ID") is not None:
                    engines.append("Google")

                engine_dropdown = gr.Dropdown(
                    label="検索エンジン",
                    choices=engines,
                    value=mem.load("setting_current_engine", engines[0]),
                    interactive=True
                )

                keywords_bar = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=mem.load("setting_keywords_count", 3),
                    step=1,
                    label="検索キーワード数",
                )
                depth_bar = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=mem.load("setting_depth", 2),
                    step=1,
                    label="リンクの深さ",
                )
                threads_bar = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=mem.load("setting_threads", 2),
                    step=1,
                    label="最大平行処理数",
                )
                articles_bar = gr.Slider(
                    minimum=1,
                    maximum=50,
                    value=mem.load("setting_articles", 5),
                    step=1,
                    label="参照記事数",
                )
                article_quality_bar = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=mem.load("setting_article_quality", 7),
                    step=1,
                    label="参照する記事の関連度",
                )
                hr = gr.HTML("<hr />")
                progress_bar = gr.Slider(
                    minimum=0,
                    maximum=100,
                    value=0,
                    label="進捗",
                    interactive=False,
                )
                progress_text = gr.Textbox(
                    label="進捗状況",
                    interactive=False
                )

            # 右カラム（検索関連）
            with gr.Column(scale=3):
                query_input = gr.Textbox(
                    label="検索テキスト",
                    placeholder="検索したい内容を入力してください...",
                    lines=3
                )
                search_button = gr.Button("検索開始")
                result_output = gr.HTML()
        
            with gr.Row():
                new_search_button = gr.Button("新規検索")
                gr.HTML("<hr />")
                history_list = gr.DataFrame(
                    headers=["ID", "検索クエリ", "結果", "検索日時"],
                    label="検索履歴"
                )

            def clear_inputs():
                return "", "", 0, ""

            async def select_history(evt: gr.SelectData):
                history = mem.load("search_history", [])
                selected_row = history[evt.index[0]]
                return {
                    query_input: selected_row[0],
                    result_output: "<hr />" + markdown.markdown(selected_row[1]) + "<hr />"
                }

            # イベントハンドラの設定
            new_search_button.click(
                fn=clear_inputs,
                outputs=[query_input, result_output, progress_bar, progress_text]
            )

            history_list.select(
                fn=select_history,
                outputs=[query_input, result_output]
            )

        async def load_history():
            history = await amem.load("search_history", [])
            return history

        async def save_history(query, result):
            await amem.save("search_history", 
                            [(query, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))] + 
                            await amem.load("search_history", []))
            
        async def search_handler(
                query: str, 
                keywords_count: int, 
                depth: int, 
                threads: int, 
                articles: int, 
                article_quality: int, 
                model: str,
                search_engine: str
                ) -> AsyncGenerator[list, None]:
            await amem.save("setting_current_model", model)
            await amem.save("setting_keywords_count", keywords_count)
            await amem.save("setting_depth", depth)
            await amem.save("setting_threads", threads)
            await amem.save("setting_articles", articles)
            await amem.save("setting_article_quality", article_quality)
            await amem.save("setting_current_engine", search_engine)

            outputs = []
            final_result = ""
            async for progress, status, result in searcher.search(
                query, keywords_count, depth, threads, articles, article_quality, model, search_engine):
                final_result = result
                outputs = [
                    int(progress),  # progress_bar の値
                    status,         # progress_text の値
                    result  # result_output の値
                ]
                yield outputs
            
                        # 検索完了時に履歴を保存
            if progress >= 1.0:
                await save_history(query, final_result)

        search_button.click(
            fn=search_handler,
            inputs=[query_input, keywords_bar, depth_bar, threads_bar, articles_bar, article_quality_bar, model_dropdown, engine_dropdown],
            outputs=[progress_bar, progress_text, result_output]
        )

        interface.load(
            fn=load_history,
            outputs=history_list
        )

    return interface

if __name__ == "__main__":
    interface = create_ui()
    interface.launch(
        server_name="127.0.0.1",
        server_port=3939,
        debug=True,
        auth=("username", "password")
    )
