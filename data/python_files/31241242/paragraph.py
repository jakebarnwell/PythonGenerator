import html
import inline
import re

def forge_line(modifiers, line):
    for modifier in modifiers:
        line = modifier(line)
    return line

class Paragraph:
    lines = []

    def __init__(self, lines):
        self.lines = lines

    def build(self):
        return self.tail(
                reduce(lambda r, line: r + [forge_line(self.modifiers(), line)],
                       self.lines, self.head()))

    def head(self):
        return []

    def tail(self, result):
        return result

    def modifiers(self):
        from nijiconf import BR
        return [html.forge, inline.forge, lambda x: x + BR]

    def length(self):
        return reduce(lambda length, line: length + len(line), self.lines, 0)

class Table(Paragraph):
    def __init__(self, lines):
        Paragraph.__init__(self, lines)

    def head(self):
        from nijiconf import TABLE_BEGIN
        return [TABLE_BEGIN]

    def tail(self, result):
        from nijiconf import TABLE_END
        result.append(TABLE_END)
        return result

    def modifiers(self):
        from table import row_extract
        from nijiconf import ROW_BEGIN, ROW_END
        return [html.forge, inline.forge,
                lambda text: ROW_BEGIN + row_extract(text) + ROW_END]

class CodeBlock(Paragraph):
    def __init__(self, lines):
        Paragraph.__init__(self, lines)

    def head(self):
        from nijiconf import MONO_BLOCK_BEGIN
        return [MONO_BLOCK_BEGIN]

    def tail(self, result):
        from nijiconf import MONO_BLOCK_END
        result.append(MONO_BLOCK_END)
        return result

    def modifiers(self):
        from nijiconf import BR
        return [html.forge, inline.forge, lambda x: x + BR]

class AsciiArt(Paragraph):
    def __init__(self, lines):
        Paragraph.__init__(self, lines)

    def head(self):
        from nijiconf import AA_BEGIN
        return [AA_BEGIN]

    def tail(self, result):
        from nijiconf import AA_END
        result.append(AA_END)
        return result

    def modifiers(self):
        from nijiconf import BR
        return [html.forge, lambda x: x[2: ] + BR]

class Bullets(Paragraph):
    def __init__(self, lines):
        Paragraph.__init__(self, lines)

    def head(self):
        from nijiconf import UL_BEGIN
        return [UL_BEGIN]

    def tail(self, result):
        from nijiconf import UL_END
        result.append(UL_END)
        return result

    def modifiers(self):
        from nijiconf import LI_BEGIN, LI_END
        return [html.forge, inline.forge,
                lambda text: LI_BEGIN + text[2: len(text)] + LI_END]

import nijiconf

LEVEL_2_STR = (
    (nijiconf.H1_BEGIN, nijiconf.H1_END),
    (nijiconf.H2_BEGIN, nijiconf.H2_END),
    (nijiconf.H3_BEGIN, nijiconf.H3_END),
)

class Head(Paragraph):
    level = 0

    def __init__(self, lines, level):
        Paragraph.__init__(self, lines)
        self.level = level

    def modifiers(self):
        from nijiconf import LI_BEGIN, LI_END
        return [html.forge, inline.forge,
                lambda text: LEVEL_2_STR[self.level][0] +
                             text[self.level + 2: len(text)] +
                             LEVEL_2_STR[self.level][1]]

class Head1(Head):
    def __init__(self, lines):
        Head.__init__(self, lines, 0)

class Head2(Head):
    def __init__(self, lines):
        Head.__init__(self, lines, 1)

class Head3(Head):
    def __init__(self, lines):
        Head.__init__(self, lines, 2)

LINE_PATTERNS = (
    ('{{{', '}}}', CodeBlock, True),
    ('\[\[\[', ']]]', Table, True),
    ('[*][ ]', '(?![*][ ])', Bullets, False),
    ('(: |:$)', '(?!(: |:$))', AsciiArt, False),
    ('=[ ]', '', Head1, False),
    ('==[ ]', '', Head2, False),
    ('===[ ]', '', Head3, False),
)

def pattern_begin(pattern):
    return pattern[0]

def pattern_end(pattern):
    return pattern[1]

def pattern_ctor(pattern):
    return pattern[2]

def pattern_excluded(pattern):
    return pattern[3]

def search_for_para(document, begin, paragraphs):
    pattern = match_pattern_begin(document[begin])
    begin += 1 if pattern_excluded(pattern) else 0
    end = begin + 1
    while end < len(document) and not re.match(pattern_end(pattern),
                                               document[end]):
        end += 1
    paragraphs.append(pattern_ctor(pattern)(document[begin: end]))
    return end + (1 if pattern_excluded(pattern) else 0)

def normal_text_from(document, begin, paragraphs):
    if match_pattern_begin(document[begin]):
        return begin
    end = begin
    while end < len(document) and not match_pattern_begin(document[end]):
        end += 1
    paragraphs.append(Paragraph(document[begin: end]))
    return end

def match_pattern_begin(line):
    for pattern in LINE_PATTERNS:
        if re.match(pattern_begin(pattern), line):
            return pattern
    return None

def split_document(document):
    paragraphs = []
    cursor = 0
    while cursor < len(document):
        cursor = normal_text_from(document, cursor, paragraphs)
        if cursor < len(document):
            cursor = search_for_para(document, cursor, paragraphs)
    return paragraphs
