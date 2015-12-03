import collections, re

from pyrem_torq.utility import split_to_strings_iter
from _prepscript_default_defs import build_decoder as _default_build_decoder

import _prepscript_util as _pu
import pyrem_torq.expression as _pte
from nodeformatter import *

_optiion_description_str = """
--decorator: keeps decorators.
--docstring: keeps docstrings.
--import: keep import statements.
"""[1:-1]

def get_version(): return (0, 1)

def get_option_description(): 
    return [ _optiion_description_str ]

_reservedWordDescriptions = [tuple(v.strip().split("<-")) for v in re.compile(";").split("""
    r_and<-and;r_as<-as;r_assert<-assert;
    r_break<-break;
    r_class<-class;r_continue<-continue;
    r_def<-def;r_del<-del;
    r_elif<-elif;r_else<-else;r_except<-except;r_exec<-exec;
    r_finally<-finally;r_for<-for;r_from<-from;
    m_filter<-filter;
    r_global<-global;
    r_if<-if;r_import<-import;r_in<-in;r_is<-is;
    r_lambda<-lambda;
    m_map<-map;
    r_not<-not;
    r_or<-or;
    r_pass<-pass;r_print<-print;
    r_raise<-raise;r_return<-return;
    m_reduce<-reduce;
    r_try<-try;
    r_while<-while;r_with<-with;r_yield<-yield;
    """[1:-1])][:-1]

def build_whitelist(options):
    L = [ 'longstring', 'block' ]
    L.extend(rd[0] for rd in _reservedWordDescriptions)
    return L

def _calc_depth(spacesOrTabs):
    depth = 0
    for c in spacesOrTabs:
        depth += 1
        if c == ' ':
            pass
        elif c == '\t':
            depth = (depth + 8 - 1) / 8 # make it the nearest multiple of eight.
        else:
            assert c in ( ' ' or '\t' )
    return depth

def _identify_longstring_and_indentblock(tokenSeq):
    stack = [ ( 0, [] )] # list of (depth, seq)
    topDepth, topSeq = stack[-1]
    def stack_push_action(newTop):
        stack.append(newTop)
        return newTop
    def stack_pop_action():
        curTopSeq = stack.pop()[1]
        newTop = stack[-1]
        newTop[1].append(curTopSeq)
        return newTop
    q = collections.deque(tokenSeq)
    while q:
        q0 = q[0]
        if q0 in ( r"'''", r'"""' ):
            longStringNode = [ 'longstring', q.popleft() ]
            while q and q[0] != q0:
                if q[0] == '\\':
                    longStringNode.append(q.popleft())
                if not q: break # error: the source file ends with an non-closing string literal
                longStringNode.append(q.popleft())
            if q and q[0] == q0:
                longStringNode.append(q.popleft())
            topSeq.append(longStringNode)
        elif q0 in ( r"'", r'"' ):
            topSeq.append(q.popleft())
            while q and q[0] != q0:
                if q[0] in ( '\r', '\n', '\r\n' ): break # error: a string literal including new-line char
                elif q[0] == '\\':
                    topSeq.append(q.popleft())
                    if not q: break # error: the source file ends with an non-closing string literal
                topSeq.append(q.popleft())
            if q and q[0] == q0:
                topSeq.append(q.popleft())
        elif q0 == '#':
            q.popleft()
            while q and q[0] not in ( '\r', '\n', '\r\n' ):
                q.popleft()
        elif q0 in ( '\r', '\n', '\r\n' ):
            topSeq.append(q.popleft())
            while q and q[0] in ( '\r', '\n', '\r\n' ):
                q.popleft()
            if q and q[0][0] in ( ' ', '\t' ):
                depth = _calc_depth(q.popleft())
            else:
                depth = 0
            while depth < topDepth:
                topDepth, topSeq = stack_pop_action()
        elif q0 == ":":
            topSeq.append(q.popleft())
            if q and q[0][0] in ( ' ', '\t' ):
                q.popleft()
                if q and q[0] == '#':
                    q.popleft()
                    while q and q[0] not in ( '\r', '\n', '\r\n' ):
                        q.popleft()
            if q and q[0] in ( '\r', '\n', '\r\n' ):
                topSeq.append(q.popleft())
                if q and q[0][0] in ( ' ', '\t' ):
                    depth = _calc_depth(q.popleft())
                else:
                    depth = 0
                topDepth, topSeq = stack_push_action(( depth, [ 'block' ] ))
        else:
            topSeq.append(q.popleft())
    while len(stack) > 1:
        topDepth, topSeq = stack_pop_action()
    return stack[-1][1]

def build_exprs(options):
    comp = _pu.expr_compile
    search = _pte.Search.build
    assign_marker_expr = _pte.assign_marker_expr
    def replaces_from_locals(ld): return dict(( k, v ) for k, v in ld.items() if isinstance(v, _pte.TorqExpression))
    
    exprs = []
    exprs.append(('identify_longstring_and_indentblock', _identify_longstring_and_indentblock))
    
    eolExpr = comp(r'("\r" | "\n" | "\r\n");')
    extractLiteralExpr = comp(r"""
    l_string <- ?ri"^[ru]+$", (<>longstring 
        | "\"", *("\\", any | any^("\"" | @eolExpr)), "\"" 
        | "'", *("\\", any | any^("\'" | @eolExpr)), "'" );
    l_int <- (ri"^0x" | ri"^0b" | ri"^0o" | r"^\d+$", req^(i"j")), ?ri"L";
    l_float <- (".", r"^\d+$") | r"^[0-9][0-9.]+$", ?(ri"^e" | i"e", ?("-" | "+"), r"^\d"), req^(i"j");
    l_imag <- (ri"^0x" | ri"^0b" | ri"^0o" | r"^\d+$") 
        | (".", r"^\d+$") | r"^[0-9][0-9.]+$", ?(ri"^e" | i"e", ?("-" | "+"), r"^\d"),
        i"j";
    l_bool <- "True" | "False";
    """, replaces=replaces_from_locals(locals()))
    
    wordLikeExpr = comp(r'ri"^[a-z_]";')
    opExpr = comp(r"""
    @extractLiteralExpr;
    word <- @wordLikeExpr;
    semicolon <- ";";
    comma <- ",";
    (LB <- "{") | (RB <- "}"); 
    (LP <- "(") | (RP <- ")"); 
    (LK <- "[") | (RK <- "]"); 
    # 3 char operator
    (op_lshift_assign <- "<", "<", "=") | (op_rshift_assign <- ">", ">", "=");
    op_power_assign <- "*", "*", "=";
    op_intdev_assign <- "/", "/", "=";
    # 2 char operator
    (op_lshift <- "<", "<") | (op_rshift <- ">", ">");
    (op_le <- "<", "=") | (op_ge <- ">", "=");
    (op_eq <- "=", "=") | (op_ne <- "!", "=") | (op_ne <- "<", ">");
    (op_add_assign <- "+", "=") | (op_sub_assign <- "-", "=");
    (op_mul_assign <- "*", "=") | (op_div_assign <- "/", "=");
    (op_mod_assign <- "%", "=") | (op_and_assign <- "&", "=");
    op_xor_assign <- "^", "="; 
    op_or_assign <- "|", "=";
    op_intdev <- "/", "/";
    op_power <- "*", "*"; # may mean power or **arg
    # single char operator
    op_star <- "*"; # may mean mul, wildcard(import), or *arg
    (op_div <- "/") | (op_mod <- "%");
    (op_plus <- "+") | (op_minus <- "-"); # may mean add(sub) or sign plus(minus)
    op_amp <- "&";
    op_complement <- "~";
    op_or <- "|";
    op_xor <- "^";
    op_assign <- "="; 
    (op_lt <- "<") | (op_gt <- ">");
    atmark <- "@";
    colon <- ":";
    dot <- ".";
    linecont <- "\\";
    backquote <- "\x60";
    """, replaces=replaces_from_locals(locals()))
    exprs.append(search(comp("@opExpr | (block :: ~@0);", replaces=replaces_from_locals(locals()))))
    
    expr = _pte.Search(_pu.ReservedwordNode(_reservedWordDescriptions) | _pte.NodeMatch("block", _pte.Marker('0')))
    _pte.assign_marker_expr(expr, '0', expr)
    exprs.append(( 'identify reserved words', expr ))
    
    someOperatorExpr = comp("(op_lshift_assign | op_rshift_assign | op_power_assign  | op_intdev_assign | op_lshift | op_rshift | op_le | op_ge | op_eq | op_ne | op_ne | op_add_assign | op_sub_assign | op_mul_assign | op_div_assign | op_mod_assign | op_and_assign | op_xor_assign | op_or_assign | op_intdev | op_power | op_star | op_div | op_mod | op_plus | op_minus | op_amp | op_complement | op_or | op_xor | op_assign | op_lt | op_gt);")
    exprs.append(( "remove whitespace", search(comp(r"""
    (l_string <- <>l_string, +(?r"^[ \t]", <>l_string))
    | (null <- +r"^[ \t]")
    | colon, ?(null <- +(@eolExpr | r"^[ \t]")), (block :: ~@0)
    | (newline <- @eolExpr), ?(null <- +(@eolExpr | r"^[ \t]")), ?(r_if | r_else | r_elif | r_for)
    | ((null <- linecont) | @someOperatorExpr | LB | LK | LP | comma), ?(null <- +r"^[ \t]"), (null <- @eolExpr) 
    | (block :: ~@0);
    """, replaces=replaces_from_locals(locals()))) ))
    
    def identifyParamIndexDictLamda():
        tbl = _pte.ExprDict()
        argumentExpr = tbl["argumentExpr"] = comp("""
        ?((param_power <- <>op_power) | (param_star <- <>op_star)), 
        (id <- <>word), 
        ?((param_assign <- <>op_assign), +(req^(comma | RP | colon), @er))
        ;""")
        er = tbl["er"] = comp("""
        (id <- <>word)
        | (l_string <- <>l_string, +(<>op_plus, <>l_string))
        | (param <- LP, @argumentExpr, *(comma, @argumentExpr), RP) # param or tuple expr
        | (param <- LP, *(req^(RP), @0), RP) # paren in expression, param or tuple expr
        | (index <- LK, *(req^(RK | colon), @0 | (index_colon <- <>colon)), RK) # getitem, or list expr
        | (dict <- LB, *(req^(RB | colon), @0 | (dict_colon <- <>colon)), RB)
        | r_lambda, (param <- (LP<-), ?(@argumentExpr, *(comma, @argumentExpr)), (RP<-)), (lamda_colon <- <>colon)
        | r_for, (param <- (LP<-), (id <- <>word), *(comma, (id <- <>word)), (RP<-)), r_in
        | (block :: ~@0)
        | any
        ;
        """, replaces=tbl)
        return [0,]*er
    exprs.append(( 'identify param, index, dict, lamda, etc', identifyParamIndexDictLamda() ))
    
    def identifyImplicitTupleExpr():
        tbl = _pte.ExprDict()
        someAssignOperatorExpr = tbl['someAssignOperatorExpr'] = comp("(op_lshift_assign | op_rshift_assign | op_power_assign  | op_intdev_assign | op_lshift | op_rshift | op_le | op_ge | op_eq | op_ne | op_ne | op_add_assign | op_sub_assign | op_mul_assign | op_div_assign | op_mod_assign | op_and_assign | op_xor_assign | op_or_assign | op_assign);")
        indexContentWoCommaExpr = tbl['indexContentWoCommaExpr'] = comp("""
        (param <- (LP<-), (req^(comma | RK | index_colon), @er), comma, *(req^(RK | index_colon), @er), (RP<-));
        """)
        er = tbl['er'] = comp("""
        (r_return | r_yield | @someAssignOperatorExpr), 
           (param <- (LP<-), (req^(comma | newline), @0), comma, *(req^(newline), @0), (RP<-), req(newline))
        | (index :: LK, 
            ?@indexContentWoCommaExpr, *(index_colon, @indexContentWoCommaExpr),
            RK)
        | (id, *(dot, id), (param :: LP, *(comma | ?(id, op_assign), *(req^(comma | RP), @0))))
        | (block :: ~@0)
        | ((r_except | r_with), *any^(colon), colon)
        | ((r_from | r_import), *any^(newline), newline)
        | (param <- (LP<-), backquote, +(req^(backquote | newline), @0), backquote, (RP<-))
        | any
        ;
        """, replaces=tbl)
        return [0,]*er
    exprs.append(( "identify implicit tuple exprs", identifyImplicitTupleExpr() ))
    
    def removeRedundantParenExpr():
        tbl = _pte.ExprDict()
        someAssignOperatorExpr = tbl['someAssignOperatorExpr'] = comp("(op_lshift_assign | op_rshift_assign | op_power_assign  | op_intdev_assign | op_lshift | op_rshift | op_le | op_ge | op_eq | op_ne | op_ne | op_add_assign | op_sub_assign | op_mul_assign | op_div_assign | op_mod_assign | op_and_assign | op_xor_assign | op_or_assign | op_assign);")
        singleValueParamExpr = tbl['singleValueParamExpr'] = comp("""
        req^((param :: LP, RP)), (param :: LP, *any^(comma));
        """)
        mutipleValueParamExpr = tbl['mutipleValueParamExpr'] = comp("""
        (param :: LP, *any^(comma), comma, *any);
        """)
        removeParenExpr = tbl['removeParenExpr'] = comp("""
        (<>param :: (null <- LP), req(@singleValueParamExpr, RP), @0, (null <- RP)) 
        | (<>param :: (null <- LP), *(req^(RP), @er), (null <- RP));
        """, replaces=tbl)
        er = tbl['er'] = comp("""
        (r_return | r_yield | @someAssignOperatorExpr), req(@singleValueParamExpr, newline), @removeParenExpr, newline
        | (block :: LB, (null <- +(r_pass, newline)), LK)
        | (block :: ~@0)
        | req(@mutipleValueParamExpr), (param :: LP, *(req(@singleValueParamExpr), @removeParenExpr | req^(RP), @0), RP)
        | (param :: LP, req(@singleValueParamExpr, RP), @removeParenExpr, RP) 
        | (param :: ~@0)
        | (r_pass, newline), ?(null <- +(r_pass, newline))
        | any;
        """, replaces=tbl)
        return [0,]*er
    
    exprs.append(( "remove redundant paren/pass", removeRedundantParenExpr() ))
    
    exprs.append(( "identify def_block, l_docstring, decorator, import statement", search(comp("""
    (def_block <- 
        *(decorator <- atmark, id, *(dot, id), ?param), (
            (r_class, id, ?param, colon)
            | (r_def, id, param, colon)
        ), (
            (block :: (l_docstring <- <>l_string, ?(null <- newline)), *@0)
            | (block :: ~@0)
        )
    )
    | (import_stmt <- (r_from | r_import), *(req^(newline), any), newline)
    | (block :: ~@0)
    | any;
    """)) ))
    
    exprs.append(( "insert control tokens", search(comp("""
    r_if, (c_cond<-),
    (r_while | r_for | m_map | m_filter | m_reduce), (c_loop<-)
    | (id | r_lambda), (c_func<-), req(param)
    | (param :: ~@0)
    | (index :: ~@0)
    | (dict :: ~@0)
    | (block :: ~@0)
    | (def_block :: ~@0);
    """)) ))
    
    return exprs

__nodefmtTbl = {
    'code' : NodeFlatten(), # top
    'id' : NodeFormatString('id|%s'),
    'dict': NodeFlatten(), 'LB' : NodeString('(brace'), 'RB' : NodeString(')brace'),
    'word' : NodeFlatten(),
    'param' : NodeFlatten(), 'LP' : NodeString('(paren'), 'RP' : NodeString(')paren'),
    'index' : NodeFlatten(), 'LK' : NodeString('(braket'), 'RK' : NodeString(')braket'),
    'newline' : NodeString('suffix:newline'),
    'semicolon' : NodeString('suffix:semicolon'),
    'block' : NodeRecurse('(block', ')block'),
    'def_block' : NodeRecurse('(def_block', ')def_block'),
    'argsep_comma' : NodeString('comma')
}
__someLiteral = "l_bool,l_string,l_int,l_float,l_imag"
__nodefmtTbl.update(( li, NodeFormatString(li + "|%s") ) for li in __someLiteral.split(","))

def build_nodeformattable(options):
    optionDocstring = "--docstring" in options
    optionDecorator = "--decorator" in options
    optionImoprtStmt = "--import" in options
    class SetNodeNameStringAsDefault(dict):
        def __missing__(self, k):
            v = NodeString(k)
            self.__setitem__(k, v)
            return v
    d = SetNodeNameStringAsDefault(__nodefmtTbl)
    d['l_docstring'] = NodeFormatString("l_docstring|%s") if optionDocstring else NodeHide()
    d['decorator'] = NodeRecurse("(decorator", ")decorator") if optionDecorator else NodeHide()
    d['import_stmt'] = NodeRecurse("(import_stmt", ")import_stmt") if optionImoprtStmt else NodeHide()
    return d

def build_decoder(options):
    default_decoder = _default_build_decoder([])
    encodeDescritionPat = re.compile(r"coding[=:]\s*([-\w.]+)")
    def dec(inputFileBytes, inputFilePath=None):
        if not inputFileBytes: return default_decoder(inputFileBytes)
        L0 = inputFileBytes.splitlines()[0] 
        L0 = L0.decode("ascii", 'ignore')
        m = encodeDescritionPat.search(L0)
        if m:
            sp = m.span(1)
            encodingName = L0[sp[0]:sp[1]]
            return inputFileBytes.decode(encodingName)
        else:
            encodingName = "utf8"
            return default_decoder(inputFileBytes)
    return dec

def build_tokenizer(options):
    bom = '\ufeff'
    textSplitPattern = re.compile("|".join([ r"'''", r'"""', r"0x[0-9a-f]+|0o[0-7]+|0b[01]+|[0-9.]+|[a-z_]\w*|[ \t]+|\r\n|." ]), re.DOTALL | re.IGNORECASE)
    def tkn(inputText, inputFilePath=None):
        if inputText.startswith(bom): inputText = inputText[len(bom):] # remove bom
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText, textSplitPattern))
        seq.append([ 'eof' ]) # insert eof node at the end of sequence
        return seq
    return tkn

def normalized_option_strs(options):
    r = []
    for o in options:
        if o in ( "--docstring", "--decorator", "--import" ):
            r.append(o)
        else:
            raise SystemError("python: unknown option %s" % o)
    return sorted(r)

def get_target_file_predicate(options):
    def pred(filePath):
        i = filePath.rfind(".")
        if i >= 0:
            ext = filePath[i:]
            return ext == ".py"
        return False
    return pred

if __name__ == '__main__':
    r = [ 'prep_python.py, preprocess script for java source files.',
         '  to run this script, use "prep.py python"',
         'options' ]
    #for s in _Options.descriptions:
    #    r.append("  " + s)
    print "\n".join(r)
