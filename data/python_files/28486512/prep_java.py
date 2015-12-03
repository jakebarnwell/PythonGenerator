import re

from pyrem_torq.utility import split_to_strings_iter
from _prepscript_default_defs import build_decoder
import _prepscript_util as _pu
import pyrem_torq.expression as _pte
from nodeformatter import *

_optiion_description = """
--annotation: keep annotations.
--array_initialization: keeps array initialization code.
--field: keeps field definitions.
--import: keep import statements.
--interface: keeps interface definitions.
--javadoc: keeps javadocs.
--metadata: keep annotation definitions.
--package: keeps package declarations.
"""

class _Options(object):
    descriptions = tuple(s.strip() for s in (_optiion_description[1:-1].splitlines()))
    strs = tuple(od.split(":")[0] for od in descriptions)
    
    def __init__(self, optionStrs):
        nos = []
        for o in optionStrs:
            if o in _Options.strs:
                nos.append(o)
            else:
                raise SystemError("java: unknown option %s" % o)
        
        self.normalizedStrs = sorted(nos)
        noset = set(nos)
        
        self.annotMod = "--annotation" in noset
        self.annotDef = "--metadata" in noset
        self.arryInit = "--array_initialization" in noset
        self.field = "--field" in noset
        self.oImport = "--import" in noset
        self.interf = "--interface" in noset
        self.javaDoc = "--javadoc" in noset
        self.package = "--package" in noset

_reservedWordDescriptions = [tuple(v.strip().split("<-")) for v in re.compile(";").split("""
    r_abstract<-abstract;r_assert<-assert;
    r_bool<-boolean;r_break<-break;r_byte<-byte;
    r_case<-case;r_catch<-catch;m_charAt<-charAt;r_char<-char;r_class<-class;m_clone<-clone;m_compareTo<-compareTo;r_continue<-continue;r_const<-const;
    r_default<-default;m_dispose<-dispose;r_double<-double;r_do<-do;
    r_else<-else;r_enum<-enum;m_equals<-equals;r_extends<-extends;
    r_false<-false;r_finally<-finally;r_final<-final;r_float<-float;r_for<-for;
    m_getClass<-getClass;m_get<-get;r_goto<-goto;
    m_hashCode<-hashCode;m_hasNext<-hasNext;
    r_if<-if;r_implements<-implements;r_import<-import;r_instanceof<-instanceof;r_interface<-interface;r_int<-int;m_iterator<-iterator;
    m_length<-length;r_long<-long;
    r_native<-native;r_new<-new;m_next<-next;r_null<-null;
    r_package<-package;r_private<-private;r_protected<-protected;r_public<-public;
    r_return<-return;m_run<-run;
    r_short<-short;m_size<-size;r_static<-static;r_strictfp<-strictfp;r_switch<-switch;r_synchronized<-synchronized;
    m_toArray<-toArray;m_toString<-toString;
    r_throws<-throws;r_throw<-throw;r_transient<-transient;r_true<-true;r_try<-try;
    r_void<-void;r_volatile<-volatile;
    r_while<-while;
    """[1:-1])][:-1]

def build_whitelist(options):
    return list(rd[0] for rd in _reservedWordDescriptions)

def build_exprs(options):
    comp = _pu.expr_compile
    search = _pte.Search.build
    assign_marker_expr = _pte.assign_marker_expr
    def replaces_from_locals(ld): return dict(( k, v ) for k, v in ld.items() if isinstance(v, _pte.TorqExpression))

    opts = _Options(options)
    
    exprs = []
    
    eolExpr = comp(r'("\r" | "\n" | "\r\n");')
    wordLikeExpr = comp(r'ri"^[a-z_]";')
    extractJavadocOrMultilineCommentExpr = comp("""
    javadoc <- "/", "*", "*", *(+r"^[^*]" | any^("*", "/")), "*", "/";
    multiline_comment <- "/", "*", *(+r"^[^*]" | any^("*", "/")), "*", "/";
    """)
    extractLiteralsExpr = comp(r"""
    l_string <- ?"L", "\"", *("\\", any | any^("\"" | @eolExpr)), "\"";
    l_char <- ?"L", "'", *("\\", any | any^("'" | @eolExpr)), "'";
    l_int <- ri"^0x[a-f0-9]+$";
    l_int <- r"^\d+$", req^(ri"^e" | i"f");
    l_float <- r"^[0-9][0-9.]+$", ?(ri"^e" | i"e", ?("-" | "+"), r"^\d");
    """, replaces=replaces_from_locals(locals()))
    
    exprs.append(search(comp(r"""
    r"^\s";
    word <- @wordLikeExpr;
    @extractJavadocOrMultilineCommentExpr;
    (singleline_comment <- "/", "/", *any^(@eolExpr)), req(@eolExpr);
    @extractLiteralsExpr;
    semicolon <- ";";
    comma <- ",";
    (LB <- "{") | (RB <- "}");
    (LP <- "(") | (RP <- ")"); 
    (LK <- "[") | (RK <- "]"); 
    # 4 char operator
    op_signed_rshift_assign <- ">", ">", ">", "=";
    # 3 char operators
    (op_lshift_assign <- "<", "<", "=") | (op_rshift_assign <- ">", ">", "=");
    op_signed_rshift <- ">", ">", ">";
    # 2 char operators
    op_lshift <- "<", "<";
    (OG <- ">"), (non_splitted <-), (OG <- ">"); # right shift operator is regarded as two ">"s at this time
    (op_increment <- "+", "+") | (op_decrement <- "-", "-");
    (op_le <- "<", "=") | (op_ge <- ">", "=");
    (op_eq <- "=", "=") | (op_ne <- "!", "=");
    (op_add_assign <- "+", "=") | (op_sub_assign <- "-", "=");
    (op_mul_assign <- "*", "=") | (op_div_assign <- "/", "=");
    (op_mod_assign <- "%", "=") | (op_and_assign <- "&", "=");
    (op_xor_assign <- "^", "=") | (op_or_assign <- "|", "=");
    (op_logical_and <- "&", "&") | (op_logical_or <- "|", "|");
    # single char operators
    op_star <- "*"; # may mean mul or wildcard
    (op_div <- "/") | (op_mod <- "%");
    (op_plus <- "+") | (op_minus <- "-"); # may mean add(sub) or sign plus(minus)
    op_amp <- "&";
    op_logical_neg <- "!";
    op_complement <- "~";
    (op_or <- "|") | (op_xor <- "^");
    op_assign <- "=";
    (OL <- "<") | (OG <- ">"); # may mean less(greater) than or template parameter
    atmark <- "@";
    (ques <- "?") | (colon <- ":") | (dot <- ".");
    """, replaces=replaces_from_locals(locals()))))

    exprs.append(( "remove whitespace", search(comp(r"""
    (null <- multiline_comment | singleline_comment | "\\", *r"[ \t]", @eolExpr | @eolExpr | r"^\s");
    """, replaces=replaces_from_locals(locals()))) ))
    
    expr = _pte.Search.build(_pu.ReservedwordNode.build(_reservedWordDescriptions))
    exprs.append(( 'identify reserved words', expr ))
    
    exprs.append(search(comp("""
    # normalizes type names
    (r_int <- r_long | r_short) | (r_double <- r_float) | (l_bool <- r_true | r_false)
        | (l_string <- <>word, <>dot, (<>word :: "getString"), <>LP, <>l_string, <>RP); # support for externalized string
    """)))
    
    exprs.append(search(comp("""
    # extracts blocks, params, and indices
    any^(LB | RB | LP | RP | LK | RK)
    | (block <- LB, *@0, RB)
    | (param <- LP, *@0, RP)
    | (index <- LK, *@0, RK);
    """)))
    
    exprs.append(search(comp("""
    word, *(dot, word), (template_param <- 
        OL,
        ?(ques, ((word :: "super") | r_extends)), @0,
        *((comma | op_amp), ?(ques, ((word :: "super") | r_extends)), @0),
        OG, ?<>non_splitted
    ) 
    | (null <- 
        OL,
        (word, *(dot, word), ((word, ::, "super") | r_extends), @0 | @0),
        *((comma | op_amp), (word, *(dot, word), ((word :: "super") | r_extends), @0 | @0)),
        OG, ?<>non_splitted
    )
    | (op_rshift <- <>OG, <>non_splitted, <>OG)
    | <>non_splitted
    | word, *(dot, word), *index | ques, *index
    | (block :: ~@0) | (param :: ~@0) | (index :: ~@0); # recurse into block, param, and index
    """)))
    
    exprs.append(('id identification', search(comp("""
    ?(null <- (word :: "this"), dot), 
        (id <- <>word, *(<>dot, <>word, req^(param)), ?(template_param :: *<>any_node))
    | (id <- (<>word :: "this"))
    | (l_string <- <>l_string, +(<>op_plus, <>l_string))
    | (block :: ~@0) | (param :: ~@0) | (index :: ~@0); # recurse into block, index, and param
    """)) ))
    
    if not opts.oImport:
        if not opts.package:
            exprs.append(('remove package/import', 
                search(comp('null <- r_package, id, semicolon | r_import, id, ?(dot, op_star), semicolon;')) ))
        else:
            exprs.append(('remove import', 
                search(comp('r_import, id, ?(dot, op_star), semicolon;')) ))
    else:
        if not opts.package:
            exprs.append(('remove package', search(comp('null <- r_package, id, semicolon')) ))
    
    extractAnnotationExpr = comp('(annot <- atmark, id, ?param);')
    exprs.append(search(comp("""
    (null <- r_private | r_public | r_protected | r_synchronized | r_final | r_abstract | r_strictfp | r_volatile | r_transient)
    | (null <- r_static, req^(LB))
    | (null <- +(r_extends, id, *(comma, id) | r_implements, id, *(comma, id)))
    | (null <- r_throws, id, *(comma, id))
    | (anotation_block <- (def_block <- ?javadoc, atmark, r_interface, id, block))
    | (interface_block <- (def_block <- *(javadoc | @extractAnnotationExpr), 
        r_interface, id, ?(r_extends, id, *(comma, id)), block))
    | @extractAnnotationExpr
    | (block :: ~@0) | (param :: ~@0); # recurse into block and param
    """, replaces=replaces_from_locals(locals()))))

    someLiteralExpr = comp("(l_bool | l_string | l_int | l_char | l_float);")
    eRemoveAryInit = """
    op_assign, (initialization_block <- req(block)), (null <- block), semicolon
    | index, (initialization_block <- req(block)), (null <- block)
    | """
    exprs.append(search(comp("""%(eRemoveAryInit)s
    (value_list <- (@someLiteralExpr | id), +(comma, (@someLiteralExpr | id), ?comma))
    | (block :: ~@0) # recurse into block
    | (param :: ~@0) | (index :: ~@0); # recurse into expression
    """ % { 'eRemoveAryInit' : eRemoveAryInit }, replaces=replaces_from_locals(locals()))))

    exprs.append(search(comp("""
    any^(id | param | index | l_float | l_int | block), (null <- op_minus) # remove unary minus
    | (method_like <- m_charAt | m_compareTo | m_dispose | m_equals | m_getClass | m_get | m_hashCode | m_hasNext | m_iterator | m_length | m_next | m_run | m_size | m_toArray | m_toString)
    | (block :: ~@0) # recurse into block
    | (param :: ~@0) | (index :: ~@0); # recurse into expression
    """)))
    
    def removeRedundantParenExpr():
        tbl = _pte.ExprDict()
        someAssignOpExpr = comp("(op_assign | op_add_assign | op_sub_assign | op_mul_assign | op_div_assign | op_mod_assign | op_and_assign | op_xor_assign | op_or_assign | op_lshift_assign | op_rshift_assign | op_signed_rshift_assign);")
        tbl["someAssignOpExpr"] = someAssignOpExpr
        
        eRemoveParenExpr = comp("""
        (<>param :: (null <- LP), req(param, RP), @0, (null <- RP)) 
        | (<>param :: (null <- LP), *(req^(RP), @er), (null <- RP));
        """)
        tbl["eRemoveParenExpr"] = eRemoveParenExpr
        
        er = comp("""
        (r_return | @someAssignOpExpr), req(param, semicolon), @eRemoveParenExpr , semicolon, ?(null <- +semicolon)
        | semicolon, ?(null <- +semicolon)
        | (param :: LP, req(param, RP), @eRemoveParenExpr, RP) | (param :: ~@0) 
        | (index :: LP, req(param, RP), @eRemoveParenExpr, RP) | (index :: ~@0)
        | (block :: ~@0)
        | any;
        """, replaces=tbl)
        tbl["er"] = er
        
        return [0,]*er
    exprs.append(("remove redundant paren/semicolon", removeRedundantParenExpr()))

    someTypeKeywordExpr = comp("(r_bool | r_byte | r_char | r_double | r_float | r_int | r_short | r_object | r_string);")
    exprs.append(( "remove delegation/getter/setter/empty method", search(comp("""
    (null <- (r_void | @someTypeKeywordExpr | id), *index,
         (id | method_like), param, ((block :: LB, ?r_return, id, dot, id, param, semicolon, RB) | (block :: LB, RB)))
    | (null <- (@someTypeKeywordExpr | id), *index,
         (id | method_like), (param :: LP, RP), (block :: LB, r_return, (id | @someLiteralExpr, semicolon, RB))
    | (null <- r_void, (id | method_like), param, (block :: LB, id, op_assign, id, semicolon, RB))
    | r_return, (param :: (null <- LP), *any^(RP)), (null <- RP)), semicolon
    | (null <- r_assert, *any^(semicolon | eof), semicolon)
    | (block :: ~@0) | (param :: ~@0); # recurse into block and param
    """, replaces=replaces_from_locals(locals()))) ))
    
    someCompoundStmtKeywordExpr = comp("(r_if | r_while | r_for | r_do | r_try | r_catch | r_switch);")
    shouldBeBlockExpr = comp("((block :: ~@0) | (block <- (LB<-), @er, (RB<-)));")
    er = search(comp("""
    r_if, param, @shouldBeBlockExpr, *(r_else, r_if, param, @shouldBeBlockExpr), ?(r_else, @shouldBeBlockExpr)
    | r_else, @shouldBeBlockExpr
    | (r_while | r_for) , param, @shouldBeBlockExpr
    | r_do, @shouldBeBlockExpr, r_while, param, semicolon
    | r_try, (block :: ~@0), *((r_catch, param | r_finally), (block :: ~@0))
    | (r_catch, ?param | r_finally), (block :: ~@0)
    | +((r_case, (id | @someLiteralExpr) | r_default), colon), 
        (
            (block :: ~@0), ?(null <- r_break, semicolon) 
            | (block <- ((LB<-), *(req^(r_break | r_case | r_default), @0), (RB<-))), 
                ?(null <- r_break, semicolon) # enclose each case clause by block
        )
    | r_switch, (block :: ~@0) 
    | (r_return | r_break | r_continue | op_assign), *any^(block | LB | semicolon), semicolon
    | *any^(block | LB | semicolon | @someCompoundStmtKeywordExpr), semicolon
    | (block :: ~@0) | (param :: ~@0); # recurse into block and param
    """, replaces=replaces_from_locals(locals())))
    assign_marker_expr(shouldBeBlockExpr, 'er', er)
    exprs.append(er)
    del shouldBeBlockExpr
    del er

    exprs.append(( "simple-statement identification", search(comp("""
    r_if, param, block, *(r_else, r_if, param, block), ?(r_else, block)
    | r_else, block
    | (r_while | r_for | r_switch), param, block
    | r_do, block, r_while, param, semicolon
    | r_try, block, *((r_catch, param | r_finally), block)
    | (r_catch, ?param | r_finally), block
    | (simple_statement <- *(javadoc | annot), *any^(block | LB | semicolon | @someCompoundStmtKeywordExpr | r_finally| r_case | r_default), semicolon)
    | (block :: ~@0) | (param :: ~@0); # recurse into block and param
    """, replaces=replaces_from_locals(locals()))) ))
    
    if not opts.field:
        eRemoveFieldExpr = comp('(null <- simple_statement) | @er;')
        er = comp('r_class, id, (block :: ~@eRemoveFieldExpr) | (block :: ~@0) | (param :: ~@0) | any;', replaces=replaces_from_locals(locals()))
        assign_marker_expr(eRemoveFieldExpr, 'er', er)
        exprs.append(("remove field definitions", [0,]*er))

    exprs.append(( "definition-block identification", search(comp("""
    (def_block <- *(javadoc | annot), r_class, id, (block :: ~@0))
    | (def_block <- *(javadoc | annot), (r_void | @someTypeKeywordExpr | id), *(index :: LK, RK), (id | method_like), param, (block :: ~@0))
    | (def_block <- *(javadoc | annot), id, param, (block :: ~@0)) # constructor
    | (block :: ~@0) | (param :: ~@0); # recurse into block and param
    """, replaces=replaces_from_locals(locals()))) ))

    exprs.append(( "control-token insertion", search(comp("""
    (id | @someTypeKeywordExpr), id, (param :: ~@0), *(comma, id, ?(param :: ~@0)), semicolon # perhaps a variable decl&init.
    | (r_for | r_while), (c_loop<-)
    | (r_if | r_switch | ques), (c_cond<-) 
    | (id | method_like), (c_func<-), (param :: ~@0)
    | (<>simple_statement :: ~@0) # recuse into simple_statement and expand the simple_statement
    | (def_block :: ~@0) | (block :: ~@0) | (param :: ~@0) | (index :: ~@0) | (simple_statement :: ~@0); # recurse into block, param, index
    """, replaces=replaces_from_locals(locals()))) ))
        
    return exprs

__nodefmtTbl = {
    'code' : NodeFlatten(), # top
    'id' : NodeFormatString('id|%s'),
    'block' : NodeFlatten(), 'LB' : NodeString('(brace'), 'RB' : NodeString(')brace'),
    'word' : NodeFlatten(),
    'param' : NodeFlatten(), 'LP' : NodeString('(paren'), 'RP' : NodeString(')paren'),
    'index' : NodeFlatten(), 'LK' : NodeString('(braket'), 'RK' : NodeString(')braket'),
    'semicolon' : NodeString('suffix:semicolon'),
    'def_block' : NodeRecurse('(def_block', ')def_block'),
    'value_list' : NodeFlatten(),
}
__someLiteral = "l_bool,l_string,l_int,l_char,l_float"
__nodefmtTbl.update(( li, NodeFormatString(li + "|%s") ) for li in __someLiteral.split(","))

def build_nodeformattable(options):
    opts = _Options(options)
    class SetNodeNameStringAsDefault(dict):
        def __missing__(self, k):
            v = NodeString(k)
            self.__setitem__(k, v)
            return v
    d = SetNodeNameStringAsDefault(__nodefmtTbl)
    d['annotation_block'] = NodeFlatten() if opts.annotDef else NodeHide()
    d['interface_block'] = NodeFlatten() if opts.interf else NodeHide()
    d['annot'] = NodeRecurse('(annot', ')annot') if opts.annotMod else NodeHide()
    d['javadoc'] = NodeFormatString("javadoc|%s") if opts.javaDoc else NodeHide()
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
    return _Options(options).normalizedStrs

def get_option_description():
    return list(_Options.descriptions)

def get_version():
    return (0, 1)

def get_target_file_predicate(options):
    def pred(filePath):
        i = filePath.rfind(".")
        if i >= 0:
            ext = filePath[i:]
            return ext == ".java"
        return False
    return pred

if __name__ == '__main__':
    r = [ 'prep_java.py, preprocess script for java source files.',
         '  to run this script, use "prep.py java"',
         'options' ]
    for s in _Options.descriptions:
        r.append("  " + s)
    print "\n".join(r)
