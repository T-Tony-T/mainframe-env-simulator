# syntax parser

AST = []



######## ######## ######## ######## ########
########        zSplitWords         ########
######## ######## ######## ######## ########

class zSplitWords(object):
    '''a text splitter'''
    def __init__(self, src = ''):
        self.src = src


    def index_split(self):
        self.len = len(self.src)

        self.res = []           # result holder
        self.indx = 0           # current char index
        self.__parse_begin()

        return self.res


    def split(self):
        return [ self.src[indx_s : indx_e]
                 for (indx_s, indx_e) in self.index_split()
                 ]


    ### supporting function
    def __parse_begin(self):
        while self.indx < self.len:
            # backup the current index
            self.indx_bkup = self.indx

            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch.isspace():    # whitespace out of a word, skip it
                continue

            # parse the word
            if ch == '"':       # start escaping matching
                self.__parse_in_quote()
            else:               # start normal matching
                self.__parse_in_word()

            # add the word to the result
            self.res.append( (self.indx_bkup, self.indx, ) )


    def __parse_in_quote(self):
        while self.indx < self.len:
            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch == '"':       # switch to normal matching
                self.__parse_in_word()
                return


    def __parse_in_word(self):
        while self.indx < self.len:
            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch == '"':       # switch to escaping matching
                self.__parse_in_quote()

            elif ch.isspace():  # whitespace in a word, end matching
                self.indx -= 1  # back up and leave space unhandled
                return
    ### end of supporting function
