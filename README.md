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
# sample

    ギャグで大うけする方法

# result

ギャグで大うけする方法について、以下の記事から得た情報を参考に、関連性の高い助言を提供します。

### 1. スラップスティック（物理的ギャグ）
スラップスティックは、誇張された身体的な動作を使って笑いを引き出すスタイルのコメディーです。イタリアの16世紀から始まった「commedia dell'arte」が起源で、現代では『The Three Stooges』『Mr. Bean』などがその例です。このスタイルを活用するには、物理的な動作を大げさにしたり、予 想外の失敗を組み込むことが有効です。
- 参考URL: [Slapstick - Wikipedia](https://en.wikipedia.org/wiki/Slapstick)

### 2. コミックタイミング（タイミングの重要性）
ギャグではタイミングが非常に重要です。対話の流れを読み、最も効果的な瞬間にギャグを入れることで、より大きな笑いを誘発します。間を活かすことで、観客にジョークのサブテキストや状況を認識させる時間を与えることができます。
- 参考URL: [The Art and Science of Comedic Timing](https://www.thecut.com/2017/05/the-art-and-science-of-comedic-timing.html)

### 3. 観客の理解と調整
笑いを引き出すためには、観客の文化、年齢、雰囲気を理解し、これに合わせたギャグを提供することが重要です。観客の反応を観察し、必要に応じて次のジョークを調整することで、より効果的なパフォーマンスが可能になります。
- 参考URL: [How to Write Stand-Up Comedy Jokes](https://creativestandup.com/how-to-write-stand-up-comedy-jokes/)

### 4. ユーモアのスタイルとセンス
ユーモアは、相手を傷つけずに楽しませる能力です。ユーモアでは、品のあるジョークや気遣いが重要で、相手の興味や感情を考慮して言葉を選びます。観客を笑顔にさせるような環境を整えることも重要です。
- 参考URL: [Humor - Psychology Today](https://www.psychologytoday.com/us/basics/humor)

### 5. スキルの向上と練習
ギャグは練習と実践によって磨かれます。小さなジョークから始めて、徐々に大きな観客に向けて披露していくことで、フィードバックを受け入れながら改善します。芸人のように会話のネタをストックしておくと、即興で面白い話ができるようになります。
- 参考URL: [How to Be Funny - Science of People](https://www.scienceofpeople.com/how-to-be-funny/)

これらの情報を活かして、あなた自身のスタイルを見つけ、場に応じた適切なギャグやユーモアを提供することで、より多くの笑いを引き出すことができるでしょう。
