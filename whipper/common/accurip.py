# -*- Mode: Python; test-case-name: whipper.test.test_common_accurip -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (C) 2017 Samantha Baldwin
# Copyright (C) 2009 Thomas Vander Stichele

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

import struct
import whipper
import os
from urllib.error import URLError, HTTPError
from urllib.request import urlopen, Request
from ruamel.yaml.comments import CommentedMap as OrderedDict

from whipper.program.arc import accuraterip_checksum

import logging
logger = logging.getLogger(__name__)


ACCURATERIP_URL = "http://www.accuraterip.com/accuraterip/"


class EntryNotFound(Exception):
    pass


class _AccurateRipResponse:
    """
    An AR resp. contains a collection of metadata identifying a specific disc.

    For disc level metadata it contains the track count, two internal disc
    IDs, and the CDDB disc ID.

    A checksum and a confidence score is stored sequentially for each track in
    the disc index, which excludes any audio hidden in track pre-gaps (such as
    HTOA).

    The response is stored as a packed binary structure.
    """

    def __init__(self, data):
        """
        Init _AccurateRipResponse.

        Checksums and confidences arrays are indexed by relative track
        position, so track 1 will have array index 0, track 2 will have array
        index 1, and so forth. HTOA and other hidden tracks are not included.
        """
        self.num_tracks = data[0]
        self.discId1 = "%08x" % struct.unpack("<L", data[1:5])[0]
        self.discId2 = "%08x" % struct.unpack("<L", data[5:9])[0]
        self.cddbDiscId = "%08x" % struct.unpack("<L", data[9:13])[0]

        self.confidences = []
        self.checksums = []
        pos = 13
        for _ in range(self.num_tracks):
            confidence = data[pos]
            checksum = "%08x" % struct.unpack("<L", data[pos + 1:pos + 5])[0]
            self.confidences.append(confidence)
            self.checksums.append(checksum)
            pos += 9

    def __eq__(self, other):
        return [
            self.num_tracks, self.discId1, self.discId2, self.cddbDiscId,
            self.confidences, self.checksums
        ] == [
            other.num_tracks, other.discId1, other.discId2, other.cddbDiscId,
            other.confidences, other.checksums
        ]


def _split_responses(raw_entry):
    responses = []
    while raw_entry:
        track_count = raw_entry[0]
        nbytes = 1 + 12 + track_count * (1 + 8)
        responses.append(_AccurateRipResponse(raw_entry[:nbytes]))
        raw_entry = raw_entry[nbytes:]
    return responses


def calculate_checksums(track_paths):
    """
    Calculate AccurateRip checksums for the given tracks.

    HTOA checksums are not included in the database and are not calculated.

    :returns: ARv1 and ARv2 checksums as two arrays of character strings in a
              dictionary: ``{'v1': ['deadbeef', ...], 'v2': [...]}``
              or None instead of checksum string for unchecksummable tracks.
    :rtype: dict(string, list()) or None
    """
    track_count = len(track_paths)
    v1_checksums = []
    v2_checksums = []
    logger.debug('checksumming %d tracks', track_count)
    # This is done sequentially because it is very fast.
    for i, path in enumerate(track_paths):
        if os.path.exists(path):
            v1_sum, v2_sum = accuraterip_checksum(path, i+1, track_count)
        else:
            logger.warning('Can\'t checksum %s; path doesn\'t exist', path)
            v1_sum, v2_sum = None, None
        if v1_sum is None:
            logger.error('could not calculate AccurateRip v1 checksum '
                         'for track %d %r', i + 1, path)
            v1_checksums.append(None)
        else:
            v1_checksums.append("%08x" % v1_sum)
        if v2_sum is None:
            logger.error('could not calculate AccurateRip v2 checksum '
                         'for track %d %r', i + 1, path)
            v2_checksums.append(None)
        else:
            v2_checksums.append("%08x" % v2_sum)
    return {'v1': v1_checksums, 'v2': v2_checksums}


def _download_entry(path):
    url = ACCURATERIP_URL + path
    UA = "whipper/%s ( https://github.com/whipper-team/whipper )" % whipper.__version__  # noqa: E501
    logger.debug('downloading AccurateRip entry from %s', url)
    try:
        with urlopen(Request(url, headers={'User-Agent': UA})) as resp:
            return resp.read()
    except (URLError, HTTPError) as e:
        logger.error('error retrieving AccurateRip entry: %s', e)


def get_db_entry(path):
    """
    Download entry from accuraterip.com.

    ``path`` is in the format of the output of ``table.accuraterip_path()``.
    """
    raw_entry = _download_entry(path)
    if not raw_entry:
        logger.warning('entry not found in AccurateRip database')
        raise EntryNotFound
    return _split_responses(raw_entry)


def _assign_checksums_and_confidences(tracks, checksums, responses):
    for i, track in enumerate(tracks):
        for v in ('v1', 'v2'):
            track.AR[v]['CRC'] = checksums[v][i]
        track.AR['DBMaxConfidence'], track.AR['DBMaxConfidenceCRC'] = max(
            [(r.confidences[i], r.checksums[i]) for r in responses],
            key=lambda t: t[0]
        )


def _match_responses(tracks, responses):
    """
    Match and save track AR response checksums against all non-hidden tracks.

    :returns: True if every track has a match for every entry for either
              AccurateRip version, False otherwise.
    :rtype: bool
    """
    for r in responses:
        for i, track in enumerate(tracks):
            for v in ('v1', 'v2'):
                if track.AR[v]['CRC'] == r.checksums[i]:
                    if (track.AR[v]['DBConfidence'] is None or
                            r.confidences[i] > track.AR[v]['DBConfidence']):
                        track.AR[v]['DBCRC'] = r.checksums[i]
                        track.AR[v]['DBConfidence'] = r.confidences[i]
                        logger.debug(
                            'track %d matched response %s in AccurateRip'
                            ' database: %s crc %s confidence %s',
                            i, r.cddbDiscId, v, track.AR[v]['DBCRC'],
                            track.AR[v]['DBConfidence'])
    return any((
        all([t.AR['v1']['DBCRC'] for t in tracks]),
        all([t.AR['v2']['DBCRC'] for t in tracks])
    ))


def verify_result(result, responses, checksums):
    """
    Verify track AccurateRip checksums against database responses.

    Store track checksums and database values on result.
    """
    if not (result and responses and checksums):
        return False
    # exclude HTOA from AccurateRip verification
    # NOTE: if pre-gap hidden audio support is expanded to include
    # tracks other than HTOA, this is invalid.
    tracks = [t for t in result.tracks if t.number != 0]
    if not tracks:
        return False
    _assign_checksums_and_confidences(tracks, checksums, responses)
    return _match_responses(tracks, responses)


def log_notfound_crcs(result):
    """Generate log messages for any failed tracks"""
    for _, track in enumerate(result.tracks):
        if track.number == 0:
            continue
        if not (track.AR['v1']['CRC'] or track.AR['v2']['CRC']):
            logger.error('no track AR CRC on non-HTOA track %d', track.number)


def generate_report(result):
    """Print AccurateRip verification results."""
    report = OrderedDict()
    for _, track in enumerate(result.tracks):
        status = 'rip NOT accurate'
        conf = '(not found)'
        db = 'notfound'
        if track.AR['DBMaxConfidence'] is not None:
            db = track.AR['DBMaxConfidenceCRC']
            conf = '(max confidence    %3d)' % track.AR['DBMaxConfidence']
            if track.AR['v1']['DBCRC'] or track.AR['v2']['DBCRC']:
                status = 'rip accurate'
                db = ', '.join([_f for _f in (
                    track.AR['v1']['DBCRC'],
                    track.AR['v2']['DBCRC']
                ) if _f])
            max_conf = max(
                [track.AR[v]['DBConfidence'] for v in ('v1', 'v2')
                 if track.AR[v]['DBConfidence'] is not None], default=None
            )
            if max_conf:
                if max_conf < track.AR['DBMaxConfidence']:
                    conf = '(confidence %3d of %3d)' % (
                        max_conf, track.AR['DBMaxConfidence']
                    )
        # htoa tracks (i == 0) do not have an ARCRC
        if track.number == 0:
            report['Track  0'] = 'unknown          (not tracked)'
            continue
        if not (track.AR['v1']['CRC'] or track.AR['v2']['CRC']):
            report['Track %2d' % track.number] = 'unknown          (error)'
        else:
            report['Track %2d' % track.number] = '%-16s %-23s v1 [%s], v2 [%s], DB [%s]' % (
                status, conf, track.AR['v1']['CRC'], track.AR['v2']['CRC'], db
            )
    return report


def print_report(result):
    """Generate and print AccurateRip verification results summary."""
    report = generate_report(result)
    for key, item in report.items():
        print('%s: %s' % (key.lower(), item))
