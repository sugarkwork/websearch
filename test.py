import trafilatura
from duckduckgo_search import DDGS
import json
import time

from litellm import completion
import dotenv
dotenv.load_dotenv()
from json_repair import repair_json

from sqlite_memory import load_memory, save_memory


api_models = [
    'openai/gpt-4o-2024-08-06', 
    "cohere/command-r-plus-08-2024", 
    "anthropic/claude-3-5-sonnet-20240620",
    "gemini-1.5-pro-002", 
    'openai/gpt-4o-mini-2024-07-18', 
    'cohere/command-r-08-2024', 
    "openai/local-llm"]

api_current_model = 0


safety_settings=[
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]


prompt_word = """
ユーザーの入力を以下の要素で分析して処理します。

1. 省略されていると思われる内容を推測して補い、完全な問い合わせ文章を作成する
2. 製品名やバージョン番号などの明確化（含まれない場合は無しで良い）
3. 考えられる回答案6個（単純な回答、逆説的思考を使った回答、ラテラルシンキングを使った回答、メタ認知思考を使った回答、パラレルシンキングを使った回答、発散思考を使った回答）
4. 回答案をふまえた上で、解決に近づけそうな検索用のキーワード案（文言の言い換えなども含む）を ___search_word_count___ 個
5. 検索キーワードの英語訳"""

prompt_keyword = """
以下のテキストから、検索キーワード（日本語、英語）を抽出してください。
1行につき1つだけ書いてください。
番号付けやコメントや補足は不要です。検索キーワード（日本語、英語）だけを出力してください。

```
___words___
```
"""

prompt_searchword = """
以下の文章から、質問文を抽出してください。
内容を抽出出来ないような内容の場合は、質問の意図を推測して文章を作成してください。
番号やコメントや補足は不要です。質問文のみを出力してください。

```
___words___
```
"""

prompt_reqrusive = """
問い合わせ内容を検索して記事を見つけました。

1. 記事の関連性を10段階（0～10）で評価してください。
2. 問い合わせを解決するために追加調査すべきキーワードが、そのキーワードをまとめてください。
3. 参考にすべきリンクがあれば、そのリンクを抽出してください。
3. 問い合わせへの回答作成に参考になる文面を抜粋してください。文字数に限らず、問い合わせに対する回答作成に参考になる文面を抜粋してください。

コメントは不要です。


回答フォーマット：
```json
{"Relevance rating": x (0~10),
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


検索した記事：
```article
URL: ___URL___
___article___
```
"""

prompt_result = """
問い合わせ内容を検索して記事を見つけました。

問い合わせ内容と記事の内容を良く読み、関連性をよく考慮して、詳細な情報の回答を作成してください。
参考にした際には、引用元のURLを明記してください。

問い合わせ内容：
___question___

記事の内容：
___articles___
"""


def page_to_text(url):
    text = load_memory(url)
    if text is not None:
        return text
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded, output_format="markdown", with_metadata=True, include_links=True)
    save_memory(url, text)
    return text


def search_ddg(query, max_results=3):
    query = query.strip()
    results = load_memory(query)
    if results is not None:
        return results
    
    print(f"[ddg] Searching: {query}")
    
    with DDGS() as ddgs:
        results = list(ddgs.text(
            keywords=query,      # 検索ワード
            region='wt-wt',       # リージョン 日本は"jp-jp",指定なしの場合は"wt-wt"
            safesearch='off',     # セーフサーチOFF->"off",ON->"on",標準->"moderate"
            timelimit=None,       # 期間指定 指定なし->None,過去1日->"d",過去1週間->"w",
                                # 過去1か月->"m",過去1年->"y"
            max_results=max_results         # 取得件数
        ))
    
    save_memory(query, results)
    return results


class Article:
    def __init__(self, url:str, question:str, text:str, rate:int, links:list, keywords:list, ex_articles:list, sub_articles:bool=False):
        self.url = url
        self.question = question
        self.text = text
        self.rate = rate
        self.related_links = links
        self.keywords = keywords
        self.ex_articles = ex_articles
        self.sub_articles = sub_articles

    def rate(self, rate):
        self.rate = rate

    def add_related_link(self, link):
        self.related_links.append(link)

    def add_keyword(self, keyword):
        self.keywords.append(keyword)

    def add_ex_article(self, article):
        self.ex_articles.append(article)


def rate_article(question: str, article: str, base_url:str) -> Article:
    key = f"rate_article_{question}_{article}_{base_url}_{prompt_reqrusive}"

    use_cache = True

    result = load_memory(key)
    if result is not None:
        try:
            article_data = Article(
                url=base_url, 
                question=question,
                text=article, 
                rate=result["Relevance rating"], 
                links=result["Related links to explore"], 
                keywords=result["Keywords to research"], 
                ex_articles=result["Excerpted articles"])
            return article_data
        except:
            use_cache = False
    
    while True:
        try:
            json_data = chat(
                '', 
                prompt_reqrusive.replace("___question___", question).replace("___article___", article).replace("___URL___", base_url), 
                use_cache)
            result = json.loads(repair_json(json_data))
            save_memory(key, result)
            article_data = Article(
                url=base_url, 
                question=question,
                text=article, 
                rate=result["Relevance rating"], 
                links=result["Related links to explore"], 
                keywords=result["Keywords to research"], 
                ex_articles=result["Excerpted articles"])
            
            print(f" - Article: (score {article_data.rate}/10) {article_data.url}")
            #return result["Relevance rating"], result["Related links to explore"], result["Keywords to research"], result["Excerpted articles"]
            return article_data
        except Exception as e:
            print(f"Rate Article Error: {e}")
            use_cache = False


def chat(system: str, message_user:str, use_cache=True) -> str:
    global api_current_model

    memory_key = f"chat_memory_{system}_{message_user}"
    result = load_memory(memory_key)
    if result and use_cache:
        return result
    
    messages = [
        {"content": f"""{system}""", "role": "system"},
        {"content": f"""{message_user}""", "role": "user"},
        ]
    
    result = None
    response = None

    current_model = api_models[api_current_model]

    while not response:
        for _ in range(2):
            try:
                if "gemini" in current_model:
                    response = completion(model=current_model, messages=messages, safety_settings=safety_settings)
                elif "local" in current_model:
                    response = completion(
                        model=current_model,
                        api_key="sk-1234",
                        api_base="http://192.168.1.14:1234/v1",
                        messages=messages,
                    )
                else:
                    response = completion(model=current_model, messages=messages)
                
                break
            except Exception as e:
                print(f"Chat Error {current_model}: {e}")
                response = None
                if "local" in current_model:
                    time.sleep(3)
                else:
                    time.sleep(30)
                continue

        else:
            api_current_model = (api_current_model + 1) % len(api_models)
            current_model = api_models[api_current_model]
            response = None
            print(f"Switching model to {current_model}")
            time.sleep(5)

    result = response.choices[0].message.content
    save_memory(memory_key, result)

    return result


def ai_search(question: str, reqursive_level:int=3, ai_level=0, word_expand=True, ai_search_word=None, search_word_valiation=3, sub_article=False) -> dict[str, Article]:
    key = f"ai_search_{question}_{reqursive_level}_{ai_level}_{prompt_keyword}_{prompt_searchword}_{prompt_word}_{ai_search_word}_{search_word_valiation}_{sub_article}"
    result = load_memory(key)
    if result:
        if isinstance(result, dict):
            return result

    articles = {}
    if word_expand:
        search_words = chat(prompt_word.replace("___search_word_count___", str(search_word_valiation)), question).strip()
        keywords = chat('', prompt_keyword.replace("___words___", search_words)).strip().split("\n")
    else:
        search_words = question
        keywords = [search_words, ]

    print(f"[{ai_level}] [ai search] search_words: {search_words}")
    print(f"[{ai_level}] [ai search] keywords: {keywords}")

    if not ai_search_word:
        ai_search_word = chat('', prompt_searchword.replace("___words___", search_words)).strip()
        print(f"[{ai_level}] [ai search] ai search word: {ai_search_word}")


    def requsive_search(url, level=0):
        if level <= 0:
            return
        url = str(url).strip()
        if url in articles:
            return
        
        page_text = page_to_text(url)
        if not page_text:
            return
        
        article_data = rate_article(ai_search_word, page_text, url)
        articles[article_data.url] = article_data

        if article_data.rate < 7:
            return
        
        if sub_article:
            article_data.sub_articles = True
            articles[article_data.url] = article_data
            return

        sub_article_len = len(article_data.keywords)
        sub_article_count = 0

        for add_keyword in article_data.keywords:
            sub_article_count += 1
            if ai_level <= 0: 
                continue
            print(f"[{ai_level}] ({sub_article_count}/{sub_article_len}) ({level}) Sub Searching (Relation Search) {add_keyword}")
            sub_results = ai_search(
                question=add_keyword, 
                reqursive_level=1, 
                ai_level=ai_level - 1, 
                word_expand=False, 
                sub_article=True)
            articles.update(sub_results)

        for link in article_data.related_links:
            requsive_search(link, level - 1)
    
    keyword_count = 0
    for keyword in keywords:
        if not keyword:
            continue
        keyword = keyword.strip()
        if not keyword:
            continue
        keyword_count += 1
        print(f"[{ai_level}] ({keyword_count}/{len(keywords)}) Searching (Keyword search) {keyword}")
        results = search_ddg(keyword)
        for result in results:
            requsive_search(result['href'], reqursive_level)

    save_memory(key, articles)
    
    return articles



def main():
    question = """
    ギャグで大うけする方法
    """.strip()

    # How many related links should you explore?
    reqursive_level = 2

    # How many related words do you want to search for?
    relation_search_level = 1

    # How many variations of search terms should you create?
    word_validation = 3

    articles = ai_search(question, reqursive_level, relation_search_level, word_validation)

    print("------------------------------------------------------------")

    top_articles = sorted(articles.values(), key=lambda x: x.rate, reverse=True)[:5]

    format_articles = []

    print("Top Articles:")
    for article in top_articles:
        for ex_article in article.ex_articles:
            format_articles.append(f'''
```article
URL: {article.url}
----
{ex_article}
```
'''.strip())
        print("------------------------------------------------------------")

    sub_articles = [article for article in articles.values() if article.sub_articles]

    print("Sub Articles:")
    for article in sub_articles:
        for ex_article in article.ex_articles:
            format_articles.append(f'''
```article
URL: {article.url}
----
{ex_article}
```
'''.strip())

    article_join = "\n\n".join(format_articles)
    prompt = prompt_result.replace("___question___", question).replace("___articles___", article_join)
    result = chat("", prompt)
    with open("prompt.txt", "w", encoding='utf8') as f:
        f.write(prompt)
    print("------------------------------------------------------------")
    print(result)


if __name__ == "__main__":
    main()
