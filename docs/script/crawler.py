"""
Claude Agent SDK ドキュメントクローラ

このスクリプトは https://platform.claude.com/docs/ja/agent-sdk/ 配下の
ドキュメントを再帰的にクローリングして、Markdown形式で保存します。

URLに.mdを付けることで、直接マークダウン形式でコンテンツを取得できます。
"""

import os
import re
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import Set, Optional, Tuple

import requests
from bs4 import BeautifulSoup

BASE_URL : str = "https://platform.claude.com/docs/en/agent-sdk/"
OUTPUT_DIR : str = "../"  # scriptディレクトリからの相対パス

# 取得対象外ページリスト（保存しないファイル名）
EXCLUDE_PAGES : list[str] = [
    "index.md",  # トップページ
    "migration-guide.md",  # マイグレーションガイド
    "typescript.md",  # TypeScript関連
    "typescript-v2-preview.md",  # TypeScript v2プレビュー
]

class ClaudeDocsWebCrawler:
    """Claude Agent SDKドキュメント用Webクローラ"""

    def __init__(
        self,
        delay: float = 1.0
    ):
        """
        クローラの初期化

        Args:
            base_url: クローリングを開始するベースURL
            output_dir: ドキュメントを保存するディレクトリ（scriptディレクトリからの相対パス）
            delay: リクエスト間の待機時間（秒）
        """
        self.base_url = BASE_URL
        self.output_dir = Path(__file__).parent / OUTPUT_DIR
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def is_valid_url(self, url: str) -> bool:
        """
        URLが対象のドメイン配下かチェック

        Args:
            url: チェックするURL

        Returns:
            対象URLの場合True
        """
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)

        # 同じドメインで、base_urlのパス配下であることを確認
        return (
            parsed.netloc == base_parsed.netloc and
            parsed.path.startswith(base_parsed.path)
        )

    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """
        指定されたURLからHTMLページを取得（リンク収集用）

        Args:
            url: 取得するページのURL

        Returns:
            BeautifulSoupオブジェクト、エラー時はNone
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            print(f"Error: Failed to fetch {url}: {e}")
            return None

    def get_markdown_content(self, url: str) -> Optional[str]:
        """
        指定されたURLに.mdを付けてマークダウンコンテンツを直接取得

        Args:
            url: 取得するページのURL（.mdなし）

        Returns:
            マークダウンコンテンツ、エラー時はNone
        """
        # URLの末尾が'/'の場合はindex.mdを付ける、それ以外は.mdを付ける
        if url.endswith('/'):
            md_url = url + 'index.md'
        else:
            md_url = url + '.md'

        try:
            response = self.session.get(md_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"Error: Failed to fetch {md_url}: {e}")
            return None

    def extract_links(self, soup: BeautifulSoup, current_url: str) -> Set[str]:
        """
        ページから同一ドメイン配下のリンクを抽出

        Args:
            soup: BeautifulSoupオブジェクト
            current_url: 現在のページURL

        Returns:
            リンクのセット
        """
        links = set()

        for link in soup.find_all('a', href=True):
            href = link['href']
            # 絶対URLに変換
            absolute_url = urljoin(current_url, href)
            # フラグメント（#）を除去
            absolute_url = absolute_url.split('#')[0]

            if self.is_valid_url(absolute_url) and absolute_url not in self.visited_urls:
                links.add(absolute_url)

        return links

    def url_to_filepath(self, url: str) -> Path:
        """
        URLからファイルパスを生成

        Args:
            url: 変換するURL

        Returns:
            保存先のファイルパス
        """
        parsed = urlparse(url)
        path = parsed.path

        # ベースURLのパスを除去
        base_path = urlparse(self.base_url).path
        if path.startswith(base_path):
            path = path[len(base_path):]

        # パスをファイル名に変換
        if not path or path == '/':
            filename = 'index.md'
        elif path.endswith('/'):
            filename = path.rstrip('/').replace('/', '_') + '_index.md'
        else:
            filename = path.replace('/', '_') + '.md'

        # ファイル名をサニタイズ
        filename = re.sub(r'[<>:"|?*]', '_', filename)

        return self.output_dir / filename

    def save_page(self, url: str, content: str) -> bool:
        """
        ページをファイルに保存

        Args:
            url: ページのURL
            content: 保存するコンテンツ

        Returns:
            保存成功時True
        """
        try:
            filepath = self.url_to_filepath(url)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # メタデータを追加
            metadata = f"""---
source_url: {url}
crawled_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(metadata + content)

            print(f"Saved: {filepath.name}")
            return True
        except Exception as e:
            print(f"Error: Failed to save {url}: {e}")
            return False

    def crawl(self, start_url: Optional[str] = None, max_pages: int = 100):
        """
        クローリングを実行

        Args:
            start_url: 開始URL（Noneの場合はbase_urlを使用）
            max_pages: 最大ページ数
        """
        start_url = start_url or self.base_url
        urls_to_visit = {start_url}
        pages_crawled = 0

        print(f"Starting crawl: {start_url}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("-" * 60)

        while urls_to_visit and pages_crawled < max_pages:
            url = urls_to_visit.pop()

            if url in self.visited_urls:
                continue

            print(f"\nProcessing ({pages_crawled + 1}/{max_pages}): {url}")

            # HTMLページを取得（リンク収集用）
            soup = self.get_page_content(url)
            if not soup:
                self.visited_urls.add(url)
                continue

            # リンクを抽出
            new_links = self.extract_links(soup, url)
            urls_to_visit.update(new_links)

            # 取得対象外ページはスキップ
            filepath = self.url_to_filepath(url)
            if filepath.name in EXCLUDE_PAGES:
                print(f"Skip: {filepath.name}")
                self.visited_urls.add(url)
                continue

            # マークダウンコンテンツを取得（URLに.mdを付ける）
            markdown_content = self.get_markdown_content(url)

            # ページを保存
            if markdown_content and self.save_page(url, markdown_content):
                pages_crawled += 1

            # 訪問済みとしてマーク
            self.visited_urls.add(url)

            # レート制限
            time.sleep(self.delay)

        print("\n" + "=" * 60)
        print(f"Saved: {pages_crawled}")
        print(f"Output: {self.output_dir.absolute()}")


def main():
    """メイン実行関数"""
    crawler = ClaudeDocsWebCrawler(
        delay=1.0
    )

    try:
        crawler.crawl(max_pages=100)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print(f"Processed pages: {len(crawler.visited_urls)}")


if __name__ == "__main__":
    main()
