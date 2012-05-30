# this is the text buffer module (and their supports) of the zComponent package

import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########       zBufferChange        ########
######## ######## ######## ######## ########

class zBufferChange(object):
    '''a node keeps track of the change in a text buffer. this is used to implement undo / redo system'''
    revert_action = {
        'i' : 'd',
        'd' : 'i',
        }

    def __init__(self, content, offset, action):
        '''
        content
            the content that changed from the last recorded state.

        offset
            the offset into the buffer of the change above.

        action
            'i' / 'a' : the indicated content is inserted / added to the buffer
            'd' / 'r' : the indicated content is deleted / removed from the buffer
        '''
        if not isinstance(content, str):
            raise ValueError('{0}: content need to be an string!'.format(content))
        self.content = content

        if not isinstance(offset, int) or offset < 0:
            raise ValueError('{0}: offset need to be a non-negative integer!'.format(offset))
        self.offset  = offset

        if action in [ 'i', 'a', ]:
            self.action = 'i'
        elif action in [ 'd', 'r', ]:
            self.action = 'd'
        else:
            raise ValueError(
                '{0}: action need to be "i" / "a" for insert / add, or "d" / "r" for delete / remove!'.format(action)
                )

    def __str__(self):
        if self.action == 'i':
            action = 'INSERT'
        else:
            action = 'DELETE'
        return '{0}: <<{1}>> AT offset {2}'.format(action, self.content, self.offset)


    def revert(self):
        return zBufferChange(self.content, self.offset, zBufferChange.revert_action[self.action])


class zAtomicChange(object):
    '''an atomic change (state) consists of a (list of) zBufferChange(s)'''
    def __init__(self, buff_changes):
        self.__state__ = []
        for change in buff_changes:
            self.__state__.append(change)

    def __str__(self):
        return ' => '.join([ str(change) for change in self.__state__ ])

    def __len__(self):
        return len(self.__state__)

    def __getitem__(self, key):
        return self.__state__[key]

    def append(self, new_change):
        self.__state__.append(new_change)

    def pop(self, index = -1):
        return self.__state__.pop(index)

    def revert(self):
        return zAtomicChange([ change.revert() for change in self.__state__ ][::-1])



######## ######## ######## ######## ########
########         zUndoStack         ########
######## ######## ######## ######## ########

class zUndoStack(object):
    '''an modified Emacs-Style Undo / Redo System implemeted using Stack (List)'''
    def __init__(self, init_content):
        self.clear(init_content)

    def __str__(self):
        rv_list = [ '[\n' ]
        for state in self.__stack:
            if self.is_saved(state):
                saved_indicator = '*'
            else:
                saved_indicator = ' '

            rv_list.append('{0}  {1:0>3}:  {2}\n'.format(saved_indicator, self.get_group_id(state), state))
        rv_list.append(']\n')

        return ''.join(rv_list)


    def clear(self, init_content = ''):
        '''reset the entire undo-stack'''
        init_state = zAtomicChange([ zBufferChange(init_content, 0, 'i') ])

        self.__stack = [ init_state ]
        self.__top   = 0        # top index (of the undo-stack)
        self.__undo  = 0        # current undo index

        self.__group = [        # any states within the same group are "equvilent"
            [ init_state ],
            ]
        self.__group_saved = 0  # the index of the group that state(s) is equvilent to the saved one


    def is_init(self):
        '''test whether the current state is an initial-state (no former edit)'''
        return self.__undo == 0

    def is_last(self):
        '''test whether the current state is an end-state (no former undo)'''
        return self.__undo == self.__top


    def is_saved(self, state = None):
        '''test whether the given state (current state, if not specified) is saved'''
        if not state:
            state = self.get_current_state()
        return state in self.__group[self.__group_saved]

    def get_group_id(self, state):
        '''retrieve the group ID for a specific state'''
        for indx in range(len(self.__group)):
            if state in self.__group[indx]:
                break
        return indx


    def get_current_state(self):
        '''retrieve the current state'''
        return self.__stack[-1]

    def save_current_state(self):
        '''mark the group of the current state as "saved"'''
        self.__group_saved = self.get_group_id(self.get_current_state())


    def new_state(self, new_state):
        '''push a new edit onto the stack'''
        self.__stack.append(new_state)
        self.__top  = len(self.__stack) - 1     # update the top index
        self.__undo = self.__top                # point the undo index to the top of the stack
        self.__group.append([ new_state ])      # add the new state into a new group

    def undo(self):
        '''push an "undo" onto the stack; this will *NOT* modified any buffer'''
        if self.is_init():
            return None # stack is at initial state, cannot undo

        undo_state = self.__stack[self.__undo].revert() # revert the state of undo index
        self.__stack.append(undo_state)                 # push the reverted state onto the stack

        self.__undo -= 1        # decrement the undo index to the previous state
        self.__group[self.get_group_id(self.__stack[self.__undo])].append(undo_state) # update group list

        return undo_state

    def redo(self):
        '''pop an "undo" out of the stack; this will *NOT* modified any buffer'''
        if self.is_last():
            return None # no former undo(s), cannot redo

        redo_state = self.__stack.pop() # pop the last state out of the stack

        self.__group[self.get_group_id(self.__stack[self.__undo])].remove(redo_state) # update group list
        self.__undo += 1        # increment the undo index to the next state

        return redo_state.revert()      # pop the reverted last state out of the stack



######## ######## ######## ######## ########
########         zKillRing          ########
######## ######## ######## ######## ########
class zKillRing(object):
    '''the kill-ring widget'''
    @classmethod
    def __init_kill_ring(cls):
        cls.__curr_corpse = None # for pop (resurrect)
        cls.__curr_grave  = 0    # for push (kill)

        cls.__kill_ring = [ None ] * cls.__capacity

        # record the current clipboards' content
        cls.__cb_text['primary']   = cls.__cb['primary'].wait_for_text()
        cls.__cb_text['clipboard'] = cls.__cb['clipboard'].wait_for_text()


    __capacity = 16
    __primary_hold = None

    __cb = {
        'primary'   : gtk.clipboard_get('PRIMARY'),
        'clipboard' : gtk.clipboard_get('CLIPBOARD'),
        }

    # the following should be exactly the same as cls.__init_kill_ring()
    __curr_corpse = None        # for pop (resurrect)
    __curr_grave  = 0           # for push (kill)

    __kill_ring = [ None ] * __capacity

    # record the current clipboards' content
    __cb_text = {
        'primary'   : __cb['primary'].wait_for_text(),
        'clipboard' : __cb['clipboard'].wait_for_text(),
        }
    # the above should be exactly the same as cls.__init_kill_ring()


    @classmethod
    def is_empty(cls):
        return None == cls.__curr_corpse


    @classmethod
    def get_kill_ring_size(cls):
        return cls.__capacity

    @classmethod
    def set_kill_ring_size(cls, size):
        cls.__capacity  = size
        cls.__primary_hold = None
        cls.__init_kill_ring()


    @classmethod
    def append_killing(cls, text):
        if cls.__kill_cb():     # successfully pushed whatever in the clipboard into the kill ring
            cls.kill(text)      # chain has been broken, no appending occur
        else:
            cls.__curr_grave = cls.__curr_corpse # kick out the last corpse
            cls.kill(cls.__kill_ring[cls.__curr_corpse] + text) # kill the appended version

    def prepend_killing(cls, text):
        if cls.__kill_cb():     # successfully pushed whatever in the clipboard into the kill ring
            cls.kill(text)      # chain has been broken, no prepending occur
        else:
            cls.__curr_grave = cls.__curr_corpse # kick out the last corpse
            cls.kill(text + cls.__kill_ring[cls.__curr_corpse]) # kill the prepended version

    @classmethod
    def kill(cls, text, clear = False):
        cls.__kill_cb()                      # push whatever in the clipboard if the content has been changed
        if clear:
            cls.__cb_text['clipboard'] = ''  # clear the backup clipboard
        cls.__cb['clipboard'].set_text(text) # push the text into system clipboard
        while cls.__cb['clipboard'].wait_for_text() != text:
            continue            # wait for system clipboard to sync
        cls.__kill_cb()         # push the just-added clipboard content into the kill ring

    @classmethod
    def resurrect(cls):
        cls.__kill_cb()                      # push whatever in the clipboard if the content has been changed

        if cls.is_empty():
            # kill-ring is empty
            if cls.__cb_text['primary']  and  cls.__primary_hold != cls.__cb_text['primary']:
                # put primary clipboard text into kill-ring
                cls.kill(cls.__cb_text['primary'], clear = True)

            elif cls.__cb_text['clipboard']:
                # put clipboard text into kill-ring
                cls.kill(cls.__cb_text['clipboard'], clear = True)

        if cls.is_empty():
            return None
        else:
            return cls.__kill_ring[cls.__curr_corpse]

    @classmethod
    def circulate_resurrection(cls):
        if not cls.is_empty():
            # only if kill-ring is not empty
            cls.__curr_corpse = (cls.__curr_corpse - 1) % cls.__capacity
            while not cls.__kill_ring[cls.__curr_corpse]:
                # skip empty slot
                cls.__curr_corpse = (cls.__curr_corpse - 1) % cls.__capacity

            return cls.resurrect()  # ought to contain something from kill-ring, not from clipboard
        else:
            return None


    ### supporting functions
    @classmethod
    def __really_kill(cls, text):
        if text:
            cls.__kill_ring[cls.__curr_grave] = text

            # update indices
            cls.__curr_corpse = cls.__curr_grave
            cls.__curr_grave  = (cls.__curr_grave + 1) % cls.__capacity

            return True         # kill +1
        else:
            return False        # kill nothing

    @classmethod
    def __kill_cb(cls):
        c_text = cls.__cb['clipboard'].wait_for_text()

        if cls.__cb_text['clipboard'] != c_text:
            # check clipboard first
            killed = cls.__really_kill(c_text)  # try killing the new content
            cls.__cb_text['clipboard'] = c_text # synchronize the backup
        else:
            killed = False

        p_text = cls.__cb['primary'].wait_for_text()

        if not killed and cls.__cb_text['primary'] != p_text:
            # if no kill for clipboard, check primary
            killed = cls.__really_kill(p_text)  # try killing the new content
            cls.__cb_text['primary'] = p_text   # synchronize the backup
            cls.__primary_hold = p_text         # hold the kill

        return killed
    ### end of supporting functions



######## ######## ######## ######## ########
########       zCompletionDict      ########
######## ######## ######## ######## ########

class zCompletionDict(object):
    '''completion dictionary used for generating completion list'''
    def __init__(self, word_set):
        self.__root__ = { '' : False } # root cannot be end-of-word
        self.__cnt__  = 0
        self.update(word_set)


    def __contains__(self, word):
        sub = self.subdict(word)
        return sub and sub['']

    def __len__(self):
        return self.__cnt__


    def add(self, word):
        '''add a word into the dict'''
        if word in self:
            return              # no need to add, early return
        ptr = self.__root__
        for ch in word:
            ptr[ch] = ptr.has_key(ch) and ptr[ch] or { '' : False }
            ptr = ptr[ch]
        ptr[''] = True          # turn on end-of-word mark
        self.__cnt__ += 1


    def complete(self, word):
        '''return the list of all possible completions of the word'''
        sub = self.subdict(word)
        return sub and self.listify(word, sub) or [ ]


    def dump(self):
        return self.__root__


    def listify(self, prefix = '', subdict = None):
        if not subdict:
            subdict = self.dump()
        return [ ''.join(chlist) for chlist in self.__listify__([ prefix ], subdict) ]

    def __listify__(self, prefix, subdict):
        rv = [ ]
        if subdict['']:
            rv.append(prefix)
        for key in subdict.iterkeys():
            if not key:         # '' is end-of-word mark, ignore it
                continue
            rv.extend(self.__listify__(prefix + [ key ], subdict[key]))
        return rv


    def subdict(self, word):
        '''return the subdict with prefix equal to the given word, or None if not found'''
        ptr = self.__root__
        for ch in word:
            if not ch in ptr:
                return None
            ptr = ptr[ch]
        return ptr


    def update(self, word_set):
        '''update the dict with a set of words'''
        for word in word_set:
            self.add(word)

