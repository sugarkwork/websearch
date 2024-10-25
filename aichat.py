import time
import os
import asyncio
import litellm  
from litellm import completion, acompletion
from sqlite_memory_async import load_memory, save_memory
import json
from json_repair import repair_json
import dotenv
dotenv.load_dotenv()


api_models = []

if not os.path.exists("models.json"):
    api_models = [
        "openai/gpt-4o-2024-08-06",
        "openai/gpt-4o-mini-2024-07-18",
        "anthropic/claude-3-5-sonnet-20241022",
        "anthropic/claude-3-5-sonnet-20240620",
        "gemini/gemini-1.5-pro-002",
        "cohere/command-r-plus-08-2024",
        "cohere/command-r-08-2024",
        "openai/local-lmstudio"
    ]
    with open("models.json", "w") as f:
        json.dump(api_models, f)

with open("models.json", "r") as f:
    api_models = json.load(f)

api_current_model = 0


def change_model(model_name: str) -> str:
    global api_current_model
    api_current_model = api_models.index(model_name)
    return api_models[api_current_model]


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

async def chat(system: str, message_user:str, use_cache=True, json_mode=False) -> str:
    global api_current_model

    memory_key = f"chat_memory_{system}_{message_user}_json_{json_mode}"
    result = await load_memory(memory_key)
    if result and use_cache:
        if json_mode and isinstance(result, str):
            result = json.loads(repair_json(result))
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
            await asyncio.sleep(0.1)

            try:
                print(f"Chatting with {current_model}")
                if "gemini" in current_model:
                    response = await acompletion(model=current_model, messages=messages, safety_settings=safety_settings)
                elif "local" in current_model:
                    response = await acompletion(
                        model=current_model,
                        api_key="sk-1234",
                        api_base="http://localhost:1234/v1",
                        messages=messages,
                    )
                elif "grok" in current_model:
                    litellm.set_verbose=True
                    response = await acompletion(
                        model=current_model, 
                        messages=messages,
                        api_key=os.getenv("X_AI_API_KEY"),
                        api_base="https://api.x.ai/v1/chat/completions",)
                else:
                    response = await acompletion(model=current_model, messages=messages)
                
                break
            except Exception as e:
                print(f"Chat Error {current_model}: {e}")
                response = None
                if "local" in current_model:
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(30)
                continue

        else:
            api_current_model = (api_current_model + 1) % len(api_models)
            current_model = api_models[api_current_model]
            response = None
            print(f"Switching model to {current_model}")
            #time.sleep(5)
            await asyncio.sleep(5)

    result = response.choices[0].message.content

    if json_mode:
        result = json.loads(repair_json(result))

    await save_memory(memory_key, result)

    return result


async def main():
    result = await chat("", "Hello, how are you?")
    print(result)

    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
