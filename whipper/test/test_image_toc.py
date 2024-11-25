# -*- Mode: Python; test-case-name: whipper.test.test_image_toc -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import copy
import shutil
import tempfile
from abc import abstractmethod

from whipper.image import toc

from whipper.test import common


class CureTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'cure.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 13)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        # its length is all of track 1 from .toc, plus the INDEX 00 length
        # of track 2
        self.assertEqual(self.toc.getTrackLength(t),
                         (((6 * 60) + 16) * 75 + 45) + ((1 * 75) + 4))
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEqual(self.toc.getTrackLength(t), -1)

    def testIndexes(self):
        # track 2, index 0 is at 06:16:45 or 28245
        # track 2, index 1 is at 06:17:49 or 28324
        # FIXME: cdrdao seems to get length of FILE 1 frame too many,
        # and START value one frame less
        t = self.toc.table.tracks[1]
        self.assertEqual(t.getIndex(0).relative, 28245)
        self.assertEqual(t.getIndex(1).relative, 28324)

    def _getIndex(self, t, i):
        track = self.toc.table.tracks[t - 1]
        return track.getIndex(i)

    def _assertAbsolute(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEqual(index.absolute, value)

    def _assertPath(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEqual(index.path, value)

    def _assertRelative(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEqual(index.relative, value)

    def testSetFile(self):
        self._assertAbsolute(1, 1, 0)
        self._assertAbsolute(2, 0, 28245)
        self._assertAbsolute(2, 1, 28324)
        self._assertPath(1, 1, "data.wav")

        self.toc.table.clearFiles()

        self._assertAbsolute(1, 1, 0)
        self._assertAbsolute(2, 0, 28245)
        self._assertAbsolute(2, 1, 28324)
        self._assertAbsolute(3, 1, 46110)
        self._assertAbsolute(4, 1, 66767)
        self._assertPath(1, 1, None)
        self._assertRelative(1, 1, None)

        # adding the first track file with length 28324 to the table should
        # relativize from absolute 0 to absolute 28323, right before track 2,
        # index 1
        self.toc.table.setFile(1, 1, 'track01.wav', 28324)
        self._assertPath(1, 1, 'track01.wav')
        self._assertRelative(1, 1, 0)
        self._assertPath(2, 0, 'track01.wav')
        self._assertRelative(2, 0, 28245)

        self._assertPath(2, 1, None)
        self._assertRelative(2, 1, None)

    def testConvertCue(self):
        cue = self.toc.table.cue()
        ref = self.readCue('cure.cue')
        common.diffStrings(ref, cue)

        # we verify it because it has failed in readdisc in the past
        self.assertEqual(self.toc.table.accuraterip_path(),
                         '3/c/4/dBAR-013-0019d4c3-00fe8924-b90c650d.bin')

    def testGetRealPath(self):
        self.assertRaises(KeyError, self.toc.getRealPath, 'track01.wav')
        (fd, path) = tempfile.mkstemp(suffix='.whipper.test.wav')
        self.assertEqual(self.toc.getRealPath(path), path)

        winpath = path.replace('/', '\\')
        self.assertEqual(self.toc.getRealPath(winpath), path)
        os.close(fd)
        os.unlink(path)

# Bloc Party - Silent Alarm has a Hidden Track One Audio


class BlocTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'bloc.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 13)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        # the length is from Track 1, Index 1 to Track 2, Index 1, so
        # does not include the htoa
        self.assertEqual(self.toc.getTrackLength(t), 19649)
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEqual(self.toc.getTrackLength(t), -1)

    def testIndexes(self):
        track01 = self.toc.table.tracks[0]
        index00 = track01.getIndex(0)
        self.assertEqual(index00.absolute, 0)
        self.assertEqual(index00.relative, 0)
        self.assertEqual(index00.counter, 0)

        index01 = track01.getIndex(1)
        self.assertEqual(index01.absolute, 15220)
        self.assertEqual(index01.relative, 0)
        self.assertEqual(index01.counter, 1)

        track05 = self.toc.table.tracks[4]

        index00 = track05.getIndex(0)
        self.assertEqual(index00.absolute, 84070)
        self.assertEqual(index00.relative, 68850)
        self.assertEqual(index00.counter, 1)

        index01 = track05.getIndex(1)
        self.assertEqual(index01.absolute, 84142)
        self.assertEqual(index01.relative, 68922)
        self.assertEqual(index01.counter, 1)

    # This disc has a pre-gap, so is a good test for .CUE writing

    def testConvertCue(self):
        self.assertTrue(self.toc.table.hasTOC())
        cue = self.toc.table.cue()
        ref = self.readCue('bloc.cue')
        common.diffStrings(ref, cue)

    def testCDDBId(self):
        # cd-discid output:
        # ad0be00d 13 15370 35019 51532 69190 84292 96826 112527 132448
        # 148595 168072 185539 203331 222103 3244

        self.assertEqual(self.toc.table.getCDDBDiscId(), 'ad0be00d')

    def testAccurateRip(self):
        # we verify it because it has failed in readdisc in the past
        self.assertEqual(self.toc.table.accuraterip_path(),
                         'e/d/2/dBAR-013-001af2de-0105994e-ad0be00d.bin')

# The Breeders - Mountain Battles has CDText


class BreedersTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'breeders.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 13)

    def testCDText(self):
        cdt = self.toc.table.cdtext
        self.assertEqual(cdt['PERFORMER'], 'THE BREEDERS')
        self.assertEqual(cdt['TITLE'], 'MOUNTAIN BATTLES')

        t = self.toc.table.tracks[0]
        cdt = t.cdtext
        self.assertRaises(AttributeError, getattr, cdt, 'PERFORMER')
        self.assertEqual(cdt['TITLE'], 'OVERGLAZED')

    def testConvertCue(self):
        self.assertTrue(self.toc.table.hasTOC())
        cue = self.toc.table.cue()
        ref = self.readCue('breeders.cue')
        self.assertEqual(cue, ref)


class DioramaTOCMixin:
    # TODO figure out how to make this class abstract
    """
    MØL - Diorama contains CD-Text.

    Two .toc files are provided:
     - diorama_utf8.toc (UTF-8 mode, cdrdao 1.2.5)
     - diorama_noutf8.toc (--no-utf8 mode, cdrdao 1.2.5, but representative of
       any older version of cdrdao)

    Regardless of the version chosen for the toc file, all the same tests should
    pass, including generating the same .cue file as output.
    """

    @property
    @abstractmethod
    def tocFileName(self) -> str:
        raise NotImplementedError

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), self.tocFileName)
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 8)

    def testCDText(self):
        cdt = self.toc.table.cdtext
        self.assertEqual(cdt['PERFORMER'], 'MØL')
        self.assertEqual(cdt['TITLE'], 'Diorama')

        t = self.toc.table.tracks[0]
        cdt = t.cdtext
        self.assertEqual(cdt['PERFORMER'], 'MØL')
        self.assertEqual(cdt['TITLE'], 'Fraktur')

    def testConvertCue(self):
        self.assertTrue(self.toc.table.hasTOC())
        cue = self.toc.table.cue()
        with open("/tmp/miau.txt", "w") as f:
            f.write(cue)
        ref = self.readCue('diorama.cue')
        self.maxDiff = None
        self.assertEqual(cue, ref)


class CDTextLatin1TOCTestCase(common.TestCase, common.UnicodeTestMixin,
                              DioramaTOCMixin):
    @property
    def tocFileName(self) -> str:
        return 'diorama_noutf8.toc'

    def setUp(self):
        DioramaTOCMixin.setUp(self)


class CDTextUTF8TOCTestCase(common.TestCase, common.UnicodeTestMixin,
                            DioramaTOCMixin):
    @property
    def tocFileName(self) -> str:
        return 'diorama_utf8.toc'

    def setUp(self):
        DioramaTOCMixin.setUp(self)


# Ladyhawke has a data track


class LadyhawkeTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'ladyhawke.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 13)
        self.assertFalse(self.toc.table.tracks[-1].audio)

    def testCDDBId(self):
        self.assertEqual(self.toc.table.getCDDBDiscId(), 'c60af50d')
        # output from cd-discid:
        # c60af50d 13 150 15687 31841 51016 66616 81352 99559 116070 133243
        # 149997 161710 177832 207256 2807

    def testMusicBrainz(self):
        self.assertEqual(self.toc.table.getMusicBrainzDiscId(),
                         "KnpGsLhvH.lPrNc1PBL21lb9Bg4-")
        self.assertEqual(self.toc.table.getMusicBrainzSubmitURL(),
                         "https://musicbrainz.org/cdtoc/attach?toc=1+12+195856+150+15687+31841+51016+66616+81352+99559+116070+133243+149997+161710+177832&tracks=12&id=KnpGsLhvH.lPrNc1PBL21lb9Bg4-")  # noqa: E501

    # FIXME: I don't trust this toc, but I can't find the CD anymore

    def testDuration(self):
        self.assertEqual(self.toc.table.duration(), 2761413)

    def testGetFrameLength(self):
        self.assertEqual(self.toc.table.getFrameLength(data=True), 210385)

    def testCue(self):
        self.assertTrue(self.toc.table.canCue())
        data = self.toc.table.cue()
        lines = data.split("\n")
        self.assertEqual(lines[0], "REM DISCID C60AF50D")


class CapitalMergeTestCase(common.TestCase):

    def setUp(self):
        self.toc1 = toc.TocFile(os.path.join(os.path.dirname(__file__),
                                             'capital.1.toc'))
        self.toc1.parse()
        self.assertEqual(len(self.toc1.table.tracks), 11)
        self.assertTrue(self.toc1.table.tracks[-1].audio)

        self.toc2 = toc.TocFile(os.path.join(os.path.dirname(__file__),
                                             'capital.2.toc'))
        self.toc2.parse()
        self.assertEqual(len(self.toc2.table.tracks), 1)
        self.assertFalse(self.toc2.table.tracks[-1].audio)

        self.table = copy.deepcopy(self.toc1.table)
        self.table.merge(self.toc2.table)

    def testCDDBId(self):
        self.assertEqual(self.table.getCDDBDiscId(), 'b910140c')
        # output from cd-discid:
        # b910140c 12 24320 44855 64090 77885 88095 104020 118245 129255 141765
        # 164487 181780 209250 4440

    def testMusicBrainz(self):
        # URL to submit: https://musicbrainz.org/cdtoc/attach?toc=1+11+
        # 197850+24320+44855+64090+77885+88095+104020+118245+129255+141765+
        # 164487+181780&tracks=11&id=MAj3xXf6QMy7G.BIFOyHyq4MySE-
        self.assertEqual(self.table.getMusicBrainzDiscId(),
                         "MAj3xXf6QMy7G.BIFOyHyq4MySE-")

    def testDuration(self):
        # this matches track 11 end sector - track 1 start sector on
        # MusicBrainz
        # compare to 3rd and 4th value in URL above
        self.assertEqual(self.table.getFrameLength(), 173530)
        self.assertEqual(self.table.duration(), 2313733)

    def testMusicBrainzDataTrackFirst(self):
        self.table = copy.deepcopy(self.toc2.table)
        self.table.merge(self.toc1.table)
        print(self.table.tracks)
        self.assertEqual(self.table.getMusicBrainzDiscId(),
                         "QTYYFFAgNK4Np2EHjfPTBavqtw8-")


class UnicodeTestCase(common.TestCase, common.UnicodeTestMixin):

    def setUp(self):
        # we copy the normal non-utf8 filename to a utf-8 filename
        # in this test because builds with LANG=C fail if we include
        # utf-8 filenames in the dist
        path = 'Jos\xe9Gonz\xe1lez.toc'
        self._performer = 'Jos\xe9 Gonz\xe1lez'
        source = os.path.join(os.path.dirname(__file__), 'jose.toc')
        (fd, self.dest) = tempfile.mkstemp(suffix=path)
        os.close(fd)
        shutil.copy(source, self.dest)
        self.toc = toc.TocFile(self.dest)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 10)

    def tearDown(self):
        os.unlink(self.dest)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        self.assertEqual(self.toc.getTrackLength(t), 12001)
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEqual(self.toc.getTrackLength(t), -1)

    def testGetTrackPerformer(self):
        t = self.toc.table.tracks[0]
        self.assertEqual(t.cdtext['PERFORMER'], self._performer)


# Interpol - Turn of the Bright Lights has same cddb disc id as
# Afghan Whigs - Gentlemen


class TOTBLTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'totbl.fast.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 11)

    def testCDDBId(self):
        self.assertEqual(self.toc.table.getCDDBDiscId(), '810b7b0b')


class GentlemenTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
                                 'gentlemen.fast.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 11)

    def testCDDBId(self):
        self.toc.table.absolutize()
        self.assertEquals(self.toc.table.getCDDBDiscId(), '810b7b0b')


# The Strokes - Someday has a 1 frame SILENCE marked as such in toc


class StrokesTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
                                 'strokes-someday.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 1)

    def testIndexes(self):
        t = self.toc.table.tracks[0]
        i0 = t.getIndex(0)
        self.assertEqual(i0.relative, 0)
        self.assertEqual(i0.absolute, 0)
        self.assertEqual(i0.counter, 0)
        self.assertEqual(i0.path, None)

        i1 = t.getIndex(1)
        self.assertEqual(i1.relative, 0)
        self.assertEqual(i1.absolute, 1)
        self.assertEqual(i1.counter, 1)
        self.assertEqual(i1.path, 'data.wav')

        cue = self._filterCue(self.toc.table.cue())
        with open(os.path.join(os.path.dirname(__file__),
                               'strokes-someday.eac.cue')) as f:
            ref = self._filterCue(f.read())
        common.diffStrings(ref, cue)

    @staticmethod
    def _filterCue(output):
        # helper to be able to compare our generated .cue with the
        # EAC-extracted one
        discard = ['TITLE', 'PERFORMER', 'FLAGS', 'REM']
        lines = output.split('\n')

        res = []

        for line in lines:
            found = False
            for needle in discard:
                if line.find(needle) > -1:
                    found = True

            if line.find('FILE') > -1:
                line = 'FILE "data.wav" WAVE'

            if not found:
                res.append(line)

        return '\n'.join(res)


# Surfer Rosa has
# track 00 consisting of 32 frames of SILENCE
# track 11 Vamos with an INDEX 02
# compared to an EAC single .cue file, all our offsets are 32 frames off
# because the toc uses silence for track 01 index 00 while EAC puts it in
# Range.wav
class SurferRosaTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), 'surferrosa.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEqual(len(self.toc.table.tracks), 21)

    def testIndexes(self):
        # HTOA
        t = self.toc.table.tracks[0]
        self.assertEqual(len(t.indexes), 2)

        i0 = t.getIndex(0)
        self.assertEqual(i0.relative, 0)
        self.assertEqual(i0.absolute, 0)
        self.assertEqual(i0.path, None)
        self.assertEqual(i0.counter, 0)

        i1 = t.getIndex(1)
        self.assertEqual(i1.relative, 0)
        self.assertEqual(i1.absolute, 32)
        self.assertEqual(i1.path, 'data.wav')
        self.assertEqual(i1.counter, 1)

        # track 11, Vamos

        t = self.toc.table.tracks[10]
        self.assertEqual(len(t.indexes), 2)

        # 32 frames of silence, and 1483 seconds of data.wav
        self.assertEqual(t.getIndex(1).relative, 111225)
        self.assertEqual(t.getIndex(1).absolute, 111257)
        self.assertEqual(t.getIndex(2).relative, 111225 + 3370)
        self.assertEqual(t.getIndex(2).absolute, 111257 + 3370)
