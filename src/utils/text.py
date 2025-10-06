import re
import html

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
BOLD_RE = re.compile(r"(\*\*|__)(.+?)\1", flags=re.DOTALL)
ITALIC_RE = re.compile(r"(\*|_)(.+?)\1", flags=re.DOTALL)
QUOTE_RE = re.compile(r"(^|\n)\s*> ?(.*?)(?=\n|$)", flags=re.DOTALL)

def _replace_links(s: str) -> str:
    def repl(m):
        text, url = m.group(1), m.group(2)
        return f'<a href="{html.escape(url, quote=True)}">{html.escape(text)}</a>'
    return LINK_RE.sub(repl, s)

def _replace_quotes(s: str) -> str:
    return QUOTE_RE.sub(lambda m: f'\n➤ {html.escape(m.group(2)).strip()}\n', s)

def md_to_html(text: str) -> str:
    if not text:
        return ""
    s = html.unescape(text)
    s = _replace_links(s)
    s = BOLD_RE.sub(lambda m: f"<b>{html.escape(m.group(2))}</b>", s)
    s = ITALIC_RE.sub(lambda m: f"<i>{html.escape(m.group(2))}</i>", s)
    s = _replace_quotes(s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = (
        s.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
         .replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
         .replace("&lt;a ", "<a ").replace("&lt;/a&gt;", "</a>")
    )
    s = s.replace("&gt;", ">")

    return re.sub(r"[ \t]+", " ", s).strip()

def clip_for_caption(s: str, max_len: int = 1024) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"