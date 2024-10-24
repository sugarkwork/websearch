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

    python3.10 -m venv venv
    venv/scripts/activate
    pip install -r requirements.txt
    python newui.py

ブラウザで [localhost:7860](http://localhost:7860/) を開きます。
