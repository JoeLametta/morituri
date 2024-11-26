# -*- Mode: Python; test-case-name: whipper.test.test_common_program -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (C) 2009, 2010, 2011 Thomas Vander Stichele

# This file is part of whipper.
#
# whipper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# whipper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with whipper.  If not, see <http://www.gnu.org/licenses/>.

"""Common functionality and class for all programs using whipper."""

import musicbrainzngs
import re
import os
import shutil
import time

from tempfile import NamedTemporaryFile
from whipper.common import accurip, checksum, common, mbngs, path
from whipper.program import cdrdao, cdparanoia
from whipper.result import result
from whipper.image import image
from whipper.extern import freedb
from whipper.extern.task import task

import logging
logger = logging.getLogger(__name__)


# FIXME: should Program have a runner ?


class Program:
    """
    I maintain program state and functionality.

    :vartype metadata: mbngs.DiscMetadata
    :cvar result: the rip's result
    :vartype result: result.RipResult
    :vartype outdir: str
    :vartype config: whipper.common.config.Config
    """

    cuePath = None
    logPath = None
    metadata = None
    outdir = None
    result = None
    skipped_tracks = None

    def __init__(self, config, record=False):
        """
        Init Program.

        :param record: whether to record results of API calls for playback
        """
        self._record = record
        self._config = config

        d = {}

        for key, default in list({
            'dot': True,
            'posix': True,
            'vfat': False,
            'whitespace': False,
            'printable': False
        }.items()):
            value = None
            value = self._config.getboolean('main', 'path_filter_' + key)
            if value is None:
                value = default

            d[key] = value

        self._filter = path.PathFilter(**d)

    @staticmethod
    def setWorkingDirectory(workingDirectory):
        if workingDirectory:
            logger.info('changing to working directory %s', workingDirectory)
            os.chdir(workingDirectory)

    @staticmethod
    def getFastToc(runner, device):
        """
        Retrieve the normal TOC table from the drive.

        Also warn about buggy cdrdao versions.
        """
        from pkg_resources import parse_version as V
        version = cdrdao.version()
        if V(version) < V('1.2.3rc2'):
            logger.warning('cdrdao older than 1.2.3 has a pre-gap length bug.'
                           ' See http://sourceforge.net/tracker/?func=detail&aid=604751&group_id=2171&atid=102171')  # noqa: E501

        t = cdrdao.ReadTOCTask(device, fast_toc=True)
        runner.run(t)
        toc = t.toc.table

        assert toc.hasTOC()
        return toc

    def getTable(self, runner, cddbdiscid, mbdiscid, device, offset,
                 toc_path):
        """
        Retrieve the Table from the drive.

        :rtype: table.Table
        """
        itable = None
        tdict = {}

        t = cdrdao.ReadTOCTask(device, toc_path=toc_path)
        t.description = "Reading table"
        runner.run(t)
        itable = t.toc.table
        tdict[offset] = itable
        logger.debug('getTable: read table %r', itable)

        assert itable.hasTOC()

        self.result.table = itable

        logger.debug('getTable: returning table with mb id %s',
                     itable.getMusicBrainzDiscId())
        return itable

    def getRipResult(self):
        """
        Return a new RipResult.

        :rtype: result.RipResult
        """
        assert self.result is None
        self.result = result.RipResult()
        return self.result

    @staticmethod
    def addDisambiguation(template_part, metadata):
        """Add disambiguation to template path part string."""
        if metadata.catalogNumber:
            template_part += ' (%s)' % metadata.catalogNumber
        elif metadata.barcode:
            template_part += ' (%s)' % metadata.barcode
        return template_part

    def getPath(self, outdir, template, mbdiscid, metadata, track_number=None):
        """
        Return disc or track path relative to outdir according to template.

        Track paths do not include extension.

        Tracks are named according to the track template, filling in
        the variables and adding the file extension. Variables
        exclusive to the track template are:

        * ``%t``: track number
        * ``%a``: track artist
        * ``%n``: track title
        * ``%s``: track sort name

        Disc files (.cue, .log, .m3u) are named according to the disc
        template, filling in the variables and adding the file
        extension. Variables for both disc and track template are:

        * ``%A``: release artist
        * ``%S``: release artist sort name
        * ``%B``: release barcode
        * ``%C``: release catalog number
        * ``%c``: release disambiguation comment
        * ``%d``: release title (with disambiguation)
        * ``%D``: disc title (without disambiguation)
        * ``%I``: MusicBrainz Disc ID
        * ``%M``: total number of discs in the chosen release
        * ``%N``: number of current disc
        * ``%T``: medium title
        * ``%y``: release year
        * ``%r``: release type, lowercase
        * ``%R``: release type, normal case
        * ``%x``: audio extension, lowercase
        * ``%X``: audio extension, uppercase
        """
        assert isinstance(outdir, str), "%r is not str" % outdir
        assert isinstance(template, str), "%r is not str" % template
        v = {}
        v['A'] = 'Unknown Artist'
        v['I'] = v['d'] = v['D'] = mbdiscid  # fallback for title
        v['r'] = 'unknown'
        v['R'] = 'Unknown'
        v['B'] = ''  # barcode
        v['C'] = ''  # catalog number
        v['x'] = 'flac'
        v['X'] = v['x'].upper()
        v['y'] = '0000'
        if track_number is not None:
            v['a'] = v['A']
            v['t'] = '%02d' % track_number
            if track_number == 0:
                v['n'] = 'Hidden Track One Audio'
            else:
                v['n'] = 'Unknown Track %d' % track_number

        if metadata:
            release = metadata.release or '0000'
            v['y'] = release[:4]
            v['A'] = metadata.artist
            v['S'] = metadata.sortName
            v['d'] = metadata.releaseTitle
            v['D'] = metadata.title
            v['B'] = metadata.barcode
            v['C'] = metadata.catalogNumber
            v['c'] = metadata.releaseDisambCmt
            v['M'] = metadata.discTotal
            v['N'] = metadata.discNumber
            v['T'] = metadata.mediumTitle
            if metadata.releaseType:
                v['R'] = metadata.releaseType
                v['r'] = metadata.releaseType.lower()
            if track_number is not None and track_number > 0:
                v['a'] = metadata.tracks[track_number - 1].artist
                v['s'] = metadata.tracks[track_number - 1].sortName
                v['n'] = metadata.tracks[track_number - 1].title
            elif track_number == 0:
                # htoa defaults to disc's artist
                v['a'] = metadata.artist

        template = re.sub(r'%(\w)', r'%(\1)s', template.strip('/'))
        # Avoid filtering non str type values, replace None with empty string
        v_fltr = {k: self._filter.filter(v2) if isinstance(v2, str) else ''
                  if v2 is None else v2 for k, v2 in v.items()}
        if outdir == os.curdir:
            return template % v_fltr  # Avoid useless './' in file paths
        return os.path.join(outdir, template % v_fltr)

    @staticmethod
    def getCDDB(cddbdiscid):
        """
        Fetch basic metadata from gnudb.org's mirror of freedb's CDDB.

        Freedb's official CDDB isn't used anymore because it's going to be
        shut down on 31/03/2020.

        See: https://web.archive.org/web/20200331093822/http://www.freedb.org/
        See: https://hydrogenaud.io/index.php?topic=118682

        :param cddbdiscid: list of id, tracks, offsets, seconds
        :rtype: str
        """
        # FIXME: convert to nonblocking?
        try:
            md = freedb.perform_lookup(
                     cddbdiscid, 'gnudb.gnudb.org', 80
            )
            logger.debug('CDDB query result: %r', md)
            return [item['DTITLE'] for item in md if 'DTITLE' in item] or None

        except ValueError as e:
            logger.warning("CDDB protocol error: %s", e)

        except IOError as e:
            # FIXME: for some reason errno is a str ?
            if e.errno == 'socket error':
                logger.warning("CDDB network error: %r", (e, ))
            else:
                raise

        return None

    def getMusicBrainz(self, ittoc, mbdiscid, release=None, country=None,
                       prompt=False):
        """
        Fetch MusicBrainz's metadata for the given MusicBrainz disc id.

        :param ittoc: disc TOC
        :type ittoc: whipper.image.table.Table
        :param mbdiscid: MusicBrainz DiscID
        :type mbdiscid: str
        :param release: MusicBrainz release id to match to
                        (if there are multiple)
        :type release: str or None
        :param country: country name used to filter releases by provenance
        :type country: str or None
        :param prompt: whether to prompt if there are multiple
                       matching releases
        :type prompt: bool
        """
        # look up disc on MusicBrainz
        print('Disc duration: %s, %d audio tracks' % (
            common.formatTime(ittoc.duration() / 1000.0),
            ittoc.getAudioTracks()))
        logger.debug('MusicBrainz submit url: %r',
                     ittoc.getMusicBrainzSubmitURL())

        metadatas = None

        for _ in range(0, 4):
            try:
                metadatas = mbngs.musicbrainz(mbdiscid,
                                              country=country,
                                              record=self._record)
                break
            except mbngs.NotFoundException as e:
                logger.warning("release not found: %r", (e, ))
                break
            except musicbrainzngs.NetworkError as e:
                logger.warning("network error: %r", (e, ))
                break
            except mbngs.MusicBrainzException as e:
                logger.warning("musicbrainz exception: %r", (e, ))
                time.sleep(5)
                continue

        if not metadatas:
            logger.warning('continuing without metadata')

        if metadatas:
            deltas = {}

            print('\nMatching releases:')

            for metadata in metadatas:
                print('\nArtist  : %s' % metadata.artist)
                print('Title   : %s' % metadata.releaseTitle)
                print('Duration: %s' % common.formatTime(
                                           metadata.duration / 1000.0))
                print('URL     : %s' % metadata.url)
                print('Release : %s' % metadata.mbid)
                print('Type    : %s' % metadata.releaseType)
                if metadata.barcode:
                    print("Barcode : %s" % metadata.barcode)
                if metadata.countries:
                    print("Country : %s" % ', '.join(metadata.countries))
                # TODO: Add test for non ASCII catalog numbers: see issue #215
                if metadata.catalogNumber:
                    print("Cat no  : %s" % metadata.catalogNumber)

                delta = abs(metadata.duration - ittoc.duration())
                if delta not in deltas:
                    deltas[delta] = []
                deltas[delta].append(metadata)

            lowest = None

            if not release and len(metadatas) > 1:
                # Select the release that most closely matches the duration.
                lowest = min(list(deltas))

                if prompt:
                    guess = (deltas[lowest])[0].mbid
                    print("\nPlease select a release. You only need to match "
                          "the last few characters.")
                    release = input(
                        "With no input the release will be [%s]: " %
                        guess).lower()

                    if not release:
                        release = guess

            if release:
                metadatas = [m for m in metadatas if m.url.endswith(release)]
                logger.debug('asked for release %r, only kept %r', release,
                             metadatas)
                if len(metadatas) == 1:
                    logger.info('picked requested release id %s', release)
                    print('Artist: %s' % metadatas[0].artist)
                    print('Title : %s' % metadatas[0].releaseTitle)
                elif not metadatas:
                    logger.warning("requested release id '%s', but none of "
                                   "the found releases match", release)
                    return None
            else:
                if lowest:
                    metadatas = deltas[lowest]

            # If we have multiple, make sure they match
            if len(metadatas) > 1:
                artist = metadatas[0].artist
                discTitle = metadatas[0].title
                for i, metadata in enumerate(metadatas):
                    if not artist == metadata.artist:
                        logger.warning("artist 0: %r and artist %d: %r are "
                                       "not the same", artist, i,
                                       metadata.artist)
                    if not discTitle == metadata.title:
                        logger.warning("title 0: %r and title %d: %r are "
                                       "not the same", discTitle, i,
                                       metadata.title)

                if not release and len(list(deltas)) > 1:
                    logger.warning('picked closest match in duration. '
                                   'Others may be wrong in MusicBrainz, '
                                   'please correct')
                    print('Artist : %s' % artist)
                    print('Title :  %s' % metadatas[0].title)

            # Select one of the returned releases. We just pick the first one.
            ret = metadatas[0]
        else:
            print('Submit this disc to MusicBrainz at the above URL.')
            ret = None

        print('')
        return ret

    def getTagList(self, number, mbdiscid):
        """
        Based on the metadata, get a dict of tags for the given track.

        :param number: track number (0 for HTOA)
        :type number: int
        :param mbdiscid: MusicBrainz DiscID
        :type mbdiscid: str
        :rtype: dict
        """
        trackArtist = 'Unknown Artist'
        releaseArtist = 'Unknown Artist'
        album = 'Unknown Album'
        title = 'Unknown Track'

        if self.metadata:
            trackArtist = self.metadata.artist
            releaseArtist = self.metadata.artist
            album = self.metadata.title  # No disambiguation is proper here
            mbidRelease = self.metadata.mbid
            mbidReleaseGroup = self.metadata.mbidReleaseGroup
            mbidReleaseArtist = self.metadata.mbidArtist

            if number > 0:
                try:
                    track = self.metadata.tracks[number - 1]
                    trackArtist = track.artist
                    title = track.title
                    mbidRecording = track.mbidRecording
                    mbidTrack = track.mbid
                    mbidTrackArtist = track.mbidArtist
                    mbidWorks = track.mbidWorks
                    composers = track.composers
                    performers = track.performers
                except IndexError as e:
                    logger.error('no track %d found, %r', number, e)
                    raise
            else:
                # htoa defaults to disc's artist
                title = 'Hidden Track One Audio'

        tags = {}

        if number > 0:
            tags['MUSICBRAINZ_DISCID'] = mbdiscid

        if self.metadata:
            tags['ALBUMARTIST'] = releaseArtist
        tags['ARTIST'] = trackArtist
        tags['TITLE'] = title
        tags['ALBUM'] = album

        tags['TRACKNUMBER'] = '%s' % number

        if self.metadata:
            if self.metadata.release is not None:
                tags['DATE'] = self.metadata.release
            if self.metadata.tracks:
                tags['TRACKTOTAL'] = str(len(self.metadata.tracks))
            if self.metadata.discTotal is not None:
                tags['DISCTOTAL'] = str(self.metadata.discTotal)
            if self.metadata.discNumber is not None:
                tags['DISCNUMBER'] = str(self.metadata.discNumber)

            if number > 0:
                tags['MUSICBRAINZ_RELEASETRACKID'] = mbidTrack
                tags['MUSICBRAINZ_TRACKID'] = mbidRecording
                tags['MUSICBRAINZ_ARTISTID'] = mbidTrackArtist
                tags['MUSICBRAINZ_ALBUMID'] = mbidRelease
                tags['MUSICBRAINZ_RELEASEGROUPID'] = mbidReleaseGroup
                tags['MUSICBRAINZ_ALBUMARTISTID'] = mbidReleaseArtist
                if len(mbidWorks) > 0:
                    tags['MUSICBRAINZ_WORKID'] = mbidWorks
                if len(composers) > 0:
                    tags['COMPOSER'] = composers
                if len(performers) > 0:
                    tags['PERFORMER'] = performers

        return tags

    def getHTOA(self):
        """
        Check if we have hidden track one audio.

        :returns: tuple of (start, stop), or None
        :rtype: tuple(int, int) or None
        """
        track = self.result.table.tracks[0]
        try:
            index = track.getIndex(0)
        except KeyError:
            return None

        start = index.absolute
        stop = track.getIndex(1).absolute - 1
        return start, stop

    @staticmethod
    def getCoverArt(path, release_id):
        """
        Get cover art image from Cover Art Archive.

        :param path: where to store the fetched image
        :type  path: str
        :param release_id: a release id (self.program.metadata.mbid)
        :type  release_id: str
        :returns: path to the downloaded cover art, else `None`
        :rtype: str or None
        """
        cover_art_path = os.path.join(path, 'cover.jpg')

        logger.debug('fetching cover art for release: %r', release_id)
        try:
            data = musicbrainzngs.get_image_front(release_id, 500)
        except musicbrainzngs.ResponseError as e:
            logger.error('error fetching cover art: %r', e)
            return

        if data:
            with NamedTemporaryFile(suffix='.cover.jpg', delete=False) as f:
                f.write(data)
            os.chmod(f.name, 0o644)
            shutil.move(f.name, cover_art_path)
            logger.debug('cover art fetched at: %r', cover_art_path)
            return cover_art_path
        return

    @staticmethod
    def verifyTrack(runner, trackResult):
        is_wave = not trackResult.filename.endswith('.flac')
        t = checksum.CRC32Task(trackResult.filename, is_wave=is_wave)

        try:
            runner.run(t)
        except task.TaskException as e:
            if isinstance(e.exception, common.MissingFrames):
                logger.warning('missing frames for %r', trackResult.filename)
                return False
            else:
                raise

        ret = trackResult.testcrc == t.checksum
        logger.debug('verifyTrack: track result crc %r, file crc %r, '
                     'result %r', trackResult.testcrc, t.checksum, ret)
        return ret

    def ripTrack(self, runner, trackResult, offset, device, taglist,
                 overread, what=None, coverArtPath=None):
        """
        Rip and store a track of the disc.

        Ripping the track may change the track's filename as stored in
        trackResult.

        :param runner: synchronous track rip task
        :type runner: task.SyncRunner
        :param trackResult: the object to store information in
        :type trackResult: result.TrackResult
        :param offset: ripping offset, in CD frames
        :type offset: int
        :param device: path to the hardware disc drive
        :type device: str
        :param taglist: dictionary of tags for the given track
        :type taglist: dict
        :param overread: whether to force overreading into the
                         lead-out portion of the disc
        :type overread: bool
        :param what: a string representing what's being read; e.g. Track
        :type what: str or None
        :param coverArtPath: path to the downloaded cover art file
        :type coverArtPath: str or None
        """
        if trackResult.number == 0:
            start, stop = self.getHTOA()
        else:
            start = self.result.table.getTrackStart(trackResult.number)
            stop = self.result.table.getTrackEnd(trackResult.number)

        dirname = os.path.dirname(trackResult.filename)
        os.makedirs(dirname, exist_ok=True)

        if not what:
            what = 'track %d' % (trackResult.number, )

        t = cdparanoia.ReadVerifyTrackTask(trackResult.filename,
                                           self.result.table, start,
                                           stop, overread,
                                           offset=offset,
                                           device=device,
                                           taglist=taglist,
                                           what=what,
                                           coverArtPath=coverArtPath)

        runner.run(t)

        logger.debug('ripped track')
        logger.debug('test speed %.3f/%.3f seconds',
                     t.testspeed, t.testduration)
        logger.debug('copy speed %.3f/%.3f seconds',
                     t.copyspeed, t.copyduration)
        trackResult.testcrc = t.testchecksum
        trackResult.copycrc = t.copychecksum
        trackResult.peak = t.peak
        trackResult.quality = t.quality
        trackResult.testspeed = t.testspeed
        trackResult.copyspeed = t.copyspeed
        # we want rerips to add cumulatively to the time
        trackResult.testduration += t.testduration
        trackResult.copyduration += t.copyduration

        if trackResult.filename != t.path:
            trackResult.filename = t.path
            logger.info('filename changed to %r', trackResult.filename)

    def verifyImage(self, runner, table):
        """
        Verify table against AccurateRip and cue_path track lengths.

        Verify our image against the given AccurateRip responses.

        Needs an initialized self.result.
        Will set accurip and friends on each TrackResult.

        Populates self.result.tracks with above TrackResults.
        """
        cueImage = image.Image(self.cuePath)
        # assigns track lengths
        if self.skipped_tracks is not None:
            verifytask = image.ImageVerifyTask(cueImage,
                                               [os.path.basename(t.filename)
                                                for t in self.skipped_tracks])
        else:
            verifytask = image.ImageVerifyTask(cueImage)
        runner.run(verifytask)
        if verifytask.exception:
            logger.error(verifytask.exceptionMessage)
            return False

        responses = accurip.get_db_entry(table.accuraterip_path())
        logger.info('%d AccurateRip response(s) found', len(responses))

        checksums = accurip.calculate_checksums([
            os.path.join(os.path.dirname(self.cuePath), t.indexes[1].path)
            for t in [t for t in cueImage.cue.table.tracks if t.number != 0]
        ])
        if not (checksums and any(checksums['v1']) and any(checksums['v2'])):
            return False

        return accurip.verify_result(self.result, responses, checksums)

    def write_m3u(self, discname):
        m3uPath = common.truncate_filename(discname + '.m3u')
        with open(m3uPath, 'w') as f:
            f.write('#EXTM3U\n')
            for track in self.result.tracks:
                if not track.filename:
                    # false positive htoa
                    continue
                if track.skipped:
                    continue
                if track.number == 0:
                    length = (self.result.table.getTrackStart(1) /
                              common.FRAMES_PER_SECOND)
                else:
                    length = (self.result.table.getTrackLength(track.number) /
                              common.FRAMES_PER_SECOND)

                target_path = common.getRelativePath(track.filename, m3uPath)
                u = '#EXTINF:%d,%s\n' % (length, target_path)
                f.write(u)
                u = '%s\n' % target_path
                f.write(u)

    def writeCue(self, discName):
        assert self.result.table.canCue()
        cuePath = common.truncate_filename(discName + '.cue')
        logger.debug('write .cue file to %s', cuePath)
        handle = open(cuePath, 'w')
        # FIXME: do we always want utf-8 ?
        handle.write(self.result.table.cue(cuePath))
        handle.close()

        self.cuePath = cuePath

        return cuePath

    def writeLog(self, discName, txt_logger):
        logPath = common.truncate_filename(discName + '.log')
        handle = open(logPath, 'w')
        log = txt_logger.log(self.result)
        handle.write(log)
        handle.close()

        self.logPath = logPath

        return logPath
