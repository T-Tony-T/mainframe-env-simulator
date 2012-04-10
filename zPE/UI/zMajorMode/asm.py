# Major Mode : Asm Mode

from zPE.UI.basemode import BaseMode

from zPE.core.asm import valid_ins as VALID_ASM_INS, valid_op  as VALID_ASM_OP, const_s, const_a
from zPE.pgm.assist_pseudo_ins import PSEUDO_INS

import sys                      # for sys.maxsize
import re


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
            an zBufferState object indicating what need to be changed, or
            None if nothing need to be changed
        '''
        curr_ln = ast.get_nodes_at(line[0])

        if curr_ln and curr_ln[0].token == 'LN-CMMNT':
            # current line is line-comment
            curr_nonsp_pos = self.__locate_nonsp(curr_ln[0].text, 1)

            for prev_ln_ndx in range(line[0] - 1, -1, -1): # count down to line No.0
                prev_ln = ast.get_nodes_at(prev_ln_ndx)
                if not prev_ln:
                    # effective previous line is empty
                    continue    # skip it
                elif prev_ln[0].token == 'LN-CMMNT':
                    # effective previous line is line-comment
                    nonsp_pos = self.__locate_nonsp(prev_ln[0].text, 1)
                    if nonsp_pos == len(prev_ln[0].text): # previous line empty
                        continue                          #   check lines prior it
                    elif nonsp_pos == curr_nonsp_pos:     # previous line at same alignment
                        return None                       #   no need to align current line
                    elif nonsp_pos > curr_nonsp_pos:      # previous line at larger alignment
                        return self.zBufferState(
                            '{0:{1}}'.format('', nonsp_pos - curr_nonsp_pos),
                            1, 'i' # insertion / deletion always occured at offset 1
                            )
                    else:                                 # previous line at smaller alignment
                        return self.zBufferState(
                            '{0:{1}}'.format('', curr_nonsp_pos - nonsp_pos),
                            1, 'd' # insertion / deletion always occured at offset 1
                            )
                else:
                    # effective previous line is not line-comment
                    return None # do not align current line
            # no search succeed
            return None
        else:
            # current line is regular line
            pos_ins_start = 10
            pos_arg_start = 6   # col 16 = col 10 + len 6
            pos_cmt_start = 16  # col 32 = col 16 + len 16

            for prev_ln_ndx in range(line[0] - 1, -1, -1): # count down to line No.0
                prev_ln = ast.get_nodes_at(prev_ln_ndx)
                if not prev_ln:
                    # effective previous line is empty
                    continue    # skip it
                elif prev_ln[0].token != 'LN-CMMNT':
                    # effective previous line is regular line
                    rel_pos = 0
                    for i in range(len(prev_ln)):
                        rel_pos += prev_ln[i].offset
                        if prev_ln[i].token == 'INSTRUCT':
                            pos_ins_start = rel_pos
                            pos_arg_start = rel_pos + len(prev_ln[i].text)
                            if i < len(prev_ln):
                                pos_arg_start += prev_ln[i+1].offset
                            rel_pos       = 0 # reset relative position
                        elif prev_ln[i].token == 'END-CMMNT':
                            pos_cmt_start = rel_pos
                            break
                        rel_pos += len(prev_ln[i].text)
                    break
                else:
                    # effective previous line is not regular line
                    continue    # skip it

            # perform the alignment
            pass
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
        print 'ASM Mode :: comment ~', line, ast.get_nodes_at(line[0])
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
        print 'ASM Mode :: complete ~', line, ast.get_nodes_at(line[0])
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


    ### supporting methods ###
    def __locate_nonsp(self, src, start = 0, end = sys.maxsize):
        while start < min(len(src), end):
            if not src[start].isspace():
                return start
            start += 1          # advance to next character
        return start            # cannot locate non-space character
