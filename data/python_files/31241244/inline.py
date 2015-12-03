import re

def monospace(text):
    from nijiconf import MONO_BEGIN, MONO_END
    return re.sub('``(?P<monospace>([^`]|`[^`])*)``'
                , lambda m: MONO_BEGIN + m.group('monospace') + MONO_END
                , text)

def bold(text):
    from nijiconf import BOLD_BEGIN, BOLD_END
    return re.sub('\*\*(?P<bold>([^\*]|\*[^\*])*)\*\*'
                , lambda m: BOLD_BEGIN + m.group('bold') + BOLD_END
                , text)

def italic(text):
    from nijiconf import ITALIC_BEGIN, ITALIC_END
    return re.sub('///(?P<italic>([^/]|/[^/]|//[^/])*)///'
                , lambda m: ITALIC_BEGIN + m.group('italic') + ITALIC_END
                , text)

def stroke(text):
    from nijiconf import STROKE_BEGIN, STROKE_END
    return re.sub('--(?P<stroke>([^-]|-[^-])*)--'
                , lambda m: STROKE_BEGIN + m.group('stroke') + STROKE_END
                , text)

def link(text):
    from nijiconf import LINK_BEGIN, LINK_END
    return re.sub('@@(?P<url>([^@ ]+))@(?P<text>(([^@]|@[^@])+))@@'
                , lambda m: (LINK_BEGIN % m.group('url')) + m.group('text') +
                             LINK_END
                , text)

def sup(text):
    from nijiconf import SUP_BEGIN, SUP_END
    return re.sub('\^\^(?P<sup>([^\^]|\^[^\^])*)\^\^'
                , lambda m: SUP_BEGIN + m.group('sup') + SUP_END
                , text)

def sub(text):
    from nijiconf import SUB_BEGIN, SUB_END
    return re.sub(',,(?P<sub>([^,]|,[^,])*),,'
                , lambda m: SUB_BEGIN + m.group('sub') + SUB_END
                , text)

def img(text):
    from nijiconf import IMAGE
    return re.sub('\[\[img (?P<img>([^\]]|,[^\]])*)]]'
                , lambda m: IMAGE % m.group('img').strip()
                , text)

def esc_back_slash(text):
    return re.sub('\\\\(?P<esc>[`*/,:;=|@#$%&\\-\\^\\[\\]\\{\\}\\(\\)\\\\])'
                , lambda m: m.group('esc')
                , text)

def forge(text):
    return esc_back_slash(
            img(sub(sup(link(stroke(italic(bold(monospace(text)))))))))
