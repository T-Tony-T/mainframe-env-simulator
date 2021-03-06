# Major Mode : Asm Mode

from zPE.util import *

from zPE.GUI.basemode import BaseMode

from zPE.base.core.asm import ASM_INSTRUCTION as ASM_INS_SET, op_code as ASM_OP_MAP, ext_mnem as EXT_MNEM_MAP, const_s, const_a
from zPE.base.pgm.assist_pseudo_ins import PSEUDO_INS

import sys                      # for sys.maxsize
import re

INS_LIST = ASM_INS_SET | set(ASM_OP_MAP.keys()) | set(EXT_MNEM_MAP.keys()) | set(PSEUDO_INS.keys()) # set union

def valid_ins(ins):
    return ins in INS_LIST

RE = {
    'lbl' : r'\.?[a-zA-Z@#$][a-zA-Z@#$0-9]*',
    'ins' : r'[a-zA-Z]+',
    'con' : ''.join(
        [ r'=?[0-9]*[' ] +
        const_s.keys() + const_a.keys() +
        [ r'](?:L[0-9]+)?' ]
        ),
    'con-' : r"'[^']*",         # incomplete constant
    'con+' : r"'[^']*'",        #   complete constant

    'wrd' : r"[^\s']+(?:'[^']*'[^\s']*)*",
    'eow' : r'(?:[^a-zA-Z0-9].*)?$',
    'spc' : r'(?:[ \t]+.*)?$',
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
            'LN-CMMNT'  : ( 0, r'(\*.*)' ),
            'JCL-STMT'  : ( 0, r'(//.*|/\*[ \t]*)' ),
            'LN-LABEL'  : ( 0, ''.join([ r'(',   RE['lbl'], r')' ]) ),
            'INSTRUCT'  : ( 0, ''.join([ r'(?:', RE['lbl'], r')?[ \t]+(',   RE['ins'], r')', RE['spc'] ]) ),
            'LOC-CNT'   : ( 0, ''.join([ r'(?:', RE['lbl'], r')?[ \t]+(?:', RE['ins'], r'[ \t]+)',
                                    # skip upto [(,] (lazy-match)       loc
                                    r'(?:.*?[(,])*?(?:[^\s*/+-]+[*/+-])*(\*).*'
                                    #              skip ExpOp (greedy)      other stuff
                                    ])
                            ),
            'END-CMMNT' : ( 0, ''.join([ r'(?:', RE['lbl'], r')?[ \t]+(?:', RE['ins'], r'[ \t]+)',
                                    r'(?:', RE['wrd'], r'[ \t]+)([^\s].*)'
                                    ])
                            ),
            'TAB-CHAR'  : ( 0, r'.*(\t+).*' ),
            },
        'non_split'     : {
            'QUOTE'     : ( 0, "'", "'" ),
            },
        'key_words' : {
            'SEPARATER' : ( 0, ',', 1 ),
            'OPERATOR'  : ( 0, r'([*/+-])', 0 ),
            'LABEL'     : ( 0, ''.join([ r'(', RE['lbl'], r')' ]), 0 ),
            'NUMBER'    : ( 0, ''.join([ r'([0-9]+(?:\.[0-9]+)?)', RE['eow'] ]), 0 ),
            'CONST'     : ( 0, ''.join([ r'(', RE['con'],             r')', RE['eow'] ]), 0 ),
            'CONSTAN-'  : ( 5, ''.join([ r'(', RE['con'], RE['con-'], r')', RE['eow'] ]), 0 ),
            'CONSTANT'  : ( 9, ''.join([ r'(', RE['con'], RE['con+'], r')', RE['eow'] ]), 0 ),
            },
        'level_dlm' : {
            'PAREN'     : ( 0, '(', ')' ),
            },
        },
    }


class AsmMode(BaseMode):

    _cp_dict_ = {
        'ins' : BaseMode.zCompletionDict(INS_LIST),
        }

    def __init__(self):
        super(AsmMode, self).__init__('ASM Mode', LC['default'], LC['ast-map'])


    def align(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            an zAtomicChange object indicating what need to be changed, or
            None if nothing need to be changed
        '''
        curr_ln = ast.get_nodes_at(line[0], ignore_anchor = True)

        if curr_ln and curr_ln[0].token == 'JCL-STMT':
            # current line is JCL card
            return None         # ignore it
        elif curr_ln and curr_ln[0].token == 'LN-CMMNT':
            # current line is line-comment
            curr_nonsp_pos = self.__locate_nonsp(curr_ln[0].text, 1)

            for prev_ln_ndx in range(line[0] - 1, -1, -1): # count down to line No.0
                prev_ln = ast.get_nodes_at(prev_ln_ndx, ignore_anchor = True)
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
                        change = self.zBufferChange(
                            '{0:{1}}'.format('', nonsp_pos - curr_nonsp_pos),
                            1, 'i' # insertion / deletion always occured at offset 1
                            )
                    else:                                 # previous line at smaller alignment
                        change = self.zBufferChange(
                            '{0:{1}}'.format('', curr_nonsp_pos - nonsp_pos),
                            1, 'd' # insertion / deletion always occured at offset 1
                            )
                    return self.zAtomicChange([ change ])
                else:
                    # effective previous line is not line-comment
                    return None # do not align current line
            # no search succeed
            return None
        else:
            # current line is regular line
            pos_ins_start = 9
            pos_arg_start = 15  # ins_start + 6
            pos_cmt_start = 31  # arg_start + 16

            for prev_ln_ndx in range(line[0] - 1, -1, -1): # count down to line No.0
                prev_ln = ast.get_nodes_at(prev_ln_ndx, ignore_anchor = True)
                if not prev_ln:
                    # effective previous line is empty
                    continue    # skip it
                elif prev_ln[0].token == 'JCL-STMT':
                    # effective previous line is JCL card
                    continue    # ignore it
                elif prev_ln[0].token != 'LN-CMMNT':
                    # effective previous line is regular line
                    prev_ln = ''.join([ str(node) for node in prev_ln ])[len(ast.get_line_prefix(prev_ln_ndx)) : ]
                    field = resplit_sq(r'(\s+)', prev_ln, 3)

                    pos_ins_start = sum([ len(f) for f in field[0:2] ])
                    if len(field) > 4: # i.e. has everything upto argument(s) field
                        pos_arg_start = pos_ins_start + sum([ len(f) for f in field[2:4] ])
                    else:
                        pos_arg_start = pos_ins_start + 6
                    if len(field) > 6: # i.e. has everything upto comment field
                        pos_cmt_start = pos_arg_start + sum([ len(f) for f in field[4:6] ])
                    else:
                        pos_cmt_start = pos_arg_start + 16
                    break
                else:
                    # effective previous line is not regular line
                    continue    # skip it

            # perform the alignment
            field = resplit_sq(r'(\s+)', line[1], 3)
            change_list = [ ]
            # check instruction alignment
            label_end  = len(field[0]) # this always exists, since an resplit_sq() on '' results [ '' ]
            offset_ins = sum([ len(f) for f in field[0:2] ])
            change = self.__align_part(label_end, offset_ins, pos_ins_start)
            if change:
                change_list.append(change)
                if change.action == 'i':
                    offset_ins += len(change.content)
                else:
                    offset_ins -= len(change.content)
            # check argument(s) alignment, if any
            if len(field) > 2 and field[2]:  # i.e. has instruction field
                ins_end    = offset_ins + len(field[2])
                offset_arg = offset_ins + sum([ len(f) for f in field[2:4] ])
                change = self.__align_part(ins_end, offset_arg, pos_arg_start)
                if change:
                    change_list.append(change)
                    if change.action == 'i':
                        offset_arg += len(change.content)
                    else:
                        offset_arg -= len(change.content)
            # check comment alignment, if any
            if len(field) > 4 and field[4]:  # i.e. has argument(s) field
                cmmnt_end  = offset_arg + len(field[4])
                offset_cmt = offset_arg + sum([ len(f) for f in field[4:6] ])
                change = self.__align_part(cmmnt_end, offset_cmt, pos_cmt_start)
                if change:
                    change_list.append(change)
            # return the change(s), if any
            if change_list:
                return self.zAtomicChange(change_list)
            else:
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
        ( indx, node ) = ast.get_word_node(ast.get_line_offset(line[0]) + line[-1])
        if node.token == 'INSTRUCT':
            curr_dict = self._cp_dict_['ins']
        elif node.token == 'LN-LABEL':
            word_set = ast.get_nodes_with(
                fetch_list = [ 'LABEL' ],
                skip_list = [ 'LN-LABEL' ], # to avoid duplicate label
                show_text = True
                )
            curr_dict = self.zCompletionDict(word_set - set([node.text]))
        elif node.token in [ 'LABEL', 'CONST', 'CONSTAN-', 'CONSTANT' ]:
            word_set = ast.get_nodes_with(
                fetch_list = [ 'LABEL', 'LN-LABEL', 'CONST', 'CONSTANT' ],
                show_text = True
                )
            curr_dict = self.zCompletionDict(word_set - set([node.text]))
        else:
            return [ ]          # nothing to complete
        return curr_dict.complete(node.text)


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
            elif leaf.token in [ 'QUOTE', 'NUMBER', 'CONST', 'CONSTANT' ]:
                rv.append((curr_pos, 'literal', pos_end))
            elif leaf.token in [ 'TAB-CHAR', 'CONSTAN-' ]:
                rv.append((curr_pos, 'invalid', pos_end))
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

    def __align_part(self, eolast, currpart, alignpos):
        if eolast < alignpos < currpart:
            return self.zBufferChange(
                '{0:{1}}'.format('', currpart - alignpos),
                eolast, 'd'
                )
        elif alignpos < eolast + 1 < currpart:
            return self.zBufferChange(
                '{0:{1}}'.format('', currpart - eolast - 1),
                eolast, 'd'
                )
        elif currpart < alignpos:
            return self.zBufferChange(
                '{0:{1}}'.format('', alignpos - currpart),
                eolast, 'i'
                )
        else:
            return None         # no need to align instruction

