import json
import time
import requests
from bs4 import BeautifulSoup
import os
from typing import List
import leetcode
import leetcode.auth
from typing import Dict

def lines_to_jsonl(lines: List[Dict], file_path: str):
    """
    Convert a list of dicts to a jsonl file
    """
    # Empty the current file
    open(file_path, 'w').close()

    with open(file_path, 'a') as file:
        for dict_data in lines:
            json_line = json.dumps(dict_data)
            file.write(json_line + os.linesep)

def get_api_instance():
    """
    Get the leetcode api instance
    """
    configuration = leetcode.Configuration()

    # From Dev Tools/Application/Cookies/LEETCODE_SESSION
    leetcode_session = os.environ["LEETCODE_SESSION"]
    csrf_token = leetcode.auth.get_csrf_cookie(leetcode_session)

    configuration.api_key["x-csrftoken"] = csrf_token
    configuration.api_key["csrftoken"] = csrf_token
    configuration.api_key["LEETCODE_SESSION"] = leetcode_session
    configuration.api_key["Referer"] = "https://leetcode.com"
    configuration.debug = False

    api_instance = leetcode.DefaultApi(leetcode.ApiClient(configuration))

    return api_instance

def get_question(url):
    """
    Get the question page
    """
    while True:
        res = requests.get(url) # type: ignore
        status = res.status_code
        if status == 200:
            return res
        elif status == 404:
            return None
        else:
            print(status)
            time.sleep(300)
    
def title_slug(title):
    """
    Format the title into a title slug
    """
    return '-'.join(title.lower().split())

def get_code_snippets(url):
    """
    Gets the code snippets for the given question url
    """
    res = get_question(url)
    if res is None:
        return None
    soup = BeautifulSoup(res.content, "html.parser")
    script_tag = soup.find('script', {'type': 'application/json'})
    data = dict(json.loads(script_tag.string))
    queries = data['props']['pageProps']['dehydratedState']['queries']
    query = [i for i in queries if 'question' in i['state']['data'] and 'codeSnippets' in i['state']['data']['question']][0]
    code_snippets = query["state"]["data"]["question"]["codeSnippets"]
    return code_snippets

url = "https://leetcode.com/graphql/"

payload = lambda slug: json.dumps({
  "query": "\n    query consolePanelConfig($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    exampleTestcaseList\n  }\n}\n    ",
  "variables": {
    "titleSlug": slug
  },
  "operationName": "consolePanelConfig"
})

headers = {
  'authority': 'leetcode.com',
  'accept': '*/*',
  'accept-language': 'en-US,en;q=0.9',
  'authorization': '',
  'baggage': 'sentry-environment=production,sentry-release=8f466f72,sentry-transaction=%2Fproblems%2F%5Bslug%5D%2F%5B%5B...tab%5D%5D,sentry-public_key=2a051f9838e2450fbdd5a77eb62cc83c,sentry-trace_id=897972800d1c46e5a5d499f12244a91b,sentry-sample_rate=0.004',
  'content-type': 'application/json',
  'cookie': 'REDACTED_SESSION_COOKIE',
  'origin': 'https://leetcode.com',
  'random-uuid': '4922dfe3-8c3c-1d65-9b7a-ca84bfe9f756',
  'referer': 'https://leetcode.com/problems/two-sum/',
  'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'sentry-trace': '897972800d1c46e5a5d499f12244a91b-a37933a4a1d212e3-0',
  'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
  'x-csrftoken': '9BiGVDJiJS7iFJKVYZ1CNMNulRAvYUdlezUlp1oYOrsR2zVsk9mZh1MD6C2d6twV'
}

def test_cases_from_slug(slug: str) -> List[str]:
    response = requests.post(url, headers=headers, data=payload(slug))
    return dict(response.json())['data']['question']['exampleTestcaseList']

