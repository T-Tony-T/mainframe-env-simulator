# Architectural Definition
GPR_NUM = 16                    # number of general purpose registers
ADDR_MODE = 31                  # default hardware addressing mode
ADDR_MAX = 2147483647           # the highest possible 31 bit address
MEMORY_SZ = 1048576             # default memory size: 1024K


# Program Definition
LANG_SUPPORTED = {              # all supported languages and their bindings
    'assist':'slv_assist',
    }
def list_lang():                # list all supported languages out
    print 'All programming languages that are currently supported:'
    print '  assist     -- Assembler language using ASSIST'
    print
                 
