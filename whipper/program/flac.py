from subprocess import check_call, CalledProcessError

import logging
logger = logging.getLogger(__name__)


def encode(infile, outfile, extraArgs=None):
    """
    Encode infile to outfile, with flac.

    extraArgs is a list of additional arguments for the flac binary

    Uses ``-f`` because whipper already creates the file.
    """
    cmd = ['flac', '--silent', '--verify' ]
    cmd.extend(extraArgs or [])
    cmd.extend(['-o', outfile, '-f', infile])
    logger.debug("executing %r", cmd)
    try:
        # TODO: Replace with Popen so that we can catch stderr and write it to
        # logging
        check_call(cmd)
    except CalledProcessError:
        logger.exception('flac failed')
        raise
