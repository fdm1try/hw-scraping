import logging
import re
from datetime import datetime
import bs4
import requests

FAKE_BROWSER_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    'Accept-Language': 'ru-RU,ru;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/104.0.5112.102 Safari/537.36 OPR/90.0.4480.84 (Edition Yx 05)'
    ),
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="104", "Opera";v="90"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': 'Windows'
}
KEYWORDS = ['дизайн', 'фото', 'web', 'python']
RE_KEYWORDS = re.compile(r'\b(' + '|'.join(KEYWORDS) + r')\b', re.IGNORECASE | re.MULTILINE)


def scrape(url: str, retry_count=3, headers: dict = {}) -> bs4.BeautifulSoup:
    for _ in range(retry_count):
        try:
            response = requests.get(url, headers={**FAKE_BROWSER_HEADERS, **headers}, timeout=3)
            if response.status_code == 200:
                return bs4.BeautifulSoup(response.text, features='html.parser')
            else:
                logging.warning(f'Error {response.status_code} occurred when loading the page: {url}')
        except Exception as e:
            logging.error(e)
    raise Exception(f'Exceeded the maximum number of attempts to load the page: {url}')


class Article:
    def __init__(self, created: datetime, title: str, preview_content: str, url: str):
        self.created = created
        self.title = title
        self.preview_content = preview_content
        self.url = url
        self._content = None

    def __str__(self):
        return f'{self.created.strftime("%d.%m.%Y")} | {self.title}: {self.url}'

    @property
    def content(self) -> str:
        if not self._content:
            article = scrape(self.url)
            if content_block := article.find(name='div', class_='tm-article-body'):
                self._content = content_block.text
            else:
                raise Exception(f'Can not find the content of the article: {self.url}')
        return self._content


def get_articles(page: int = 1) -> list:
    articles = []
    for article in scrape(f'https://habr.com/ru/all/page{page}').find_all('article'):
        if date_block := article.find('time'):
            if timestamp := date_block.attrs.get('datetime'):
                date = datetime.strptime(timestamp.split('.')[0] + '+0000', '%Y-%m-%dT%H:%M:%S%z').astimezone()
            else:
                raise Exception('The timestamp cannot be found in the datetime block!')
        else:
            raise Exception('Can not find the date of the article!')
        if title_block := article.select_one("h2 > a > span"):
            title = title_block.text
        else:
            raise Exception('Can not find the title of the article!')
        if link_block := article.select_one("h2 > a"):
            url = f'https://habr.com{link_block.attrs["href"]}'
        else:
            raise Exception('Can not find the link to the article!')
        if content_block := article.find(name='div', class_='tm-article-body'):
            content = content_block.text
        else:
            raise Exception('Can not find the content of the article!')
        articles.append(Article(created=date, title=title, preview_content=content, url=url))
    return articles


if __name__ == '__main__':
    articles = get_articles()
    total_count = len(articles)
    print(f'Загружено {total_count} статей. Поиск по ключевым словам: {", ".join(KEYWORDS)}')
    count = 0
    error_count = 0
    for article in articles:
        try:
            if RE_KEYWORDS.search(article.preview_content) or RE_KEYWORDS.search(article.content):
                print(f'{article}')
                count += 1
        except Exception as error:
            logging.error(f'Не удалось загрузить контент статьи: {article.url}')
            logging.error(error)
            error_count += 1
    print(f'Найдено {count} статей\nОбработано статей: {total_count - error_count} из {total_count}')
