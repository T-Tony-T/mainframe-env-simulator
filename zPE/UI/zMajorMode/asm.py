# Major Mode : Asm Mode

from zPE.UI.basemode import BaseMode

from zPE.core.asm import valid_ins as VALID_ASM_INS, valid_op  as VALID_ASM_OP, const_s, const_a
from zPE.pgm.assist_pseudo_ins import PSEUDO_INS

def valid_ins(ins):
    if ( VALID_ASM_INS(ins)  or
         VALID_ASM_OP(ins)   or
         ins in PSEUDO_INS
         ):
        return True
    else:
        return False

RE = {
    'lbl' : r'\.?[a-zA-Z@#$][a-zA-Z@#$0-9]*',
    'ins' : r'[a-zA-Z]+',
    'con' : ''.join(
        [ r'=?[0-9]*[' ] +
        const_s.keys() + const_a.keys() +
        [ r'](?:L[0-9]+)?', r"(?:'[^']*')?" ]
        ),
    'wrd' : r"[^\s']+(?:'[^']*'[^\s']*)*",
    'eow' : r'(?:[^a-zA-Z0-9].*)?$',
    'spc' : r'(?: +.*)?$',
    }


LC = {                          # local config
    'default' : {
        'JCL-header' : '''
//KC00NIUA JOB ,'DEFAULT ASSIST JCL',MSGCLASS=H
//STEP1    EXEC PGM=ASSIST
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
'''[1:],

        'JCL-tailer' : '''
/*
//
'''[1:],

        'scratch'    : '''* (test this)
* This buffer is for notes you don't want to save.
* If you want to create a file, do that with
*   {0}
* or save this buffer explicitly.
*
'''.format('"Open a New Buffer" -> Right Click -> "New File"')
        },


    'ast-map' : {
        'pos_rlvnt'     : {
            'LN-CMMNT'  : r'(\*.*)',
            'JCL-STMT'  : r'(//.*)',
            'LN-LABEL'  : ''.join([ r'(', RE['lbl'], r')' ]),
            'INSTRUCT'  : ''.join([ r'(?:', RE['lbl'], r')? +(', RE['ins'], r')', RE['spc'] ]),
            'LOC-CNT'   : ''.join([ r'(?:', RE['lbl'], r')? +(?:', RE['ins'], r' +)(?:[^\s*/+-]+[*/+-])*\(*(\*).*' ]),
            'END-CMMNT' : ''.join([ r'(?:', RE['lbl'], r')? +(?:', RE['ins'], r' +)(?:', RE['wrd'], r' +)(.+)' ]),
            },
        'non_split'     : {
            'QUOTE'     : ( "'", "'" ),
            },
        'key_words' : {
            'SEPARATER' : ( ',', 1 ),
            'OPERATOR'  : ( r'([*/+-])', 0 ),
            'LABEL'     : ( ''.join([ r'(', RE['lbl'], r')' ]), 0 ),
            'NUMBER'    : ( ''.join([ r'([0-9]+(?:\.[0-9]+)?)', RE['eow'] ]), 0 ),
            'CONSTANT'  : ( ''.join([ r'(', RE['con'], r')', RE['eow'] ]), 0 ),
            },
        'level_dlm' : {
            'PAREN'     : ( '(', ')' ),
            },
        },
    }


class AsmMode(BaseMode):
    def __init__(self):
        super(AsmMode, self).__init__('ASM Mode', LC['default'], LC['ast-map'])


    def align(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            aligned line tuple, or None if nothing need to be changed
        '''
        print 'ASM Mode :: align ~', line, ast.get_node_at(line[0])
        return None


    def comment(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            the line tuple with comment added / ajusted, or None if nothing need to be changed
        '''
        print 'ASM Mode :: comment ~', line, ast.get_node_at(line[0])
        return None


    def complete(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            the completion-list
        '''
        print 'ASM Mode :: complete ~', line, ast.get_node_at(line[0])
        return [ ]


    def hilite(self, ast):
        '''
        ast
            the abstract syntax tree associated with the buffer

        return
            the highlight tag info list, where each tag entry is
            (abs_pos_s, hilite_key, abs_pos_e)
        '''
        curr_pos = 0
        rv = []
        for leaf in ast.get_ast().flat():
            curr_pos += leaf.offset # locate start pos of the token
            pos_end   = curr_pos + len(leaf.text)
            if leaf.token in [ 'LN-CMMNT', 'END-CMMNT' ]:
                rv.append((curr_pos, 'comment', pos_end))
            elif leaf.token in [ 'LN-LABEL', 'LOC-CNT', 'LABEL' ]:
                rv.append((curr_pos, 'symbol', pos_end))
            elif leaf.token == 'INSTRUCT'  and  valid_ins(leaf.text):
                rv.append((curr_pos, 'reserve', pos_end))
            elif leaf.token in [ 'QUOTE', 'NUMBER', 'CONSTANT' ]:
                rv.append((curr_pos, 'literal', pos_end))
            else:
                pass            # no special rules applied
            curr_pos = pos_end  # advance to end of the token
        return rv
