"""Markdown ファイルから FAQ の Q&A ペアを抽出するパーサー。

構文ルール:
- H2 見出し（## ）を質問文として扱う。
- H2 見出しの直後から次の H2 見出しまでの本文を回答文とする。
- 複数段落は改行で連結し、前後の空白をトリムする。
- H3 以下の見出しは回答文の一部として扱う。
"""
import re


class MarkdownParseError(ValueError):
    """Markdown パース失敗を表す例外。"""


class MarkdownParser:
    """Markdown コンテンツを (question, answer) ペアのリストに変換する。"""

    _H2_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)

    def parse(self, content: str) -> list[tuple[str, str]]:
        """content を解析して Q&A ペアのリストを返す。

        Args:
            content: Markdown 形式の文字列。

        Returns:
            [(question, answer), ...] のリスト。

        Raises:
            MarkdownParseError: 形式不正、空の質問・回答、重複質問文、
                               有効なセクションが0件の場合。
        """
        sections = self._split_sections(content)
        if not sections:
            raise MarkdownParseError("有効な Q&A セクションが見つかりません。H2 見出し（## ）で質問文を記述してください。")

        pairs: list[tuple[str, str]] = []
        seen_questions: set[str] = set()

        for question, raw_answer in sections:
            question = question.strip()
            if not question:
                raise MarkdownParseError("空の質問文が含まれています。H2 見出しに質問文を記述してください。")

            answer = self._clean_answer(raw_answer)
            if not answer:
                raise MarkdownParseError(f"質問「{question}」に対する回答が空です。")

            if question in seen_questions:
                raise MarkdownParseError(f"質問文が重複しています: 「{question}」")

            seen_questions.add(question)
            pairs.append((question, answer))

        return pairs

    def _split_sections(self, content: str) -> list[tuple[str, str]]:
        """H2 見出しを境界として (question_raw, answer_raw) のリストに分割する。"""
        matches = list(self._H2_PATTERN.finditer(content))
        if not matches:
            return []

        sections: list[tuple[str, str]] = []
        for i, match in enumerate(matches):
            question = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            answer_block = content[start:end]
            sections.append((question, answer_block))

        return sections

    def _clean_answer(self, raw: str) -> str:
        """回答ブロックから H2 を除いた本文をクリーニングして返す。"""
        # H2 は _split_sections で分割済みなので含まれない
        # H3 以下の見出しは回答文の一部として残す
        lines = raw.splitlines()
        # 空行のみの先頭・末尾を除き、段落を改行で連結
        paragraphs: list[str] = []
        current: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                current.append(stripped)
            else:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
        if current:
            paragraphs.append(" ".join(current))
        return "\n".join(paragraphs).strip()
