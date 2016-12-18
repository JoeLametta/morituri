# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

from morituri.common import logcommand
from morituri.result import result

from morituri.common import task, cache

import logging
logger = logging.getLogger(__name__)

class RCCue(logcommand.Lager):
    summary = "write a cue file for the cached result"
    description = summary

    def do(self, args):
        self._cache = cache.ResultCache()

        try:
            discid = args[0]
        except IndexError:
            self.stderr.write(
                'Please specify a cddb disc id\n')
            return 3

        persisted = self._cache.getRipResult(discid, create=False)

        if not persisted:
            self.stderr.write(
                'Could not find a result for cddb disc id %s\n' % discid)
            return 3

        self.stdout.write(persisted.object.table.cue().encode('utf-8'))


class RCList(logcommand.Lager):
    summary = "list cached results"
    description = summary

    def do(self, args):
        self._cache = cache.ResultCache()
        results = []

        for i in self._cache.getIds():
            r = self._cache.getRipResult(i, create=False)
            results.append((r.object.artist, r.object.title, i))

        results.sort()

        for artist, title, cddbid in results:
            if artist is None:
                artist = '(None)'
            if title is None:
                title = '(None)'

            self.stdout.write('%s: %s - %s\n' % (
                cddbid, artist.encode('utf-8'), title.encode('utf-8')))


class RCLog(logcommand.Lager):
    summary = "write a log file for the cached result"
    description = summary
    #formatter_class = argparse.

    def add_arguments(self):
        loggers = result.getLoggers().keys()

        self.parser.add_argument(
            '-L', '--logger',
            action="store", dest="logger",
            default='morituri',
            help="logger to use (choose from '" + "', '".join(loggers) + "')"
        )

    def do(self, args):
        self._cache = cache.ResultCache()

        persisted = self._cache.getRipResult(args[0], create=False)

        if not persisted:
            self.stderr.write(
                'Could not find a result for cddb disc id %s\n' % args[0])
            return 3

        try:
            klazz = result.getLoggers()[self.options.logger]
        except KeyError:
            self.stderr.write("No logger named %s found!\n" % (
                self.options.logger))
            return 3

        logger = klazz()
        self.stdout.write(logger.log(persisted.object).encode('utf-8'))


class ResultCache(logcommand.Lager):
    summary = "debug result cache"
    description = summary

    subcommands = {
        'cue':  RCCue,
        'list': RCList,
        'log':  RCLog,
    }


class Checksum(logcommand.Lager):
    summary = "run a checksum task"
    description = summary

    def add_arguments(self):
        self.parser.add_argument('files', nargs='+', action='store',
                                 help="audio files to checksum")

    def do(self):
        runner = task.SyncRunner()
        # here to avoid import gst eating our options
        from morituri.common import checksum

        for f in self.options.files:
            fromPath = unicode(f)
            checksumtask = checksum.CRC32Task(fromPath)
            runner.run(checksumtask)
            self.stdout.write('Checksum: %08x\n' % checksumtask.checksum)


class Encode(logcommand.Lager):
    summary = "run an encode task"
    description = summary

    def add_arguments(self):
        # here to avoid import gst eating our options
        from morituri.common import encode

        default = 'flac'
        # slated for deletion as flac will be the only encoder
        self.parser.add_argument('--profile',
            action="store",
            dest="profile",
            help="profile for encoding (default '%s', choices '%s')" % (
                default, "', '".join(encode.ALL_PROFILES.keys())),
            default=default)
        self.parser.add_argument('input', action='store',
                                 help="audio file to encode")
        self.parser.add_argument('output', nargs='?', action='store',
                                 help="output path")

    def do(self):
        from morituri.common import encode
        profile = encode.ALL_PROFILES[self.options.profile]()

        try:
            fromPath = unicode(self.options.input)
        except IndexError:
            # unexercised after BaseCommand
            self.stdout.write('Please specify an input file.\n')
            return 3

        try:
            toPath = unicode(self.options.output)
        except IndexError:
            toPath = fromPath + '.' + profile.extension

        runner = task.SyncRunner()

        logger.debug('Encoding %s to %s',
            fromPath.encode('utf-8'),
            toPath.encode('utf-8'))
        encodetask = encode.EncodeTask(fromPath, toPath, profile)

        runner.run(encodetask)

        self.stdout.write('Peak level: %r\n' % encodetask.peak)
        self.stdout.write('Encoded to %s\n' % toPath.encode('utf-8'))


class MaxSample(logcommand.Lager):
    summary = "run a max sample task"
    description = summary
    
    def add_arguments(self):
        self.parser.add_argument('files', nargs='+', action='store',
                                 help="audio files to sample")

    def do(self):
        runner = task.SyncRunner()
        # here to avoid import gst eating our options
        from morituri.common import checksum

        for arg in self.options.files:
            fromPath = unicode(arg.decode('utf-8'))

            checksumtask = checksum.MaxSampleTask(fromPath)

            runner.run(checksumtask)

            self.stdout.write('%s\n' % arg)
            self.stdout.write('Biggest absolute sample: %04x\n' %
                checksumtask.checksum)


class Tag(logcommand.Lager):
    summary = "run a tag reading task"
    description = summary

    def add_arguments(self):
        self.parser.add_argument('file', action='store',
                                 help="audio file to tag")

    def do(self):
        try:
            path = unicode(self.options.file)
        except IndexError:
            self.stdout.write('Please specify an input file.\n')
            return 3

        runner = task.SyncRunner()

        from morituri.common import encode
        logger.debug('Reading tags from %s' % path.encode('utf-8'))
        tagtask = encode.TagReadTask(path)

        runner.run(tagtask)

        for key in tagtask.taglist.keys():
            self.stdout.write('%s: %r\n' % (key, tagtask.taglist[key]))


class MusicBrainzNGS(logcommand.Lager):
    summary = "examine MusicBrainz NGS info"
    description = """Look up a MusicBrainz disc id and output information.

You can get the MusicBrainz disc id with rip cd info.

Example disc id: KnpGsLhvH.lPrNc1PBL21lb9Bg4-"""

    def add_arguments(self):
        self.parser.add_argument('mbdiscid', action='store',
                                 help="MB disc id to look up")

    def do(self):
        try:
            discId = unicode(self.options.mbdiscid)
        except IndexError:
            self.stdout.write('Please specify a MusicBrainz disc id.\n')
            return 3

        from morituri.common import mbngs
        metadatas = mbngs.musicbrainz(discId, record=self.options.record)

        self.stdout.write('%d releases\n' % len(metadatas))
        for i, md in enumerate(metadatas):
            self.stdout.write('- Release %d:\n' % (i + 1, ))
            self.stdout.write('    Artist: %s\n' % md.artist.encode('utf-8'))
            self.stdout.write('    Title:  %s\n' % md.title.encode('utf-8'))
            self.stdout.write('    Type:   %s\n' % md.releaseType.encode('utf-8'))
            self.stdout.write('    URL: %s\n' % md.url)
            self.stdout.write('    Tracks: %d\n' % len(md.tracks))
            if md.catalogNumber:
                self.stdout.write('    Cat no: %s\n' % md.catalogNumber)
            if md.barcode:
                self.stdout.write('   Barcode: %s\n' % md.barcode)

            for j, track in enumerate(md.tracks):
                self.stdout.write('      Track %2d: %s - %s\n' % (
                    j + 1, track.artist.encode('utf-8'),
                    track.title.encode('utf-8')))


class CDParanoia(logcommand.Lager):
    summary = "show cdparanoia version"
    description = summary

    def do(self):
        from morituri.program import cdparanoia
        version = cdparanoia.getCdParanoiaVersion()
        self.stdout.write("cdparanoia version: %s\n" % version)


class CDRDAO(logcommand.Lager):
    summary = "show cdrdao version"
    description = summary

    def do(self):
        from morituri.program import cdrdao
        version = cdrdao.getCDRDAOVersion()
        self.stdout.write("cdrdao version: %s\n" % version)


class Version(logcommand.Lager):
    summary = "debug version getting"
    description = summary

    subcommands = {
        'cdparanoia': CDParanoia,
        'cdrdao': CDRDAO,
    }


class Debug(logcommand.Lager):
    summary = "debug internals"
    description = "debug internals"

    subcommands = {
        'checksum':       Checksum,
        'encode':         Encode,
        'maxsample':      MaxSample,
        'tag':            Tag,
        'musicbrainzngs': MusicBrainzNGS,
        'resultcache':    ResultCache,
        'version':        Version,
    }
