import http.client
import json


class InterfaceAPI:
    def __init__(self, api_endpoint, api_key, model_LLM, debug_mode,temperature, llm_url_info):
        self.api_endpoint = api_endpoint
        self.api_key = api_key

        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.n_trial = 5
        self.temperature = temperature

        self.llm_url_info = llm_url_info


    def get_response(self, prompt_content, add_url_info=""):
        payload_explanation = json.dumps(
            {
                "model": self.model_LLM,
                "messages": [
                    {"role": "user", "content": prompt_content}
                ],
                "stream": False,
            }
        )
        if self.temperature is not None:
            # Range: [0.0 - 2.0], controls randomness; lower is more deterministic, higher is more creative
            payload_explanation["temperature"] = self.temperature

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
            "x-api2d-no-cache": 1
        }
        
        response = None
        json_data = None
        n_trial = 1

        while True:
            n_trial += 1
            if n_trial > self.n_trial:
                return response, json_data
            try:
                conn = http.client.HTTPSConnection(self.api_endpoint)
                conn.request("POST", self.llm_url_info, payload_explanation, headers)

                res = conn.getresponse()
                data = res.read()
                json_data = json.loads(data)

                response = json_data["choices"][0]["message"]["content"]
                break
            except Exception as e:
                print(e)
                if self.debug_mode:
                    print("Error in API. Restarting the process...")
                print("Error in API. Restarting the process...")
                continue

        return response, json_data