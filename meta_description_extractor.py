import argparse
import csv
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DEFAULT_INPUT = "urls.csv"
DEFAULT_OUTPUT = "meta_descriptions_output.csv"
DEFAULT_TIMEOUT = 10
DEFAULT_USER_AGENT = "MetaDescriptionFetcher/stdlib"


@dataclass
class MetaDescriptionResult:
    url: str
    description: str


class MetaDescriptionParser(HTMLParser):
    """HTMLParser subclass to capture the <meta name="description"> content."""

    def __init__(self) -> None:
        super().__init__()
        self.meta_description: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if self.meta_description is not None:
            return

        if tag.lower() != "meta":
            return

        attributes = {name.lower(): (value or "") for name, value in attrs}
        name_value = attributes.get("name", "").lower()
        property_value = attributes.get("property", "").lower()

        if name_value == "description" or property_value in {
            "og:description",
            "twitter:description",
        }:
            self.meta_description = attributes.get("content", "").strip()


def read_urls(input_path: Path) -> List[str]:
    urls: List[str] = []
    with input_path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue
            url = row[0].strip()
            if url.lower() == "url":
                # Skip header rows
                continue
            if url:
                urls.append(url)
    return urls


def fetch_html(
    url: str, timeout: int = DEFAULT_TIMEOUT, user_agent: str = DEFAULT_USER_AGENT
) -> Optional[str]:
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, ValueError):
        return None


def extract_meta_description(html: str) -> str:
    parser = MetaDescriptionParser()
    parser.feed(html)
    return parser.meta_description or ""


def write_results(output_path: Path, results: List[MetaDescriptionResult]) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["URL", "Meta Description"])
        for result in results:
            writer.writerow([result.url, result.description])


def process_urls(
    input_path: Path,
    output_path: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
) -> None:
    urls = read_urls(input_path)
    if not urls:
        raise ValueError("The input CSV contains no URLs.")

    results: List[MetaDescriptionResult] = []
    for url in urls:
        print(f"Fetching {url} ...")
        html = fetch_html(url, timeout=timeout, user_agent=user_agent)
        description = extract_meta_description(html) if html is not None else ""
        results.append(MetaDescriptionResult(url=url, description=description))

    write_results(output_path, results)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract meta descriptions from URLs listed in a CSV using only the standard library."
        )
    )
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT,
        help=f"Input CSV file containing URLs (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file for results (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for each HTTP request (default: 10)",
    )
    parser.add_argument(
        "-u",
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help=f"User-Agent header to send with requests (default: {DEFAULT_USER_AGENT})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        sys.exit(f"Input file '{input_path}' not found. Please add it to the repository root.")

    try:
        process_urls(
            input_path,
            output_path,
            timeout=args.timeout,
            user_agent=args.user_agent,
        )
    except Exception as exc:  # noqa: BLE001
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
