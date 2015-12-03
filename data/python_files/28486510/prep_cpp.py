import re

from _prepscript_default_defs import build_decoder
from pyrem_torq.utility import split_to_strings_iter
import _prepscript_util as _pu
import pyrem_torq.expression as _pte
from nodeformatter import *

try:
    import c_macro_interpreter
except:
    c_macro_interpreter = None

_reservedWordDescriptions = [tuple(v.strip().split("<-")) for v in re.compile(";").split("""
    op_logical_and<-and;op_and_assign<-and_eq;
    m_abort<-abort;r_auto<-auto;r_amp<-bitand;m_assert<-assert;
    r_or<-bitor;r_bool<-bool;r_break<-break;
    r_case<-case;r_catch<-catch;r_char<-char;r_class<-class;op_complement<-compl;r_const_cast<-const_cast;r_const<-const;r_continue<-continue;
    r_default<-default;r_delete<-delete;r_dynamic_cast<-dynamic_cast;r_double<-double;r_do<-do;
    r_else<-else;r_enum<-enum;m_exit<-exit;r_explicit<-explicit;r_extern<-extern;
    r_false<-false;r_float<-float;r_for<-for;r_friend<-friend;
    r_goto<-goto;
    r_if<-if;r_inline<-inline;r_intmax<-intmax_t;r_intptr<-intptr_t;
    r_int64<-int64_t;r_int64<-int_least64_t;r_int64<-int_fast64_t;
    r_int32<-int32_t;r_int32<-int_least32_t;r_int32<-int_fast32_t;
    r_int16<-int16_t;r_int16<-int_least16_t;r_int16<-int_fast16_t;
    r_int8<-int8_t;r_int8<-int_least8_t;r_int8<-int_fast8_t;
    r_int<-int;
    m_longjmp<-longjmp;r_long<-long;
    r_mutable<-mutable;
    r_namespace<-namespace;r_new<-new;op_logical_neg<-not;op_ne<-not_eq;
    m_offsetof<-offsetof;r_operator<-operator;op_logical_or<-or;op_or_assign<-or_eq;
    r_private<-private;r_protected<-protected;m_ptrdiff_t<-ptrdiff_t;r_public<-public;
    r_register<-register;r_reinterpret_cast<-reinterpret_cast;r_restrict<-restrict;r_return<-return;
    r_short<-short;m_setjmp<-setjmp;r_signed<-signed;r_sizeof<-sizeof;m_size_t<-size_t;r_static<-static;r_static_cast<-static_cast;r_struct<-struct;r_switch<-switch;
    r_template<-template;r_throw<-throw;r_true<-true;r_try<-try;r_typedef<-typedef;r_typeid<-typeid;r_typename<-typename;
    r_union<-union;r_unsigned<-unsigned;
    r_uint64<-uint64_t;r_uint64<-uint_least64_t;r_uint64<-uint_fast64_t;
    r_uint32<-uint32_t;r_uint32<-uint_least32_t;r_uint32<-uint_fast32_t;
    r_uint16<-uint16_t;r_uint16<-uint_least16_t;r_uint16<-uint_fast16_t;
    r_uint8<-uint8_t;r_uint8<-uint_least8_t;r_uint8<-uint_fast8_t;
    r_uintmax<-uintmax_t;r_uintptr<-uintptr_t;r_using<-using;
    r_virtual<-virtual;r_void<-void;r_volatile<-volatile;
    m_wchar_t<-wchar_t;r_while<-while;
    op_xor<-xor;op_xor_assign<-xor_eq
    """[1:-1])][:-1]

def build_whitelist(options):
    L = [ "configure_macro_line" ]
    L.extend(rd[0] for rd in _reservedWordDescriptions)
    return L

def build_exprs(options):
    if "--macro" in options and not c_macro_interpreter:
        raise SystemError("can't import c_macro_interpreter")
    
    comp = _pu.expr_compile
    search = _pte.Search.build
    assign_marker_expr = _pte.assign_marker_expr
    def replaces_from_locals(ld): return dict(( k, v ) for k, v in ld.items() if isinstance(v, _pte.TorqExpression))

    exprs = []
    
    eolExpr = comp(r'("\r" | "\n" | "\r\n");', replaces=replaces_from_locals(locals()))
    wordLikeExpr = comp(r'ri"^[a-z_]";', replaces=replaces_from_locals(locals()))
    extractMultilineCommentExpr = comp('(multiline_comment <- "/", "*", *(+r"^[^*]" | any^("*", "/")), "*", "/");', 
        replaces=replaces_from_locals(locals()))
    extractLiteralExpr = comp(r"""
    l_string <- ?"L", "\"", *("\\", any | any^("\"" | @eolExpr)), "\"";
    l_char <- ?"L", "'", *("\\", any | any^("'" | @eolExpr)), "'";
    l_int <- ri"^0x[a-f0-9]+$", req^(ri"^p"), ?ri"^[ul]+$";
    l_float <- ri"^0x[a-f0-9.]+$", ?(ri"^p" | i"p", ?("-" | "+"), ?r"^\d"), ?i"l";
    l_int <- r"^\d+$", req^(ri"^e" | i"f"), ?ri"^[ul]+$";
    l_float <- r"^[0-9][0-9.]+$", ?(ri"^e" | i"e", ?("-" | "+"), r"^\d"), ?ri"^[fl]+$";
    """, replaces=replaces_from_locals(locals()))
    
    if "--getmacrocode" in options:
        exprs.append(search(comp(r"""
        null <- +any^("/" | "#" | "\"" | "'" | "L");
        @extractMultilineCommentExpr;
        (singleline_comment <- "/", "/", *any^(@eolExpr)), req(@eolExpr);
        ?"L", "\"", *("\\", any | any^("\"" | @eolExpr)), "\"";
        ?"L", "'", *("\\", any | any^("'" | @eolExpr)), "'";
        macro_line <- "#", *(
                (space <- "\\", *r"[ \t]", @eolExpr)
                | any^(eof | @eolExpr | "/", "*" | "/", "/")
                | (space <- @extractMultilineCommentExpr)
                ), req(eof | @eolExpr | "/", "/");
        null <- any;
        """, replaces=replaces_from_locals(locals()))))
    else:
        exprs.append(search(comp(r"""
        r"^\s";
        word <- @wordLikeExpr;
        @extractMultilineCommentExpr;
        (singleline_comment <- "/", "/", *any^(@eolExpr)), req(@eolExpr);
        @extractLiteralExpr;
        macro_line <- "#", *(
                (space <- "\\", *r"[ \t]", @eolExpr)
                | any^(eof | @eolExpr | "/", "*" | "/", "/")
                | (space <- @extractMultilineCommentExpr)
                ), req(eof | @eolExpr | "/", "/");
        semicolon <- ";";
        comma <- ",";
        (LB <- "{") | (RB <- "}");
        (LP <- "(") | (RP <- ")"); 
        (LK <- "[") | (RK <- "]"); 
        # 3 char operators
        (op_lshift_assign <- "<", "<", "=") | (op_rshift_assign <- ">", ">", "=");
        op_pointer_to_member_from_pointer <- "-", ">", "*";
        # 2 char operators
        op_scope_resolution <- ":", ":";
        op_lshift <- "<", "<";
        (OG <- ">"), (non_splitted <-), (OG <- ">"); # right shift operator is regarded as two ">"s at this time
        (op_increment <- "+", "+") | (op_decrement <- "-", "-");
        op_member_access_from_pointer <- "-", ">";
        (op_le <- "<", "=") | (op_ge <- ">", "=") | (op_eq <- "=", "=") | (op_ne <- "!", "=");
        (op_add_assign <- "+", "=") | (op_sub_assign <- "-", "=");
        (op_mul_assign <- "*", "=") | (op_div_assign <- "/", "=") | (op_mod_assign <- "%", "=");
        (op_and_assign <- "&", "=") | (op_xor_assign <- "^", "=") | (op_or_assign <- "|", "=");
        op_poiner_to_member_from_reference <- ".", "*";
        (op_logical_and <- "&", "&") | (op_logical_or <- "|", "|");
        # single char operators
        op_star <- "*"; # may mean mul or indirection
        (op_div <- "/") | (op_mod <- "%");
        (op_plus <- "+") | (op_minus <- "-"); # may mean add(sub) or sign plus(minus)
        op_amp <- "&"; # may mean bitwise and or indirection
        op_logical_neg <- "!";
        (op_complement <- "~") | (op_or <- "|") | (op_xor <- "^");
        op_assign <- "=";
        (OL <- "<") | (OG <- ">"); # may mean less(greater) than or template parameter
        (ques <- "?") | (colon <- ":") | (dot <- ".");
        """, replaces=replaces_from_locals(locals()))))
        #print("exprs[-1].extract_redundant_inners()=",exprs[-1].extract_redundant_inners())
        
    if "--macro" in options:
        if "--getmacrocode" in options:
            descriptions = [d for d in options if d not in ( "--macro", "--getmacrocode" )]
            macroInterpreter = c_macro_interpreter.MacroInterpreter(getMacroCode=True)
        else:
            descriptions = [o for o in options if o != "--macro"]
            macroInterpreter = c_macro_interpreter.MacroInterpreter()
        macroInterpreter.build_tables(sorted(descriptions))
        exprs.append(( 'macro interpretation', macroInterpreter ))
    else:
        exprs.append(( "macro removal", search(comp(r"""
        (null <- macro_line | multiline_comment | singleline_comment | "\\", *r"[ \t]", @eolExpr | @eolExpr | r"^\s");
        """, replaces=replaces_from_locals(locals()))) ))
        
    if "--getmacrocode" not in options:
        expr = _pte.Search.build(_pu.ReservedwordNode.build(_reservedWordDescriptions))
        exprs.append(( 'identify reserved words', expr ))
        
        exprs.append(search(comp("""
        # normalizes type names
        (r_int <- <>r_intmax | <>r_intptr | <>r_int64 | <>r_int32 | <>r_int16
            | <>r_uintmax | <>r_uintptr | <>r_uint64 | <>r_uint32 | <>r_uint16
            | <>m_wchar_t)
        | (r_char <- <>r_int8 | <>r_uint8)
        | (r_char <- (<>r_signed | <>r_unsigned), <>r_char)
        | (r_int <- ((<>r_signed | <>r_unsigned), ?(<>r_long, ?<>r_long | <>r_short), ?<>r_int)
            | (<>r_long, ?<>r_long | <>r_short), ?<>r_int
            | <>m_size_t | <>m_ptrdiff_t | <>m_wchar_t)
        | (r_float <- ?<>r_long, ?<>r_long, <>r_double)
        # builds operator names
        | (word <- <>r_operator, (
            <>LP, <>RP
            | <>LK, <>RK
            | <>comma
            | <>op_logical_neg | <>op_logical_and | <>op_logical_or
            | <>op_mod_assign | <>op_and_assign 
                | <>op_add_assign | <>op_mul_assign | <>op_add_assign | <>op_sub_assign | <>op_div_assign 
                | <>op_lshift_assign | <>op_assign | <>op_rshift_assign | <>op_xor_assign
            | <>op_amp | <>op_star | <>op_plus | <>op_minus | <>op_div | <>op_mod 
                | <>op_lshift | <>OG, <>non_splitted, <>OG | <>op_xor | <>op_complement
                | <>op_ne | <>op_eq | <>OG | <>OL | <>op_ge | <>op_le
            | <>op_increment | <>op_decrement
            | <>op_member_access_from_pointer | <>op_pointer_to_member_from_pointer
            | <>r_delete | <>r_new
            | <>r_bool))
        # removes visibility keywords
        | (null <- (r_private | r_public | r_protected), colon)
        | (null <- r_virtual | r_inline | r_static)
        # normalizes literals
        | (l_int <- (<>word :: "NULL"))
        | (l_bool <- <>r_true | <>r_false)
        | (l_string <- +<>l_string)
        
        # extracts blocks, params, and indices
        | any^(LB | RB | LP | RP | LK | RK | r_namespace)
        | (null <- LP, op_star), *@0, (null <- RP), (op_member_access_from_pointer <- dot) 
        | (index <- LK, *@0, RK)
        | (param <- (LP, ?(null <- r_void), RP | LP, *@0, RP))
        | (null <- r_namespace, ?word | r_extern, l_string), (null <- LB), *@0, (null <- RB) 
        | r_namespace
        | (block <- LB, *@0, RB)
        ;"""  )))
        
        exprs.append(('c++-specific normalizations', search(comp("""
        (word <- <>op_scope_resolution, <>word, *(<>op_scope_resolution, <>word), ?(<>op_scope_resolution, <>op_complement, <>word)
            | <>word, +(<>op_scope_resolution, <>word), ?(<>op_scope_resolution, <>op_complement, <>word)
            | <>word, <>op_scope_resolution, <>op_complement, <>word)

        | any^(OL | OG | block | param | index | non_splitted)             
        | (template_param <- OL, *@0, OG), ?<>non_splitted
        | (op_rshift <- <>OG, <>non_splitted, <>OG)
        | <>non_splitted
        | (block :: ~@0) | (param :: ~@0) | (index :: ~@0) # recurse into block, param, and index
        ;"""  ))))
        
        exprs.append(('id identification', search(comp("""
        req(word), (
            ?(null <- (word :: "this"), op_member_access_from_pointer),
                (id <- <>word, ?(null <- template_param), *((<>dot | <>op_member_access_from_pointer), <>word, req^(param)), ?(null <- template_param))
            | (id <- (<>word :: "this"))
        )
        | (block :: ~@0) | (param :: ~@0) | (index :: ~@0) # recurse into block, param, and index
        ;"""  ))))
        
        someLiteralExpr = comp("(l_bool | l_string | l_int | l_char | l_float);")
        someMethodAttrExpr = comp("(r_public | r_private | r_protected | r_virtual);")
        someCompoundStmtKeywordExpr = comp("(r_if | r_while | r_for | r_do | r_try | r_catch | r_switch);")
        exprs.append(( "initialization block, etc", search(comp("""
        op_assign, (initialization_block <- req(block)), (null <- block), semicolon
        | (r_class | r_struct), id, (null <- colon, *(@someMethodAttrExpr, id, *(comma, *(@someMethodAttrExpr, id))))
        | (null <- r_enum, ?id, block)
        | (null <- m_assert, param, semicolon)
        
        | (null <- +(id, param, req(id, param))) # declaration by macro
        | (value_list <- (@someLiteralExpr | id), +(comma, (@someLiteralExpr | id), ?comma))
        | (null <- (r_friend | r_typedef), *any^(block | LB | semicolon | @someCompoundStmtKeywordExpr), semicolon)
        | (null <- r_using, r_namespace, id, semicolon)
        | (null <- r_namespace, op_eq, id, semicolon)
        | (block :: ~@0) # recurse into block
        ;""", replaces=replaces_from_locals(locals()))) ))

        def removeRedundantParenExpr():
            tbl = _pte.ExprDict()
            
            someAssignOpExprExpr = comp("(op_assign | op_add_assign | op_sub_assign | op_mul_assign | op_div_assign | op_mod_assign | op_and_assign | op_xor_assign | op_or_assign | op_lshift_assign | op_rshift_assign);")
            tbl["someAssignOpExprExpr"] = someAssignOpExprExpr
            
            eRemoveParenExpr = comp("""
            (<>param :: (null <- LP), req(param, RP), @0, (null <- RP)) 
            | (<>param :: (null <- LP), *(req^(RP), @er), (null <- RP));
            """)
            tbl["eRemoveParenExpr"] = eRemoveParenExpr
            
            er = comp("""
            (r_return | @someAssignOpExprExpr), req(param, semicolon), @eRemoveParenExpr , semicolon, ?(null <- +semicolon)
            | semicolon, ?(null <- +semicolon)
            | (param :: LP, req(param, RP), @eRemoveParenExpr, RP) | (param :: ~@0) 
            | (index :: LP, req(param, RP), @eRemoveParenExpr, RP) | (index :: ~@0)
            | (block :: ~@0)
            | any
            ;""", replaces=tbl)
            tbl["er"] = er
            
            return [0,]*er
        exprs.append(("remove redundant paren/semicolon", removeRedundantParenExpr()))
        
        someTypeKeywordExpr = comp("(r_int | r_char | r_float | r_bool | r_class | r_struct | r_enum | r_union | r_const | r_volatile);")
        exprs.append(search(comp("""
        any^(id | param | RK | l_float | l_int | block), (null <- op_minus) # remove unary minus
        | (null <- r_struct | r_union | r_enum), id, req^(block | colon)
        | (null <- (r_const_cast | r_dynamic_cast | r_reinterpret_cast | r_static_cast), (null <- template_param))
        | (null <- (param :: LP, +(@someTypeKeywordExpr | r_void | id), +(op_star | op_amp), RP)) # cast of pointer types
        | (@someTypeKeywordExpr| id), (param :: ~@0) # not a cast expression
        | (null <- (param :: LP, (@someTypeKeywordExpr | r_void), RP)) # cast of simple types
        | (block :: ~@0) # recurse into block
        | (param :: ~@0) | (index :: ~@0) # recurse into param and index
        ;""", replaces=replaces_from_locals(locals()))))
        
        def braceInsertionExpr():
            tbl = _pte.ExprDict()
            
            someCompoundStmtKeywordExpr = comp("(r_if | r_while | r_for | r_do | r_try | r_catch | r_switch);")
            tbl['someCompoundStmtKeywordExpr'] = someCompoundStmtKeywordExpr
            
            shouldBeBlockExpr = comp("((block :: ~@er) | (block <- (LB<-), @er, (RB<-)));")
            tbl['shouldBeBlockExpr'] = shouldBeBlockExpr
            
            er = comp("""
            r_if, param, @shouldBeBlockExpr, *(r_else, r_if, param, @shouldBeBlockExpr), ?(r_else, @shouldBeBlockExpr) 
            | r_else, @shouldBeBlockExpr
            | (r_for | r_while), param, @shouldBeBlockExpr
            | r_do, @shouldBeBlockExpr, r_while, param, semicolon
            | r_try, (block :: ~@0), *(r_catch, param, (block :: ~@0))
            | r_catch, (block :: ~@0)
            | +((r_case, (id | l_bool | l_char | l_int) | r_default), colon), 
                ((block :: ~@0), ?(null <- r_break, semicolon) | (block <- ((LB<-), *(req^(r_break | r_case | r_default), @0), (RB<-))), ?(null <- r_break, semicolon)) # enclose each case clause by block
            | r_switch, (block :: ~@0) 
            | (r_return | r_break | r_continue | op_assign), *any^(block | LB | semicolon), semicolon
            | *any^(block | LB | semicolon | @someCompoundStmtKeywordExpr), semicolon
            | (block :: ~@0) # recurse into block
            ;""", replaces=tbl)
            tbl['er'] = er
            
            return [0,]*(er | _pte.Any())
        exprs.append(braceInsertionExpr())
        
        exprs.append(( "simple-statment identification", search(comp("""
        r_if, param, block, *(r_else, r_if, param, block), ?(r_else, block) 
        | (r_catch | r_else), block
        | (r_for | r_switch | r_while), param, block
        | r_do, block, r_while, param, semicolon
        | r_try, block, *(r_catch, param, block)
        | (simple_statement <- *any^(block | LB | semicolon | @someCompoundStmtKeywordExpr | r_case | r_default | configure_macro_line), semicolon)
        | (block :: ~@0); # recurse into block
        """, replaces=replaces_from_locals(locals()))) ))
        
        exprs.append(( "decl/getter/setter removal", search(comp("""
        # mark simple getter/setter/delegation/empty block
        +(r_void | @someTypeKeywordExpr | op_star | op_amp | index | id), 
            param, ?r_const, ?(r_throw, param),
            ?(colon, id, param, *(comma, id, param)),
            (getter_body <- (block :: LB, (simple_statement :: r_return, ?(id, op_member_access_from_pointer), id, ?param, semicolon), RB)
                | (block :: LB, (<>simple_statement :: ?(id, op_member_access_from_pointer), id, param, semicolon), RB)
                | (block :: LB, RB))
        | (simple_statement :: (r_return | r_continue | r_break | r_throw), +any) | (null <- simple_statement) # remove simple statements at top level of class definition
        | (r_class | r_struct | r_union ), ?id, (block :: ~@0) # recurse into class definition
        ;""", replaces=replaces_from_locals(locals()))) ))
        
        exprs.append(( "definition-block identification", search(comp("""
        (
            ?(null <- +(r_template, template_param)), (
                (null <- (r_class | r_struct | r_union), ?id, (block :: LB, RB)) # remove empty structure definition
                | (def_block <- r_class, id, (block :: ~@0))
                | (def_block <- (r_struct | r_union), ?id, (block :: ~@0))
                | (null <- +(r_void | @someTypeKeywordExpr | op_star | op_amp | index | (id <- <>op_complement, <>id) | ?r_typename, id), param, ?r_const, ?(null <- (r_throw, param)),
                    ?(colon, id, param, *(comma, id, param)),
                    getter_body)
                | (def_block <- +(@someTypeKeywordExpr | op_star | op_amp | index | (id <- <>op_complement, <>id) | ?r_typename, id ), param, ?r_const, ?(null <- (r_throw, param)),
                    ?(null <- colon, id, param, *(comma, id, param)), # remove initialization list of constructor
                    (block :: ~@0))
                | (def_block <- r_void, id, (c_func<-), param, ?r_const, ?(null <- r_throw, param), (block :: ~@0))
            )
        )
        | (block :: ~@0)
        ;""", replaces=replaces_from_locals(locals()))) ))
        
        exprs.append(( "control-token insertion", search(comp("""
        (id | @someTypeKeywordExpr), id, (param :: ~@0), *(comma, id, ?(param :: ~@0)), semicolon # perhaps a variable decl&init.
        | (r_for | r_while), (c_loop<-)
        | (r_if | r_switch | ques), (c_cond<-) 
        | id, (c_func<-), (param :: ~@0)
        | (<>simple_statement :: ~@0) # recuse into simple_statement and expand the simple_statement
        | (def_block :: ~@0) | (block :: ~@0) | (param :: ~@0) | (index :: ~@0) # recurse into block, param, index
        ;""", replaces=replaces_from_locals(locals()))) ))
        
    return exprs

__nodefmtTbl = {
    'code' : NodeFlatten(), # top
    'id' : NodeFormatString('id|%s'),
    'block' : NodeFlatten(), 'LB' : NodeString('(brace'), 'RB' : NodeString(')brace'),
    'word' : NodeFlatten(),
    'param' : NodeFlatten(), 'LP' : NodeString('(paren'), 'RP' : NodeString(')paren'),
    'index' : NodeFlatten(), 'LK' : NodeString('(braket'), 'RK' : NodeString(')braket'),
    'macro_line' : NodeHide(),
    'semicolon' : NodeString('suffix:semicolon'),
    'def_block' : NodeRecurse('(def_block', ')def_block'),
    'value_list' : NodeFlatten(),
}
__someLiteral = "l_bool,l_string,l_int,l_char,l_float"
__nodefmtTbl.update(( li, NodeFormatString(li + "|%s") ) for li in __someLiteral.split(","))

__macroOverridings = {
    'configure_macro_line' : NodeRecurse('(configure_macro_line', ')configure_macro_line'),
    'M_EXPR' : NodeFlatten(),
    'M_CLAUSE' : NodeFlatten()
}

def build_nodeformattable(options):
    class SetNodeNameStringAsDefault(dict):
        def __missing__(self, k):
            v = NodeString(k)
            self.__setitem__(k, v)
            return v
    d = SetNodeNameStringAsDefault(__nodefmtTbl)
    if "--getmacrocode" in options:
        d.update(__macroOverridings)
    return d

# build_decoder is default one

def build_tokenizer(options):
    textSplitPattern = re.compile(r"0x[0-9a-f]+([.][0-9a-f]+)?|[0-9.]+|[a-z_]\w*|[ \t]+|\r\n|.", re.DOTALL | re.IGNORECASE)
    def tkn(inputText, inputFilePath=None):
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText, textSplitPattern))
        seq.append([ 'eof' ]) # insert eof node at the end of sequence
        return seq
    return tkn

def normalized_option_strs(options):
    rd = []; ru = []; rn = []; rl = []
    for o in options:
        if o == "--macro":
            rl.append("--macro")
        elif o == "--getmacrocode":
            rl.append(o)
        elif o.startswith("-D"): 
            rd.append("D%s" % o[2:])
            rl.append("--macro")
        elif o.startswith("-U"): 
            ru.append("U%s" % o[2:])
            rl.append("--macro")
        elif o.startswith("-N"): 
            rn.append("N%s" % o[2:])
            rl.append("--macro")
        else:
            raise SystemError("cpp: unknown option %s" % o)
    
    rd = sorted(set(rd))
    ru = sorted(set(ru))
    rn = sorted(set(rn))
    rl = sorted(set(rl))
    for item in rd + ru + rn:
        if item.find(' ') >= 0:
            raise SystemError("cpp: argument of option -D, -U, or -N must not include space character")
    return [("-%s" % s) for s in rd + ru + rn] + rl

def get_option_description():
    return [ "-Dname: #define name",
            "-Dname=value: #define name value",
            "-Uname: #undef name",
            "-Nname: make the name 0 or null string",
            "--macro: truns on interpretation of #if's",
            "--getmacrocode: expands c-macros and outputs the result, w/o further preprocessing"
        ]

def get_version():
    return (0, 1)

def get_target_file_predicate(options):
    def pred(filePath):
        i = filePath.rfind(".")
        if i >= 0:
            ext = filePath[i:]
            return ext in ( ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx" )
        return False
    return pred

if __name__ == '__main__':
    r = [ 'cpp_prep.py, preprocess script for c/c++ source files.',
         '  to run this script, use "prep.py cpp"',
         'options' ]
    for s in get_option_description():
        r.append("  " + s)
    print "\n".join(r)

