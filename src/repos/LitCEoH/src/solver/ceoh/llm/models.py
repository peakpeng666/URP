import os

###################################################################
# LLM Models for configuration of local or openrouter requests

OPENROUTER_MODELS = [
]

DEEPSEEK_MODELS = [
    'deepseek-chat',
    'deepseek-reasoner',
]

OPENAI_MODELS = [
    'gpt-4',
    'gpt-4o',
    'gpt-4o-2024-08-06',
    'gpt-4o-2024-11-20',
]

LOCAL_MODELS = [
    'llama3.1:70b',
    'gemma3:27b',
    'qwen2.5-coder:32b',
]

def get_model_info(model_name):

    llm_use_local = False
    add_url_info = False

    if model_name in LOCAL_MODELS:
        print("--- USE Local Model")
        print(f"--- > {model_name}")

        # Enter full url of your model
        llm_api_endpoint = "https://api.imi-services.imi.kit.edu/api/generate"
        llm_use_local = True
        api_key = ""

    elif model_name in OPENROUTER_MODELS:
        print("--- USE OPENROUTER Model")
        print(f"--- > {model_name}")

        api_key = os.getenv('OPENROUTER_API_KEY')
        llm_api_endpoint = "openrouter.ai"
        add_url_info="/api/v1/chat/completions"

    elif model_name in DEEPSEEK_MODELS:
        print("--- USE DEEPSEEK Model")
        print(f"--- > {model_name}")

        api_key = os.getenv('DEEPSEEK_API_KEY')
        llm_api_endpoint = "api.deepseek.com"
        add_url_info="/chat/completions"

    else:
        print("--- USE REST Model")
        print(f"--- > {model_name}")

        api_key = os.getenv('OPENAI_API_KEY')
        llm_api_endpoint = "api.openai.com"
        add_url_info="/v1/chat/completions"

    if api_key == None:
        print('##########################################')
        print(' -- No LLM API Key is set. -- ')
        print(' -- Have a look into the .env file! -- ')
        print('##########################################')
        exit(0)

    return llm_api_endpoint, add_url_info, api_key, llm_use_local