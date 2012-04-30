# this defines the CPU execution details

EXCEPTION_STACK = [ ]

def e_size():
    '''get the size of the stack'''
    return len(EXCEPTION_STACK)

def e_empty():
    '''test whether the stack is empty'''
    return not len(EXCEPTION_STACK)

def e_clear():
    '''clear the stack'''
    del EXCEPTION_STACK[:]
    return

def e_push(e):
    '''push a new exception into the stack'''
    EXCEPTION_STACK.append(e)
    return

def e_pop():
    '''pop an exception out of the stack'''
    if e_empty():
        return None
    return EXCEPTION_STACK.pop()

def e_peek():
    '''peek at the last exception on the stack'''
    if e_empty():
        return None
    return EXCEPTION_STACK[-1]

def e_dump():
    '''dump the entire stack'''
    if e_empty():
        trace = [ '[ no exception found ]\n' ]
    else:
        trace = [ repr(e) for e in EXCEPTION_STACK ]
    return '\n'.join(
        [ 'Exception Trace: (same order as they occured)\n--------' ] + trace
        )


### exception definition
##  base exception
class zPException(Exception):
    _type_ = {
        'S' : 'SYSTEM',
        'U' : 'UTILITY',
        }

    def __init__(self, etype, ecode, emsg, *extra):
        self.args = (etype, ecode, emsg) + extra

    def __repr__(self):
        return '{0}{1} {2}\nextra msg(s): {3}\n'.format(
            self.args[0], self.args[1], self.args[2],
            repr(self.args[3:]) # extra
            )
    def __str__(self):
        return '{0:>8} = {1} {2}'.format(self.type(), self.code(), self.text())

    def __dict__(self):
        return {
            'type'  : self.args[0],
            'code'  : self.args[1],
            'text'  : self.args[2],
            'extra' : self.args[3:],
            }

    def type(self):
        return self._type_[self.args[0]]

    def code(self):
        return self.args[1]

    def text(self):
        return self.args[2]

    def extra(self):
        return self.args[3:]


##  system exception
def newSystemException(ecode, emsg, *extra):
    return zPException('S', ecode, emsg, *extra)

##  utility exception
def newUtilityException(ecode, emsg, *extra):
    return zPException('U', ecode, emsg, *extra)


#   commonly used exceptions
def newOperationException(* extra):
    return newSystemException('0C1', 'OPERATION EXCEPTION', *extra)

def newProtectionException(* extra):
    return newSystemException('0C4', 'PROTECTION EXCEPTION', *extra)

def newAddressingException(* extra):
    return newSystemException('0C5', 'ADDRESSING EXCEPTION', *extra)

def newSpecificationException(* extra):
    return newSystemException('0C6', 'SPECIFICATION EXCEPTION', *extra)

def newDataException(* extra):
    return newSystemException('0C7', 'DATA EXCEPTION', *extra)

def newFixedPointOverflowException(* extra):
    return newSystemException('0C8', 'FIXED POINT OVERFLOW EXCEPTION', *extra)

def newFixedPointDivideException(* extra):
    return newSystemException('0C9', 'FIXED POINT DEVIDE EXCEPTION', *extra)

def newDecimalOverflowException(* extra):
    return newSystemException('0CA', 'DECIMAL OVERFLOW EXCEPTION', *extra)

def newDecimalDivideException(* extra):
    return newSystemException('0CB', 'DECIMAL DEVIDE EXCEPTION', *extra)
