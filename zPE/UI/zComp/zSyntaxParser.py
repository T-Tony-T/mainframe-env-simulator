# syntax parser

import sys                      # for sys.maxsize
import re


######## ######## ######## ######## ########
########        zAstLeafNode        ########
######## ######## ######## ######## ########

class zAstLeafNode(object):
    '''
    a leaf node of a (sub) abstract syntax tree;
    has the following members:
        token:  the token type of the element
        text:   the content of the element
        offset: the relative offset to the end of the previous element
    '''
    def __init__(self, token, text, offset = 0):
        self.token  = token
        self.text   = text
        self.offset = offset

    def __str__(self):
        return '{0:>{1}}{2}'.format('', self.offset, self.text)

    def __repr__(self):
        return '{0}({1})'.format(self.token, self.text)

    def __len__(self):
        return self.offset + len(self.text)


    ### the following functions are required by zAstSubTree()
    def index_from_offset(self, abs_pos):
        return [ abs_pos - self.offset ] # negative value suggests pre-token space(s)

    def index_to_offset(self, index):
        return self.offset + index[0]

    def __getitem__(self, index):
        if not (- self.offset) <= index[0] <= len(self.text):
            raise ValueError('absolute offset excess the AST Leaf Node length')
        return self
    ### the above functions are required by zAstSubTree()



######## ######## ######## ######## ########
########        zAstSubTree         ########
######## ######## ######## ######## ########

class zAstSubTree(object):
    '''
    an sub-tree (non-leaf node) of a (sub) abstract syntax tree
    '''
    def __init__(self, token):
        self.token    = token
        self.__list__ = [ ]


    def __str__(self):
        return ''.join([ ele.__str__() for ele in self.__list__ ])

    def __repr__(self):
        return '{0}{1}{2}{3}'.format(self.token, '{ ',
            ', '.join([ ele.__repr__() for ele in self.__list__ ]),
            ' }'
            )

    def __len__(self):
        return len(self.__str__())


    def flat(self, show_text = False):
        rv = [ ]
        def __flat__(node):
            if isinstance(node, zAstSubTree): # non-leaf node
                [ __flat__(ele) for ele in node ]
            else:                             # leaf node
                if show_text:
                    rv.append(node.text)
                else:
                    rv.append(node)
        __flat__(self)
        return rv

    def __contains__(self, content):
        return content in self.flat(show_text = True)

    def count(self, content):
        return self.flat(show_text = True).count(content)


    def index_from_offset(self, abs_pos):
        if abs_pos > self.__len__():
            raise ValueError('absolute offset excess the AST Sub-Tree Node length')
        curr_pos = 0
        search   = 0
        while search < len(self.__list__):
            ele_size = len(self.__list__[search])
            if abs_pos < curr_pos + ele_size:
                # abs_pos corresponding to current sub-tree
                break
            # abs_pos is past current sub-element
            curr_pos += ele_size
            search += 1         # move to next element
        if search < len(self.__list__):
            return [ search ] + self.__list__[search].index_from_offset(abs_pos - curr_pos)
        else:
            return [ search - 1, ele_size ]

    def index_to_offset(self, index):
        curr_pos  = 0
        norm_indx = slice(index[0]).indices(len(self.__list__))[1]
        for search in range(norm_indx):
            curr_pos += len(self.__list__[search])
        return curr_pos + self.__list__[norm_indx].index_to_offset(index[1:])


    def __getitem__(self, index):
        if isinstance(index, list):
            if not -1 <= index[0] <= self.__len__(): # check indexing range
                raise IndexError('AST element index out of range.')
            if len(index) == 1: # last node to be fetched
                return self.__list__[index[0]]
            else:
                return self.__list__[index[0]].__getitem__(index[1:]) # recursive
        else:
            return self.__list__[index]

    def __setitem__(self, index, val):
        if isinstance(index, list):
            self.__getitem__(index[:-1]).__setitem__(index[-1], val)
        else:
            raise ValueError('Assignment of AST Non-Leaf Node is forbidden')


    ### generic list (sub tree) manipulation
    def extend(self, valist):
        self.__list__.extend(valist)

    def append(self, val):
        self.__list__.append(val)

    def insert(self, indx, val):
        self.__list__.insert(indx, val)

    def remove(self, val):
        self.__list__.remove(val)

    def pop(self, indx = -1):
        return self.__list__.pop(indx)
    ### generic list (sub tree) manipulation


    def index(self, content, index_start = 0, index_end = sys.maxsize):
        try:
            return [ str(ele).strip() for ele in self.__list__ ].index(content, index_start, index_end)
        except:
            raise ValueError('content is not in the current level of AST.\n'
                             '\ttry `search_content()` if you need a deep search.')

    def search_content(self, content):
        raise AssertionError('not supported yet.')



######## ######## ######## ######## ########
########       zSyntaxParser        ########
######## ######## ######## ######## ########

class zSyntaxParser(object):
    '''
    the abstract syntax parser that generates an AST based on the
    dictionaries `lvl_dict` and `key_words`.
    '''
    def __init__(self, src, pos_rlvnt = {}, non_split = {}, key_words = {}, level_dlm = {}):
        '''
        src
            the source string to be parsed

        pos_rlvnt
            a dictionary defining the position-relevant non-splitable items;
            anything within such an item will not be parsed further

            if present (non-empty), take the highest precedence

            format = {
                # re should containing exactly 1 catch-group to indicate
                # the intended match
                pos_token   : re_match_exp,
                ...
                }

            Note: this should always be empty for context-free languages

        non_split
            a dictionary defining the regular non-splitable items;
            anything within such an item will not be parsed further

            format = {
                nonsp_token : ( starting_dlm, ending_dlm ),
                ...
                }

            Note: this should be empty in most cases, since it reduces the
                  helpfulness of the AST and increases the parsing time greatly

        key_words
            a dictionary defining the key words the AST should recognize;
            token falls into this category will force a new leaf node to
            be generated, even if there is no spaces around

            format = {
                # re should containing exactly 1 catch-group to indicate
                # the intended match
                key_token   : ( re_match_exp, 0 ), # regular expression match
                key_token   : ( key_word_str, 1 ), # exact string match
                ...
                }

        level_dlm
            a dictionary defining the level delimiter

            if present, take the lowest precedence

            format = {
                level_token : ( starting_dlm, ending_dlm ),
                ...
                }
        '''
        self.__src   = src      # original string

        self.__pos__ = pos_rlvnt
        self.__one__ = non_split
        self.__key__ = key_words
        self.__lvl__ = level_dlm

        self.__parse()


    def __parse(self):
        self.__ast__ = zAstSubTree('_ROOT_')
        self.__lns__ = [ ]      # line-content fast-lookup table

        self.__size  = len(self.__src) # length of original string
        self.__last  = 0        # end of the last element
        self.__indx  = 0        # current char index

        self.__line  = ''       # current line (will be filled by __get_line_at())
        self.__lpos  = -1       # absolute starting position of current line
        self.__eol   = 0        # absolute ending   position of current line
        self.__lnum  = -1       # current line number

        self.__parse_begin(self.__ast__)
        return self


    def __str__(self):
        return str(self.__ast__)

    def __len__(self):
        return len(self.__ast__.flat())


    def get_ast(self):
        return self.__ast__


    def get_nodes_at(self, line_num):
        if line_num < len(self.__lns__):
            return self.__lns__[line_num]
        else:
            return None


    def get_word(self, abs_pos, conn_back = False):
        ( indx_s, indx_e ) = self.get_word_bounds(abs_pos, conn_back)
        return self.__src[indx_s : indx_e]

    def get_word_bounds(self, abs_pos, conn_back = False):
        index = self.__ast__.index_from_offset(abs_pos)
        if index[-1] < 0:       # not within a word
            return ( None, None )
        wlen = len(self.__ast__[index].text)
        while ( conn_back        and           # need to try connecting back
                sum(index[:-1])  and           # not at 1st element
                not self.__ast__[index].offset # not apart from previous element
                ):
            abs_pos -= index[-1] + 1 # move back to previous element
            index = self.__ast__.index_from_offset(abs_pos)
            wlen += len(self.__ast__[index].text)
        indx_s = abs_pos - index[-1]
        return ( indx_s, indx_s + wlen )


    def update(self, buffer_state):
        if not buffer_state:
            return self
        if buffer_state.action == 'i':
            self.__src = ''.join([
                    self.__src[ : buffer_state.offset],
                    buffer_state.content,
                    self.__src[buffer_state.offset : ]
                    ])
        else:
            self.__src = ''.join([
                    self.__src[ : buffer_state.offset],
                    self.__src[buffer_state.offset + len(buffer_state.content) : ]
                    ])
        return self.__parse()

    def reparse(self, pos_rlvnt = {}, non_split = {}, key_words = {}, level_dlm = {}):
        self.__pos__ = pos_rlvnt
        self.__one__ = non_split
        self.__key__ = key_words
        self.__lvl__ = level_dlm

        return self.parse()


    ### supporting function
    def __advance_indx(self, offset, ast_node):
        self.__indx += offset
        if self.__indx < self.__size:
            # check position-relevant token
            self.__parse_pos_relevant(ast_node)


    def __append_lns(self, line_num, node):
        while len(self.__lns__) <= line_num: # line_num start at 0
            self.__lns__.append([])
        self.__lns__[line_num].append(node)

    def __append_curr_lns(self, node):
        self.__get_line_at(self.__indx) # update line info
        self.__append_lns(self.__lnum, node)


    def __parse_begin(self, ast_node):
        if ast_node.token in self.__lvl__: # sub-tree
            # append starting dlm
            dlm_s = self.__lvl__[ast_node.token][0]
            indx_s = self.__indx
            indx_e = indx_s + len(dlm_s)
            if not self.__src.startswith(dlm_s, self.__indx):
                raise SystemError('AST parser failed unexpected.')
            ast_node.append(zAstLeafNode(ast_node.token, self.__src[indx_s : indx_e], indx_s - self.__last))
            self.__append_curr_lns(ast_node[-1])
            self.__last = indx_e # mark the end of the item just parsed
            self.__advance_indx(len(dlm_s), ast_node)

        # check position-relevant token
        self.__parse_pos_relevant(ast_node)

        # main processing loop
        while self.__indx < self.__size:
            # skip whitespaces outside any word
            if self.__src[self.__indx].isspace():
                self.__advance_indx(1, ast_node)

            # try parsing non-splitable item
            elif self.__parse_non_splitable(ast_node):
                pass

            # try parsing reserved words
            elif self.__parse_reserve_word(ast_node):
                pass

            # regular whitespace-separated words left
            else:
                if ast_node.token in self.__lvl__: # sub-tree
                    # check ending dlm first
                    dlm_e = self.__lvl__[ast_node.token][1]
                    if self.__src.startswith(dlm_e, self.__indx):
                        indx_s = self.__indx
                        indx_e = indx_s + len(dlm_e)
                        ast_node.append(zAstLeafNode(ast_node.token, self.__src[indx_s : indx_e], indx_s - self.__last))
                        self.__append_curr_lns(ast_node[-1])
                        self.__last = indx_e # mark the end of the item just parsed
                        return len(dlm_s)    # report to upper level the offset index should be advanced
                else:
                    dlm_e = ' ' # default dlm for word end

                # try parsing level indicator
                word = self.__get_word_at(self.__indx, dlm_e)
                ( token, indx ) = self.__search_level_dlm(word)
                if indx:
                    # e.g. 'word(...' (indx > 0)  or  'word' (indx == -1)
                    if indx < 0:
                        indx = len(word)
                    indx_s = self.__indx
                    indx_e = indx_s + indx
                    ast_node.append(zAstLeafNode('_ITEM_', self.__src[indx_s : indx_e], indx_s - self.__last))
                    self.__append_curr_lns(ast_node[-1])
                    self.__last = indx_e # mark the end of the item just parsed
                    self.__advance_indx(indx, ast_node)
                else:
                    # e.g. '(...' (indx == 0)
                    new_sub_tree = zAstSubTree(token)
                    ast_node.append(new_sub_tree)
                    offset = self.__parse_begin(new_sub_tree) # go to next level
                    self.__advance_indx(offset, ast_node)
        return 0 # index should not be advanced since no content any more


    def __parse_pos_relevant(self, ast_node):
        if self.__indx >= self.__size:
            return None
        for (k, v) in self.__pos__.iteritems():
            match = re.match(v, self.__get_line_at(self.__indx))
            if match:
                indx_s = self.__lpos + match.start(1)
                indx_e = self.__lpos + match.end(1)
                if indx_s == self.__indx:
                    ast_node.append(zAstLeafNode(k, self.__src[indx_s : indx_e], indx_s - self.__last))
                    self.__append_lns(self.__lnum, ast_node[-1])
                    self.__last = indx_e # mark the end of the item just parsed
                    self.__advance_indx(indx_e - indx_s, ast_node)
                    return True
        return False


    def __parse_non_splitable(self, ast_node):
        if self.__indx >= self.__size:
            return None
        for (k, v) in self.__one__.iteritems():
            if self.__src.startswith(v[0], self.__indx):
                indx_s = self.__indx
                indx_e = self.__src.find(v[1], self.__indx + len(v[0]))
                if indx_e >= 0:
                    indx_e += len(v[1]) # to include ending dlm
                else:
                    indx_e = self.__size
                ast_node.append(zAstLeafNode(k, self.__src[indx_s : indx_e], indx_s - self.__last))
                self.__append_curr_lns(ast_node[-1])
                self.__last = indx_e # mark the end of the item just parsed
                self.__advance_indx(indx_e - indx_s, ast_node)
                return True
        return False


    def __parse_reserve_word(self, ast_node):
        if self.__indx >= self.__size:
            return None
        for (k, v) in self.__key__.iteritems():
            if v[-1]:           # exact string match
                if self.__src.startswith(v[0], self.__indx):
                    indx_s = self.__indx
                    indx_e = indx_s + len(v[0])
                    match = True
                else:
                    match = False
            else:               # regular expression match
                match = re.match(v[0], self.__get_word_at(self.__indx))
                if match:
                    indx_s = self.__indx + match.start(1)
                    indx_e = self.__indx + match.end(1)
            if match:
                ast_node.append(zAstLeafNode(k, self.__src[indx_s : indx_e], indx_s - self.__last))
                self.__append_curr_lns(ast_node[-1])
                self.__last = indx_e # mark the end of the item just parsed
                self.__advance_indx(indx_e - indx_s, ast_node)
                return True
        return False


    def __search_level_dlm(self, word):
        for (k, v) in self.__lvl__.iteritems():
            if v[0] in word:
                return ( k, word.index(v[0]), )
        return ( None, -1 )


    def __get_line_at(self, indx):
        if indx < self.__lpos:
            return None         # currently not supporting backward seeking
        if indx < self.__eol:
            return self.__line

        # forward seeking
        self.__lpos = self.__eol
        eol = self.__src.find('\n', indx)
        if eol >= 0:
            self.__line = self.__src[self.__eol : eol + 1] # +1 to including '\n'
            self.__eol  = eol + 1
            cnt = self.__line.count('\n')
        else:
            self.__line = self.__src[self.__eol :        ]
            self.__eol  = self.__size
            cnt = 1             # EoF is considered a virtual '\n'
        self.__lnum += cnt
        if cnt > 1:             # more than 1 line fetched
            # skip "extra" ones
            self.__line = self.__line[self.__line.rindex('\n') + 1 : ]
        return self.__line

    def __get_word_at(self, indx, dlm = None):
        indx_e = indx
        in_quote = None
        while indx_e < self.__size:
            if ( not in_quote  and
                 ( self.__src[indx_e] == dlm  or
                   self.__src[indx_e].isspace()
                   )
                 ):
                break
            if self.__src[indx_e] == in_quote:
                in_quote = None
            elif not in_quote and self.__src[indx_e] in [ '"', "'" ]:
                in_quote = self.__src[indx_e]
            indx_e += 1
        return self.__src[indx : indx_e]
    ### end of supporting function
