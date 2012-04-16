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
        token:    the token type of the element
        text:     the content of the element
        offset:   the relative offset to the end of the previous element
        complete: whether the leaf node is complete or not
    '''
    def __init__(self, token, text, offset = 0, complete = True):
        self.token  = token
        self.text   = text
        self.offset = offset
        self.__complete__ = complete

    def __str__(self):
        # do not use 'format()' since it is slow
        return '%*s%s' % (self.offset, '', self.text)

    def spec(self):
        return '{0}({1})'.format(self.token, self.__complete__ and 'C' or 'I')

    def __repr__(self):
        return '{0}<{1}|{2}>'.format(self.spec(), self.offset, self.text)

    def __len__(self):
        return self.offset + len(self.text)

    def __nonzero__(self):
        return True


    def complete(self, setting = True):
        self.__complete__ = setting

    def iscomplete(self):
        return self.__complete__

    def allcomplete(self):
        return self.iscomplete()


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
    def __init__(self, token, complete = None):
        self.token    = token
        self.__list__ = [ ]
        self.__complete__ = complete


    def __str__(self):
        return ''.join([ ele.__str__() for ele in self.__list__ ])

    def spec(self):
        return '{0}({1})'.format(self.token, self.__complete__ and 'C' or 'I')

    def __repr__(self):
        return '{0}{1}{2}{3}'.format(self.spec(), '{ ',
            ', '.join([ ele.__repr__() for ele in self.__list__ ]),
            ' }'
            )

    def __len__(self):
        return len(self.__str__())

    def __nonzero__(self):
        return True


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


    def complete(self, setting = True):
        self.__complete__ = setting

    def iscomplete(self):
        return self.__complete__

    def allcomplete(self, children_only = False):
        if not children_only and not self.__complete__:
            return False
        for ele in self.__list__:
            if not ele.allcomplete():
                return False
        return True


    def index_from_offset(self, abs_pos):
        if abs_pos > self.__len__():
            raise ValueError('absolute offset excess the AST Sub-Tree Node length')
        next_pos = 0
        for search in range(len(self.__list__)):
            curr_pos = next_pos # backup current position
            next_pos += len(self.__list__[search])
            if abs_pos < next_pos:
                # abs_pos corresponding to current sub-tree
                break
        # search succeed, or reached the end of current (sub-)tree
        return [ search ] + self.__list__[search].index_from_offset(abs_pos - curr_pos)

    def index_to_offset(self, index):
        curr_pos  = 0
        norm_indx = slice(index[0]).indices(len(self.__list__))[1]
        for search in range(norm_indx):
            curr_pos += len(self.__list__[search])
        return curr_pos + self.__list__[norm_indx].index_to_offset(index[1:])

    def list_top_index(self, indx_s, indx_e):
        indx = 0
        while indx_s[indx] == indx_e[indx]:
            indx += 1
        return indx_s[:indx]


    def index(self, node):
        # this is SLOW!!! need to be improved later
        # avoid using it if possible
        for search in range(len(self.__list__)):
            search_node = self.__list__[search]
            if isinstance(search_node, zAstLeafNode):
                if search_node == node:
                    return [ search ]
                else:
                    continue
            else:
                try:
                    return [ search ] + search_node.index()
                except:
                    continue
        raise KeyError('node not in the AST Sub Tree')

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
        self.__lns__ = [        # line-content fast-lookup table
            # (line_offset, content_since_last_node), node_1, node_2, ...
            ]

        self.__size  = len(self.__src) # length of original string
        self.__last  = 0        # end of the last element
        self.__indx  = 0        # current char index

        self.__line  = ''       # current line (will be filled by __get_line_at())
        self.__lpos  = -1       # absolute starting position of current line
        self.__eol   = 0        # absolute ending   position of current line
        self.__lnum  = -1       # current line number

        # mark the start of the root tree
        self.__ast__.append(zAstLeafNode('_TOP_', '', 0))
        self.__append_curr_lns(self.__ast__[-1])

        # fill the root tree
        self.__parse_begin(self.__ast__)

        # mark the end of the root tree
        self.__ast__.append(zAstLeafNode('_EOF_', '', self.__indx - self.__last))
        self.__append_curr_lns(self.__ast__[-1])

        self.__ast__.complete(self.__ast__.allcomplete(children_only = True))
        return self


    def __str__(self):
        return str(self.__ast__)

    def __len__(self):
        return len(self.__ast__.flat())


    def get_ast(self):
        return self.__ast__

    def is_complete(self):
        return self.__ast__.iscomplete()


    def get_nodes_at(self, line_num, ignore_anchor = False):
        '''the offset of first node in the list need to be corrected using get_line_prefix()'''
        if line_num < len(self.__lns__):
            nodes = self.__lns__[line_num][1:]
            if ignore_anchor:
                if nodes and nodes[0].token  == '_TOP_':
                    nodes.pop(0)
                if nodes and nodes[-1].token == '_EOF_':
                    nodes.pop(-1)
            return nodes
        else:
            return None

    def get_line_offset(self, line_num):
        if line_num < len(self.__lns__):
            return self.__lns__[line_num][0][0]
        else:
            return len(self.__src)

    def get_line_prefix(self, line_num):
        if line_num < len(self.__lns__):
            return self.__lns__[line_num][0][1]
        else:
            return None

    def get_line_index(self, node, start = 0, end = sys.maxsize):
        ln = start
        end = min(len(self.__lns__), end)
        while ln < end:
            if node in self.__lns__[ln]:
                return ln
            ln += 1
        return None

    def get_prev_node(self, node_indx, line_num):
        if node_indx > 1:
            return self.__lns__[line_num][node_indx - 1]
        while line_num > 0  and  len(self.__lns__[line_num - 1]) == 1:
            line_num -= 1
        if line_num > 0:
            return self.__lns__[line_num - 1][-1]
        return None

    def get_next_node(self, node_indx, line_num):
        if node_indx < len(self.__lns__[line_num]) - 1:
            return self.__lns__[line_num][node_indx + 1]
        max_line_indx = len(self.__lns__) - 1
        while line_num < max_line_indx  and  len(self.__lns__[line_num + 1]) == 1:
            line_num += 1
        if line_num < max_line_indx:
            return self.__lns__[line_num + 1][1]
        return None

        
    def get_nodes_at_lines(self, ln_s, ln_e):
        return sum([ self.get_nodes_at(ln) for ln in range(ln_s, ln_e) ], [])

    def get_contents_at_lines(self, ln_s, ln_e, prefix = True, surfix = True):
        indx_s = self.get_line_offset(ln_s)
        if prefix:
            prefix = self.get_line_prefix(ln_s)  or  ''
            indx_s -= len(prefix)
        indx_e = self.get_line_offset(ln_e)
        if surfix:
            while ln_e < len(self.__lns__) - 1:
                ln_e += 1
                line = self.__lns__[ln_e]
                if line[0][0] != None:
                    indx_e += len(line[0][1]) - 1
                    break
        return self.__src[indx_s : indx_e]


    def all_complete_at_lines(self, ln_s, ln_e):
        for ln in range(ln_s, ln_e):
            for ele in self.get_nodes_at(ln):
                if not ele.allcomplete():
                    return False
        return True


    def get_word(self, abs_pos, conn_back = False):
        ( indx_s, indx_e ) = self.get_word_bounds(abs_pos, conn_back)
        return self.__src[indx_s : indx_e]

    def get_word_bounds(self, abs_pos, conn_back = False):
        index = self.__ast__.index_from_offset(abs_pos)
        if index[-1] < 0:       # not within a word
            return ( None, None )
        wlen = len(self.__ast__[index].text)
        while ( conn_back                 and  # need to try connecting back
                abs_pos >= index[-1] + 1  and  # not 1st element (_TOP_)
                not self.__ast__[index].offset # not apart from previous element
                ):
            abs_pos -= index[-1] + 1 # move back to previous element
            index = self.__ast__.index_from_offset(abs_pos)
            wlen += len(self.__ast__[index].text)
        indx_s = abs_pos - index[-1]
        return ( indx_s, indx_s + wlen )


    def reparse(self, pos_rlvnt = {}, non_split = {}, key_words = {}, level_dlm = {}):
        self.__pos__ = pos_rlvnt
        self.__one__ = non_split
        self.__key__ = key_words
        self.__lvl__ = level_dlm

        return self.__parse()


    def update(self, change):
        if not change:
            return self

        # calculate effected line range of the change
        index = self.__ast__.index_from_offset(change.offset)
        node  = self.__ast__[index] # must be a leaf node
        ln_s  = self.get_line_index(node)
        ln_e = ln_s + 1
        if change.action == 'd':
            ln_e += change.content.count('\n') # extend effected range to include deleted content
        if index[-1] <= 0:    # insertion/deletion before current node
            node = self.get_prev_node(self.__lns__[ln_s].index(node), ln_s)  or  node
            ln_s = self.get_line_index(node)
        while ln_e < len(self.__lns__)  and  len(self.__lns__[ln_e]) == 1:
            ln_e += 1

        # apply changes
        if change.action == 'i':
            return self.__update_insert(ln_s, change, ln_e)
        else:
            return self.__update_delete(ln_s, change, ln_e)


    def print_tree(self):
        self.__print_subtree('', self.__ast__)


    ### supporting function
    def __advance_indx(self, offset, ast_node):
        self.__indx += offset
        if self.__indx < self.__size:
            # check position-relevant token
            self.__parse_pos_relevant(ast_node)


    def __append_lns(self, line_num, node):
        while len(self.__lns__) <= line_num: # line_num start at 0
            self.__lns__.append([ (None, None) ])
        if len(self.__lns__[line_num]) == 1: # first node in the line
            # update correction offset, if needed
            gross_prefix = self.__src[self.__last : self.__indx]
            net_prefix   = gross_prefix[ : gross_prefix.rfind('\n')+1]
                           # if found, [:rfind()+1] contains net_prefix;
                           # otherwise, rfind()+1 == 0 gives '' as net_prefix
            self.__lns__[line_num][0] = (self.__last + len(net_prefix), net_prefix)
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
            ast_node.complete(False) # mark the sub-tree as incomplete

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
                        ast_node.complete()  # complete the sub-tree
                        return len(dlm_e)    # report to upper level the offset index should be advanced
                else:
                    dlm_e = ' ' # default dlm for word end

                # try parsing level indicator
                word = self.__get_word_at(self.__indx, dlm_e)
                ( token, indx, action ) = self.__search_level_dlm(word)
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
                    # e.g. '(...' (indx == 0)  or  ') ...' (indx == 0, action == 'reform tree')
                    if action == 'normal':
                        new_sub_tree = zAstSubTree(token)
                        ast_node.append(new_sub_tree)
                        offset = self.__parse_begin(new_sub_tree) # go to next level
                        if isinstance(offset, zAstSubTree):
                            # offset is really a new sub-tree to be appended
                            ast_node.append(offset)
                            self.__append_curr_lns(ast_node[-1])
                            self.__last += len(offset)
                            offset = self.__last - self.__indx
                        self.__advance_indx(offset, ast_node)
                    elif action == 'reform tree':
                        dlm_e  = self.__lvl__[token][1]
                        indx_s = self.__indx
                        indx_e = indx_s + len(dlm_e)
                        new_subtree = zAstSubTree(token, False)
                        new_subtree.append(zAstLeafNode(token, self.__src[indx_s : indx_e], indx_s - self.__last))
                        if ast_node.token in self.__lvl__: # sub-tree
                            ast_node.complete(False) # mark the current sub-tree as incomplete
                            return new_subtree # report to upper level the sub-tree need to be appended
                        else:
                            ast_node.append(new_subtree)
                            self.__append_curr_lns(ast_node[-1])
                            self.__last = indx_e
                            self.__advance_indx(len(dlm_e), ast_node)
                    else:
                        raise KeyError('{0}: action not supported!'.format(action))
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
                    complete = True
                else:
                    indx_e = self.__size
                    complete = False
                ast_node.append(zAstLeafNode(k, self.__src[indx_s : indx_e], indx_s - self.__last, complete))
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
        edlm = {                # holding (invalid) ending dlm
            'indx' : len(word),
            'key'  : None,
            }
        for (k, v) in self.__lvl__.iteritems():
            if v[0] in word:
                return ( k, word.index(v[0]), 'normal' )
            if v[1] in word:    # potential invalid ending dlm
                indx = word.index(v[1])
                if indx < edlm['indx']:
                    edlm['indx'] = indx
                    edlm['key']  = k
        if edlm['key']:
            return ( edlm['key'], edlm['indx'], 'reform tree' )
        return ( None, -1, 'pass' )


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



    def __update_insert(self, ln_s, change, ln_e):
        old_complete = self.all_complete_at_lines(ln_s, ln_e)
        if old_complete:
            content = self.get_contents_at_lines(ln_s, ln_e, prefix = True, surfix = True)

            # test change on line content
            offset = change.offset - self.get_line_offset(ln_s) + len(self.get_line_prefix(ln_s))
            update = zSyntaxParser(
                ''.join([ content[ : offset],
                          change.content,
                          content[offset : ]
                          ]),
                pos_rlvnt = self.__pos__,
                non_split = self.__one__,
                key_words = self.__key__,
                level_dlm = self.__lvl__
                )

            if update.is_complete():
                # all  complete   -> all  complete:   safe to modify AST directly
                self.__apply_update(ln_s, update, ln_e) # apply modification

        # apply the change
        self.__src = ''.join([
                self.__src[ : change.offset],
                change.content,
                self.__src[change.offset : ]
                ])
        if old_complete  and  update.is_complete():
            # all  complete   -> all  complete:   safe to modify AST directly
            return self
        else:
            # all  complete   -> some incomplete: may be safe (furture feature)
            # some incomplete -> all  complete:   almost safe (furture feature)
            # some incomplete -> some incomplete: unsafe to modify AST directly
            return self.__parse()

    def __update_delete(self, ln_s, change, ln_e):
        old_complete = self.all_complete_at_lines(ln_s, ln_e)
        if old_complete:
            content = self.get_contents_at_lines(ln_s, ln_e, prefix = True, surfix = True)

            # test change on line content
            offset = change.offset - self.get_line_offset(ln_s) + len(self.get_line_prefix(ln_s))
            update = zSyntaxParser(
                ''.join([ content[ : offset],
                          content[offset + len(change.content) : ]
                          ]),
                pos_rlvnt = self.__pos__,
                non_split = self.__one__,
                key_words = self.__key__,
                level_dlm = self.__lvl__
                )

            if update.is_complete():
                # all  complete   -> all  complete:   safe to modify AST directly
                self.__apply_update(ln_s, update, ln_e) # apply modification

        # apply the change
        self.__src = ''.join([
                self.__src[ : change.offset],
                self.__src[change.offset + len(change.content) : ]
                ])
        if old_complete  and  update.is_complete():
            # all  complete   -> all  complete:   safe to modify AST directly
            return self
        else:
            # all  complete   -> some incomplete: may be safe (furture feature)
            # some incomplete -> all  complete:   almost safe (furture feature)
            # some incomplete -> some incomplete: unsafe to modify AST directly
            return self.__parse()


    def __apply_update(self, ln_s, update, ln_e):
        #self.print_tree()
        #update.print_tree()
        # normalize AST and fast-lookup table
        old_nodes = self.get_nodes_at_lines(ln_s, ln_e)
        if old_nodes[0]  == self.__ast__[0]:
            # 1st node to be removed is TOP, keep it
            keep_top = old_nodes.pop(0)
        else:
            keep_top = None
        update.__lns__[0].pop(1) # remove TOP from 1st line
        if len(update.__lns__[0]) == 1:
            # nothing after TOP in the 1st line
            top_insert = update.__lns__[0][0]
            update.__lns__.pop(0) # remove it
        else:
            top_insert = None

        if old_nodes[-1] == self.__ast__[-1]:
            # last node to be removed is EoF, keep it
            keep_eof = old_nodes.pop()
        else:
            # more nodes follows, record next one
            keep_eof = None
        update.__lns__[-1].pop() # remove EoF from last line
        if len(update.__lns__[-1]) == 1:
            # nothing before EoF in the last line
            eof_insert = update.__lns__[-1][0]
            update.__lns__.pop() # remove it
        else:
            eof_insert = None

        # generate offset modifier
        ln_s_offset = self.get_line_offset(ln_s) - len(self.get_line_prefix(ln_s))
        ln_e_offset = ln_s_offset + len(update.__src) - self.get_line_offset(ln_e)

        # locate outdated nodes
        text = ''.join([ str(node) for node in old_nodes ])
        indx_s = self.__ast__.index_from_offset(ln_s_offset)
        indx_e = self.__ast__.index_from_offset(ln_s_offset + len(text))
        top_indx = self.__ast__.list_top_index(indx_s, indx_e)
        parent = self.__ast__
        for indx in top_indx:
            parent = parent[indx]
        indx_s = indx_s[len(top_indx)]
        indx_e = indx_e[len(top_indx)]

        # update the AST
        for indx in range(indx_s, indx_e):
            parent.pop(indx_s)
        next_node = parent[indx_s]
        for node in update.__ast__[-2:0:-1]: # reverse order, exclude 1st and last nodes
            parent.insert(indx_s, node)

        # correct 1-pass-last node offset
        if not keep_eof:        # more node follows
            node_offset = update.__ast__[-1].offset - len(self.get_line_prefix(ln_e))
        else:                   # EoF  node
            node_offset = update.__ast__[-1].offset - next_node.offset
        next_node.offset += node_offset

        # update fast-lookup table
        for i in range(ln_s, ln_e):
            self.__lns__.pop(ln_s)
        next_line = ln_s
        for line in update.__lns__[-1::-1]: # reverse order
            if line[0][0] == None:
                self.__lns__.insert(ln_s, line)
            else:
                self.__lns__.insert(ln_s, [ (ln_s_offset + line[0][0], line[0][1]) ] + line[1:])
            next_line += 1
        if keep_top:
            if top_insert:
                self.__lns__.insert(ln_s, [ top_insert ])
            self.__lns__[ln_s].insert(1, keep_top)
        if keep_eof:
            if eof_insert:
                self.__lns__.insert(next_line, [ (ln_s_offset + eof_insert[0], eof_insert[1]) ])
                next_line += 1
            self.__lns__[next_line - 1].append(keep_eof)

        # correct all-pass-last line offset
        for ln in range(next_line, len(self.__lns__)):
            line = self.__lns__[ln]
            if line[0][0] != None:
                line[0] = (ln_e_offset + line[0][0], line[0][1])

        #self.print_tree()
        return self


    def __print_subtree(self, leading_msg, treenode):
        if isinstance(treenode, zAstSubTree):
            # sub-tree
            line1 = '{0}{1} -> '.format(leading_msg, treenode.spec())
            if len(treenode):
                self.__print_subtree(line1, treenode[0])
                linen = '{0:{1}}'.format('', len(line1))
                for node in treenode[1:]:
                    self.__print_subtree(linen, node)
            else:
                sys.stderr.write('{0}{1}\n'.format(line1, '[ empty ]'))
        else:
            # leaf node
            sys.stderr.write('{0}{1}\n'.format(leading_msg, repr(treenode)))
    ### end of supporting function
