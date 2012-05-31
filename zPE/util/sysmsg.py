from zPE.util.global_config import JES

def IEF237(ddname, ddtype = 'instream', action = 'ALLOCATED'):
    return ' '.join([ 'IEF237I', JES[ddtype], action, 'TO', ddname ])

def IEF285(ddname, path, action):
    return ' '.join([ 'IEF285I', ' ', '{0:<44}'.format(path), action ])

def IGD103(ddname, ddtype = 'file', action = 'ALLOCATED'):
    return ' '.join([ 'IGD103I', JES[ddtype], action, 'TO DDNAME', ddname ])

def IGD104(ddname, path, action):
    return ' '.join([ 'IGD104I', '{0:<44}'.format(path),
                      '{0:<10}'.format(action + ','),
                      'DDNAME={0}'.format(ddname) ])
