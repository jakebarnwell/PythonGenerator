Module([ImportFrom('nltk', [alias('CFG', None)], 0), Assign([Name('GRAMMAR_FILENAME', Store())], Str('cfg_grammar.txt')), Assign([Name('f', Store())], Call(Name('open', Load()), [Name('GRAMMAR_FILENAME', Load()), Str('r')], [], None, None)), Assign([Name('file_contents_str', Store())], Call(Attribute(Name('f', Load()), 'read', Load()), [], [], None, None)), Expr(Call(Attribute(Name('f', Load()), 'close', Load()), [], [], None, None)), Assign([Name('grammar', Store())], Call(Attribute(Name('CFG', Load()), 'fromstring', Load()), [Name('file_contents_str', Load())], [], None, None)), Expr(Call(Attribute(Name('grammar', Load()), 'productions', Load()), [], [], None, None))])