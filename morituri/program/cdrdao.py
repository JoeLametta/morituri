import logging
import os
import re
import tempfile
from subprocess import check_call, Popen, PIPE, CalledProcessError

from morituri.image.toc import TocFile

CDRDAO = 'cdrdao'

def read_toc(device, fast_toc=False):
    """
    Return cdrdao-generated table of contents for 'device'.
    """
    # cdrdao MUST be passed a non-existing filename as its last argument
    # to write the TOC to; it does not support writing to stdout or
    # overwriting an existing file, nor does linux seem to support
    # locking a non-existant file. Thus, this race-condition introducing
    # hack is carried from morituri to whipper and will be removed when
    # cdrdao is fixed.
    fd, tocfile = tempfile.mkstemp(suffix=u'.cdrdao.read-toc.whipper')
    os.close(fd)
    os.unlink(tocfile)

    cmd = [CDRDAO, 'read-toc', '--device', device, tocfile]
    if fast_toc:
        cmd.insert(2, '--fast-toc')
    # PIPE is the closest to >/dev/null we can get
    try:
        check_call(cmd, stdout=PIPE, stderr=PIPE)
    except CalledProcessError, e:
        logging.warning('cdrdao read-toc failed: return code is non-zero: ' +
                        str(e.returncode))
        raise e
    toc = TocFile(tocfile)
    toc.parse()
    os.unlink(tocfile)
    return toc

def version():
    """
    Return cdrdao version as a string.
    """
    cdrdao = Popen(CDRDAO, stderr=PIPE)
    out, err = cdrdao.communicate()
    if cdrdao.returncode != 1:
        logging.warning("cdrdao version detection failed: "
                        "return code is " + str(cdrdao.returncode))
        return None
    m = re.compile(r'^Cdrdao version (?P<version>.*) - \(C\)').search(
                   err.decode('utf-8'))
    if not m:
        logging.warning("cdrdao version detection failed: "
                + "could not find version")
        return None
    return m.group('version')

def ReadTOCTask(device):
    """
    stopgap morituri-insanity compatability layer
    """
    return read_toc(device, fast_toc=True)

def ReadTableTask(device):
    """
    stopgap morituri-insanity compatability layer
    """
    return read_toc(device)

def getCDRDAOVersion():
    """
    stopgap morituri-insanity compatability layer
    """
    return version()
