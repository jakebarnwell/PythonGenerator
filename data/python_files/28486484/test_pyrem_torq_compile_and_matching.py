import sys, re

from pyrem_torq.utility import split_to_strings_iter
import pyrem_torq.expression
import pyrem_torq.script
import pyrem_torq.treeseq

import unittest

to_gsublike_expr = pyrem_torq.expression.Search.build

def my_compile(exprStr, recursionAtMarker0=True):
    try:
        seq = pyrem_torq.script.parse_to_ast(exprStr, sys.stderr)
    except pyrem_torq.expression.InterpretError, e:
        raise pyrem_torq.script.CompileError("pos %s: error: %s" % ( repr(e.stack), str(e) ))
    #print "ast=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
    
    exprs = pyrem_torq.script.convert_to_expression_object(seq)
    
    if recursionAtMarker0:
        for expr in exprs:
            expr.replace_marker_expr("0", expr)
    
    return exprs

def compile_exprs(exprStrs):
    exprs = []
    for exprStr in exprStrs:
        expr = pyrem_torq.script.compile(exprStr, recursionAtMarker0=True)
        #expr = my_compile(exprStr, recursiionAtMarker0=True)
        
        exprs.append(expr)
    return exprs

class TestTorqComileAndInterpret(unittest.TestCase):
    def test1st(self):
        exprStrs = [ 
            r'~((v <- +(r"^\d" | ".")) | (null <- +(" " | "\t")));',
            r'~(v <- (null <- "("), +(@0 | req^("(" | ")"), any), (null <- ")"));',
            r"""
                ?(v <- (u_op <- "+" | "-"), (v :: ~@0)), 
                *(
                    (v :: ~@0), *("+" | "-") 
                    | (v <- (u_op <- "+" | "-"), (v :: ~@0))
                    | any
                );
            """,
            r'~((v <- (v :: ~@0), +((b_op <- "**"), (v :: ~@0))) | (v :: ~@0));',
            r'~((v <- (v :: ~@0), +((b_op <- "*" | "/"), (v :: ~@0))) | (v :: ~@0));', 
            r'~((v <- (v :: ~@0), +((b_op <- "+" | "-"), (v :: ~@0))) | (v :: ~@0));',
        ]
        exprs = compile_exprs(exprStrs)
        
        seq = [ 'code' ]; seq.extend(split_to_strings_iter("+1.0 + 2 * ((3 - 4) / -.5) ** 6"))
        for exprIndex, expr in enumerate(exprs):
            print "exprIndex=", exprIndex, "cur seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
            newSeq = expr.parse(seq)
            self.assertTrue(newSeq, None)
            seq = newSeq
        print "result seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
        
    def test3rd(self):
        exprStrs = [
            r'~(eol <- "\t" | "\f" | "\v" | "\r" | "\n");',
            r'~(comment <- "/", "*", *(+"*", (req^("/"), any) | req^("*"), any), +"*", "/");',
            r'~(comment <- "/", "/", *(req^(eol), any));',
        ]
        exprs = compile_exprs(exprStrs)
        
        inputText = """
#include <stdio.h> // import printf()

int main(int argc, char *argv[])
{
    /************************
     ** the arguments argc/**
     ** argv are not used. **
     ************************/
    
    printf("hello, world.\n");
    return 0;
}
"""[1:-1]

        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        for expr in exprs:
            posDelta, outSeq, dropSeq = expr.match(seq, 1)
            self.assertEqual(1 + posDelta, len(seq))
            seq = [ seq[0] ] + outSeq
        print "result seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
    
    def test4th(self):
        IN = pyrem_torq.expression.InsertNode.build
        BtN = pyrem_torq.expression.BuildToNode.build
        L = pyrem_torq.expression.Literal.build
        A = pyrem_torq.expression.Any.build
        Q = pyrem_torq.expression.Req.build
        S = pyrem_torq.expression.Search.build
        
        eolExpr = BtN('eol', L("\r\n") | L("\n") | L("\r"))
        expr = S(eolExpr) + Q(pyrem_torq.expression.EndOfNode()) + IN('eof')
        
        seq = [ 'code' ]; seq.extend(split_to_strings_iter("abc\n"))

        posDelta, outSeq, dropSeq = expr.match(seq, 1)
        self.assertEqual(1 + posDelta, 3)
        self.assertEqual(outSeq, [ 'abc', [ 'eol', '\n' ], [ 'eof' ] ])
    
    def test5th(self):
        atoz = 'r"^[a-z]"'
        exprStrs = [ r'~(req(%(atoz)s), ((op_logical_and <- "and") | (op_logical_or <- "or")), req^(%(atoz)s));' % { 'atoz': atoz } ]
        
        exprs = compile_exprs(exprStrs)
        
        inputText = r'if (x and y or z) printf("hello\n");'
        inputText = inputText.decode(sys.getfilesystemencoding())
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        
        for expr in exprs:
            newSeq = expr.parse(seq)
            self.assertTrue(newSeq, None)
            seq = newSeq
        
        foundAnd, foundOr = False, False
        for item in seq:
            if isinstance(item, list):
                if item[0:1] == [ 'op_logical_and' ]: foundAnd = True
                if item[0:1] == [ 'op_logical_or' ]: foundOr = True
        self.assertTrue(foundAnd)
        self.assertTrue(foundOr)
                    
        print "result seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
    
    def test6th(self):
        searchWordLike = r'~(wordlike <- "_", *(r"^[a-zA-Z]" | r"\d" | "_") | r"^[a-zA-Z]", *(r"^[a-zA-Z]" | r"\d" | "_"));'
        exprs = compile_exprs([ searchWordLike ])
        assert len(exprs) == 1
        
        inputText = r'argv[0];'
        inputText = inputText.decode(sys.getfilesystemencoding())
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        
        seq = exprs[0].parse(seq)
        self.assertEqual(seq[1], [ 'wordlike', u'argv' ])
        
        print "result seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))
        
    def test7th(self):
        searchWordLike = r'~(word <- ("_", *("_" | r"^[a-zA-Z]" | r"^\d") | r"^[a-zA-Z]", *("_" | r"^[a-zA-Z]" | r"^\d")));'
        searchIdMake = r'~(id <- <>word);'
        
        exprs = compile_exprs([ searchWordLike, searchIdMake ])
        assert len(exprs) == 2

        inputText = r'argv[0];'
        inputText = inputText.decode(sys.getfilesystemencoding())
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        
        for expr in exprs:
            newSeq = expr.parse(seq)
            self.assertTrue(newSeq)
            seq = newSeq
        
        print "result seq=", "\n".join(pyrem_torq.treeseq.seq_pretty(seq))

    def test8th(self):
        searchFloatingPointLitearal = r"""~(
            l_float <- "0", (
                ri"^x[a-f0-9]+p\d+$" | ri"^x[a-f0-9]+p$", ("-" | "+"), r"^\d"
                | ri"^x[a-f0-9]+$", ".", *(ri"^[a-f0-9]+$" | r"^\d"), ?(ri"^[a-f0-9]*p\d+$" | ri"^[a-f0-9]*p$", ("-" | "+"), r"^\d")
            ), ?i"l"
        );
        """
        exprs = compile_exprs([ searchFloatingPointLitearal ])
        assert len(exprs) == 1
        
        pat = re.compile(r"\d+|[a-zA-Z_][a-zA-Z_0-9]*|[ \t]+|\r\n|.", re.DOTALL | re.IGNORECASE)
        
        sampleFlotingPointLiterals = [ '0x012abc.def', '0xabc.012', '0xap10' ]
        for inputText in sampleFlotingPointLiterals:
            inputText = inputText.decode(sys.getfilesystemencoding())
            seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText, pat))
            
            seq = exprs[0].parse(seq)
            self.assertEqual(seq[0], 'code')
            self.assertEqual(seq[1][0], 'l_float')
            self.assertEqual(u"".join(seq[1][1:]), inputText)
        
    def test9th(self):
        exprs = compile_exprs([ r"""
        ~("a", error "literal 'a' should not appear" | any);
        """ ])
        assert len(exprs) == 1
        
        inputText = r'b,c,d'
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        seq = exprs[0].parse(seq)
        self.assertEqual(seq, [ 'code', 'b', ',', 'c', ',', 'd' ])
        
        inputText = r'a,b,c'
        seq = [ 'code' ]; seq.extend(split_to_strings_iter(inputText))
        self.assertRaises(pyrem_torq.expression.InterpretErrorByErrorExpr, exprs[0].parse, seq)
        
if __name__ == '__main__':
    unittest.main()
