# websearch

perplexity っぽい実装を目指したテストコードです。

処理の流れ：

1. 受け取った情報をキーワードに変換
2. キーワードを検索していく
3. 見つけたページが質問にマッチしているかどうかを判定
4. 見つけたページから関連リンクを見つけて、関連性がある場合は取得
5. 見つけたページ上の関連キーワードを見つけて、検索対象とする
6. 関連リンクの取得および、関連キーワードを再帰的に検索（パラメータで最大数を指定）
7. 最終的に役立つ記事から役立つ部分を抽出
8. 役立つと思われる情報をまとめて AI に渡して、ユーザーの質問に答えてもらう

# 使い方
.env ファイルを作って以下のように API キーを記載します。

    GOOGLE_API_KEY="AIzaSy...."
    GEMINI_API_KEY="AIzaS...."
    OPENAI_API_KEY="sk-fn4d..."
    ANTHROPIC_API_KEY="sk-ant-api0..."
    COHERE_API_KEY="QRu7..."
    AWS_ACCESS_KEY_ID="AK..."
    AWS_SECRET_ACCESS_KEY="Z0wT..."

使う AI の API キーだけでいいです。

手動で起動する場合。

    python3.10 -m venv venv
    venv/scripts/activate
    pip install -r requirements.txt
    python newui.py

Python が入っている環境で自動構築して使用する場合（Windows）

    webui.bat

ブラウザで [localhost:7860](http://localhost:7860/) を開きます。

# パッケージとして使う

.env に API キーを設定した上で、インストール

    pip install -U git+https://github.com/sugarkwork/websearch

こんな感じで、簡単に AI 検索が利用できる。

    import asyncio
    from ai_web_search.searcher import search_simple
    
    async def main(query:str):
        result = await search_simple(query=query, output_format="makrdown")
        print("-----------------")
        print(result)
    
    if __name__ == "__main__":
        asyncio.run(main("Python"))

このコードの実行結果例:

    Pythonについての基本的な情報を以下にまとめます。
    
    ### Pythonとは
    - **開発者と開発年**: Pythonは1991年にオランダ人のグイド・ヴァン・ロッサム氏によって開発された汎用的なプログラミング言語です。この言語はそのシンプルさと可 読性の高さで知られています。
      - 出典: [Qiitaの記事](https://qiita.com/AI_Academy/items/b97b2178b4d10abe0adb)
    
    ### Pythonの特徴
    - **シンプルさと効率性**: Pythonの大きな特徴は、少ないコードでシンプルに記述できることです。これにより、コードの可読性が高く、初心者にも優しい言語となって います。
    - **多様な用途**: Pythonは人工知能技術の開発、Web開発、業務自動化ツールの作成など、幅広い分野で利用されています。1つの言語で多くのことを実現できるのが魅力 です。
      - 出典: [Qiitaの記事](https://qiita.com/AI_Academy/items/b97b2178b4d10abe0adb)
    
    ### 学習環境とリソース
    - **Google Colaboratory (Colab)**: Pythonを学ぶ際の便利なツールとして、Googleが提供するGoogle Colaboratory (Colab)があります。これはWebブラウザからPythonコードを実行できるサービスで、無料で利用可能です。手間のかかる環境設定が不要で、プログラミング未経験者でもすぐに始められます。
      - 出典: [Python入門講座](https://www.python.jp/train/index.html)
    
    ### 学習の目的
    - **基礎知識の取得**: プログラミング未経験者を対象に、Pythonプログラミングに必要な最低限の操作方法と基礎知識を習得することを目的としています。
      - 出典: [Python入門講座](https://www.python.jp/train/index.html)
    
    これらの情報を元に、Pythonは多様な場面で活用できる強力なプログラミング言語であり、多くの学習リソースやツールを活用することで、効果的に習得することが可能で す。
