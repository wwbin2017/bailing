import requests
from bs4 import BeautifulSoup
from typing import List

from app.tool.search.base import WebSearchEngine

class BingSearchEngine(WebSearchEngine):
    name: str = "bing_search"
    description: str = """Perform a Bing search and return a list of relevant links."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to Bing.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    def perform_search(self, query, num_results=10, *args, **kwargs):
        return self.search(query, num_results=num_results)

    def search(self, query: str, num_results: int = 10) -> List[str]:
        url = "https://www.bing.com/search"
        params = {"q": query}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        }
        response = requests.get(url, params=params, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.select("h2 a"):
            href = a.get("href")
            if href and len(links) < num_results:
                links.append(href)
        return links
