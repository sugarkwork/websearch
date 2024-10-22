# websearch

テスト実装です。

以下の機能で構成されています。

1. ウェブページのテキスト抽出 (page_to_text 関数)
2. DuckDuckGoでの検索 (search_ddg 関数)
3. 再帰的な検索と情報抽出 (requsive_search 関数、推測)
4. AI による検索と分析 (ai_search 関数、推測)
5. メイン処理 (main 関数)


処理の流れとして

1. 受け取った情報をキーワードに変換
2. キーワードを全部検索していく
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

main 関数の最初にある question に検索ワードを入れます。

    def main():
        question = """
        ギャグで大うけする方法
        """.strip()
