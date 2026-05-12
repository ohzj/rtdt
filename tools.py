import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_TEXT_LENGTH = 40_000


def fetch_url_content(url: str) -> tuple[str, str]:
    """
    Fetch and clean text content from a URL.
    Returns (text, error_message). On success, error_message is empty.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")

        # Remove noise tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        lines = [ln for ln in text.splitlines() if ln.strip()]
        text = "\n".join(lines)
        return text[:MAX_TEXT_LENGTH], ""
    except requests.exceptions.HTTPError as e:
        return "", f"HTTP error {e.response.status_code}: {e}"
    except requests.exceptions.ConnectionError:
        return "", "Could not connect to the URL. Check the address and try again."
    except requests.exceptions.Timeout:
        return "", "Request timed out (20s). The server may be slow or blocking bots."
    except Exception as e:
        return "", f"Unexpected error: {e}"


def extract_pdf_text(file_bytes: bytes) -> tuple[str, str]:
    """
    Extract text from a PDF given its raw bytes.
    Returns (text, error_message).
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            return "", "PDF is encrypted/password-protected and cannot be read."
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        if not text.strip():
            return "", "Could not extract text from PDF. It may be a scanned image."
        return text[:MAX_TEXT_LENGTH], ""
    except Exception as e:
        return "", f"Error reading PDF: {e}"
