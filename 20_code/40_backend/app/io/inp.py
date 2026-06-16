"""
@module: app.io.inp
@context: I/O layer — Abaqus `.inp` keyword decks.
@role: A keyword-block-aware view of an Abaqus input deck for editing the model
       definition (rigid bodies, contact, sections, material include, step, BCs)
       without materializing the huge `*NODE`/`*ELEMENT` data: each block keeps
       its raw data text untouched, so round-tripping is exact and big meshes
       pass through verbatim.

A block starts at a single-`*` keyword line; everything until the next keyword
line (data rows and `**` comments) is that block's raw ``data``.
"""

from pathlib import Path

from pydantic import BaseModel, Field


class InpBlock(BaseModel):
    """One keyword block: its raw header line plus the raw lines beneath it."""

    header: str  # the raw "*KEYWORD, params" line ("" for the pre-keyword preamble)
    data: str = ""  # raw lines beneath the header, joined by newlines (no trailing newline)

    @property
    def keyword(self) -> str:
        """Upper-case keyword name, e.g. "STEP" or "SOLID SECTION" ("" for preamble)."""
        if not self.header.startswith("*"):
            return ""
        return self.header[1:].split(",", 1)[0].strip().upper()

    def parameter(self, name: str) -> str | None:
        """Value of keyword parameter ``name`` (case-insensitive). "" for a flag
        parameter present without a value; None if the parameter is absent."""
        target = name.strip().upper()
        for part in self.header.split(",")[1:]:
            key, sep, value = part.partition("=")
            if key.strip().upper() == target:
                return value.strip() if sep else ""
        return None


class InpDeck(BaseModel):
    """An Abaqus deck as an ordered list of keyword blocks."""

    blocks: list[InpBlock] = Field(default_factory=list)

    def find(self, keyword: str) -> list[InpBlock]:
        """All blocks with the given keyword."""
        target = keyword.upper()
        return [block for block in self.blocks if block.keyword == target]

    def first(self, keyword: str) -> InpBlock | None:
        """First block with the given keyword, else None."""
        target = keyword.upper()
        for block in self.blocks:
            if block.keyword == target:
                return block
        return None

    def remove(self, keyword: str) -> int:
        """Remove all blocks with the given keyword; return how many were removed."""
        target = keyword.upper()
        before = len(self.blocks)
        self.blocks = [block for block in self.blocks if block.keyword != target]
        return before - len(self.blocks)

    def insert_after(self, keyword: str, block: InpBlock) -> bool:
        """Insert ``block`` right after the first block with ``keyword``."""
        target = keyword.upper()
        for index, existing in enumerate(self.blocks):
            if existing.keyword == target:
                self.blocks.insert(index + 1, block)
                return True
        return False

    def to_text(self) -> str:
        """Serialize back to inp text (line-for-line faithful to the input)."""
        parts: list[str] = []
        for block in self.blocks:
            if block.header:
                parts.append(block.header)
            if block.data:
                parts.append(block.data)
        return "\n".join(parts)


def parse_inp(text: str) -> InpDeck:
    """Parse Abaqus inp text into keyword blocks (mesh data kept as raw text)."""
    blocks: list[InpBlock] = []
    header = ""  # preamble before the first keyword
    data: list[str] = []
    for line in text.splitlines():
        if line.startswith("*") and not line.startswith("**"):
            blocks.append(InpBlock(header=header, data="\n".join(data)))
            header = line
            data = []
        else:
            data.append(line)
    blocks.append(InpBlock(header=header, data="\n".join(data)))
    return InpDeck(blocks=blocks)


def load_inp(path: Path) -> InpDeck:
    """Load and parse a `.inp` file."""
    return parse_inp(path.read_text(encoding="latin-1"))
