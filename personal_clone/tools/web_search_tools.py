import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from urllib.parse import urljoin, urlparse


def scrape_web_page(url: str, timeout: float = 10.0) -> dict:
    """
    Scrape a page, capturing headings, paragraphs, and code blocks.

    Returns a dict like:
    {
      "url": url,
      "title": str,
      "sections": [
          {
            "heading": str,  # e.g. "agent.py" or "Setup"
            "content": [  # list in reading order
                {"type": "paragraph", "text": ...},
                {"type": "code", "language": ..., "code": ...},
                ...
            ]
          },
          ...
      ],
      "links": [ ... ]  # absolute URLs
    }
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyAgent/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        # resp.raise_for_status()
        if resp.status_code == 200:
            html = resp.text

            soup = BeautifulSoup(html, "lxml")
            title = (
                soup.title.string.strip() if (soup.title and soup.title.string) else ""
            )

            # Collect all links
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()  # type: ignore
                abs_href = urljoin(url, href)
                parsed = urlparse(abs_href)
                if parsed.scheme in ("http", "https"):
                    links.append(abs_href)

            # We'll break down into "sections" based on headings <h1>, <h2>, ...
            # Then inside each section, traverse siblings until next heading of same or higher level.
            sections = []
            # Get top-level content container (often <article> or <main> or body)
            container = soup.find("main") or soup.find("article") or soup.body

            if container is None:
                container = soup  # fallback to full document

            # find all headings in that container
            headings = container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            # If no headings, treat the entire content as one section
            if not headings:
                # single default section
                sec = {"heading": title or "", "content": []}
                for el in container.children:
                    _collect_node(el, sec["content"], base_url=url)
                sections.append(sec)
            else:
                # Build sections
                for idx, h in enumerate(headings):
                    sec = {"heading": h.get_text(strip=True), "content": []}
                    # define boundary: until next heading of same or higher level
                    next_sibs = []
                    for sib in h.next_siblings:
                        # stop if we reach another heading of same/higher level
                        if isinstance(sib, Tag) and sib.name in [
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                        ]:
                            # Check level
                            if int(sib.name[1]) <= int(h.name[1]):
                                break
                        next_sibs.append(sib)
                    for el in next_sibs:
                        _collect_node(el, sec["content"], base_url=url)
                    sections.append(sec)

            return {
                "url": url,
                "title": title,
                "sections": sections,
                "links": links,
            }
        else:
            return {"success": False, "status": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _collect_node(node, content_list: list, base_url: str):
    """
    Recursively collect a node (paragraphs, code blocks) into content_list.
    node may be Tag, NavigableString, etc.
    """
    if node is None:
        return
    if isinstance(node, NavigableString):
        text = node.strip()
        if text:
            content_list.append({"type": "text", "text": text})
        return
    if not isinstance(node, Tag):
        return

    # if it's a code block
    # Many docs use <pre><code class="language-..."> or <code> inline.
    if node.name == "pre":
        # Try to find code inside
        code_tag = node.find("code")
        if code_tag:
            lang = None
            # often class="language-python" etc.
            classes = code_tag.get("class")
            if classes and isinstance(classes, list):
                for c in classes:
                    if c.startswith("language-"):
                        lang = c.split("language-")[1]
                        break
            code_text = code_tag.get_text()
        else:
            # fallback
            lang = None
            code_text = node.get_text()
        content_list.append({"type": "code", "language": lang, "code": code_text})
        return

    if node.name == "code" and node.parent and node.parent.name != "pre":
        # inline code
        text = node.get_text()
        content_list.append({"type": "inline_code", "code": text})
        return

    # if paragraph or block-level with text
    if node.name in ("p", "div", "span", "section"):
        # if it has children, iterate
        for child in node.children:
            _collect_node(child, content_list, base_url)
        return

    # for lists, tables, etc., you can extend here
    # fallback: dive into children
    for child in node.children:
        _collect_node(child, content_list, base_url)
