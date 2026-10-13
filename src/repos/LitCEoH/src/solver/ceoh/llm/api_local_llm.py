# This file includes classe to get response from deployed local LLM
import json
import logging
import requests


class InterfaceLocalLLM:
    """Language model that predicts continuation of provided source code.
    """

    def __init__(self, url, model, temperature):
        self._url = url  # 'http://127.0.0.1:11045/completions'
        self._model = model
        self._temperature = temperature
        print(f'[LocalLLM]: {model} is used')

    def get_response(self, content: str) -> str:
        while True:
            try:
                response, full_response = self._do_request(content)

                import re
                # Regex pattern to remove <think>...</think> including the tags
                pattern = r"<think>.*?</think>"

                # Using re.sub to replace matches with an empty string
                response = re.sub(pattern, "", response, flags=re.DOTALL)

                return response, full_response
            except KeyboardInterrupt:
                print("\n[HTTP] Operation canceled by user.")
                exit(0)
            except:
                print("[HTTP] Failed, retry...")
                continue


    def _do_request(self, content: str) -> str:
        content = content.strip('\n').strip()
        # repeat the prompt for batch inference (inorder to decease the sample delay)
        data = {
            "prompt": content,
            "model": self._model,
            "stream": False,
        }

        if self._temperature is not None:
            data["temperature"] = self._temperature # Range: [0.0 - 2.0], controls randomness; lower is more deterministic, higher is more creative

        headers = {'Content-Type': 'application/json'}
        response = requests.post(self._url, data=json.dumps(data), headers=headers)
        if response.status_code == 200 or response.status_code == "200":
            full_response = response.json()
            response = response.json()['response'] #response.json()['content'][0]

            return response, full_response
        else:
            logging.info(f"[HTTP-LocalAPI] ERROR CODE: {response}")
            print(f"[HTTP] ERROR CODE: {response}")
            return None, None

