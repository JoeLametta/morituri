# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import pkg_resources
import musicbrainzngs
import site
import whipper
from distutils.sysconfig import get_python_lib
from whipper.command import cd, offset, drive, image, accurip, mblookup
from whipper.command.basecommand import BaseCommand
from whipper.common import common, directory, config
from whipper.extern.task import task
from whipper.program.utils import eject_device
from whipper.program import cdparanoia

import logging
logger = logging.getLogger(__name__)


def main():
    cdparanoia_cmd = config.Config().get('main', 'cdparanoia')
    if cdparanoia_cmd:
        cdparanoia.setCdParanoiaCommand(cdparanoia_cmd)

    server = config.Config().get_musicbrainz_server()
    https_enabled = server['scheme'] == 'https'
    try:
        musicbrainzngs.set_hostname(server['netloc'], https_enabled)
    # Parameter 'use_https' is missing in versions of musicbrainzngs < 0.7
    except TypeError:
        logger.warning("Parameter 'use_https' is missing in versions of "
                       "musicbrainzngs < 0.7. This means whipper will only "
                       "be able to communicate with the configured "
                       "MusicBrainz server ('%s') over plain HTTP. If a "
                       "custom server which speaks HTTPS only has been "
                       "declared, a suitable version of the "
                       "musicbrainzngs module will be needed "
                       "to make it work in whipper.", server['netloc'])
        musicbrainzngs.set_hostname(server['netloc'])

    # Find whipper's plugins paths (local paths have higher priority)
    plugins_p = [directory.data_path('plugins')]  # local path (in $HOME)
    if hasattr(sys, 'real_prefix'):  # no getsitepackages() in virtualenv
        plugins_p.append(
            get_python_lib(plat_specific=False, standard_lib=False,
                           prefix='/usr/local') + '/whipper/plugins')
        plugins_p.append(get_python_lib(plat_specific=False,
                         standard_lib=False) + '/whipper/plugins')
    else:
        plugins_p += [x + '/whipper/plugins' for x in site.getsitepackages()]

    # register plugins with pkg_resources
    distributions, _ = pkg_resources.working_set.find_plugins(
        pkg_resources.Environment(plugins_p)
    )
    list(map(pkg_resources.working_set.add, distributions))
    try:
        cmd = Whipper(sys.argv[1:], os.path.basename(sys.argv[0]), None)
        ret = cmd.do()
    except SystemError as e:
        logger.critical("SystemError: %s", e)
        if (isinstance(e, common.EjectError) and
                cmd.options.eject in ('failure', 'always')):
            # XXX: Pylint, instance of 'SystemError' has no 'device' member
            eject_device(e.device)
        return 255
    except RuntimeError as e:
        print(e)
        return 1
    except KeyboardInterrupt:
        return 2
    except ImportError:
        raise
    except task.TaskException as e:
        if isinstance(e.exception, ImportError):
            raise ImportError(e.exception)
        elif isinstance(e.exception, common.MissingDependencyException):
            logger.critical('missing dependency "%s"', e.exception.dependency)
            return 255

        if isinstance(e.exception, common.EmptyError):
            logger.debug("EmptyError: %s", e.exception)
            logger.critical('could not create encoded file')
            return 255

        # in python3 we can instead do `raise e.exception` as that would show
        # the exception's original context
        logger.critical(e.exceptionMessage)
        return 255
    return ret if ret else 0


class Whipper(BaseCommand):
    description = (
        "whipper is a CD ripping utility focusing on accuracy over speed.\n\n"
        "whipper gives you a tree of subcommands to work with.\n"
        "You can get help on subcommands by using the -h option "
        "to the subcommand.\n")
    no_add_help = True
    subcommands = {
        'accurip': accurip.AccuRip,
        'cd': cd.CD,
        'drive': drive.Drive,
        'offset': offset.Offset,
        'image': image.Image,
        'mblookup': mblookup.MBLookup
    }

    def add_arguments(self):
        self.parser.add_argument('-R', '--record',
                                 action='store_true', dest='record',
                                 help="record API requests for playback")
        self.parser.add_argument('-v', '--version',
                                 action="store_true", dest="version",
                                 help="show version information")
        self.parser.add_argument('-h', '--help',
                                 action="store_true", dest="help",
                                 help="show this help message and exit")
        self.parser.add_argument('-e', '--eject',
                                 action="store", dest="eject",
                                 default="success",
                                 choices=('never', 'failure',
                                          'success', 'always'),
                                 help="when to eject disc (default: success)"),
        self.parser.add_argument('-c', '--drive-auto-close', action="store",
                                 dest="drive_auto_close", default=True,
                                 help="whether to auto close the drive's "
                                 "tray before reading a CD (default: True)")

    def handle_arguments(self):
        if self.options.help:
            self.parser.print_help()
            sys.exit(0)
        if self.options.version:
            print("whipper %s" % whipper.__version__)
            sys.exit(0)
