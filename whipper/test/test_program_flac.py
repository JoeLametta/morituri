# -*- Mode: Python; test-case-name: whipper.test.test_program_flac -*-

import os
import subprocess
from tempfile import NamedTemporaryFile
import wave

from whipper.program import flac
from whipper.test import common

def read_flac(path):
    with NamedTemporaryFile(suffix='.wav') as fp:
        subprocess.check_call(['flac', '--silent', '-d', path, '-fo', fp.name])
        wf = wave.open(fp.name)
        return wf._data_chunk.read()

class FlacTestCase(common.TestCase):
    def setUp(self):
        self.original_path = os.path.join(os.path.dirname(__file__),
                                          'track.flac')

    def testEncode(self):
        with (NamedTemporaryFile(suffix='.wav') as decoded,
              NamedTemporaryFile(suffix='.flac') as encoded_default,
              NamedTemporaryFile(suffix='.flac') as encoded_optimum):
            # Create a wav file
            subprocess.check_call(['flac', '--silent', '-d', self.original_path,
                                   '-fo', decoded.name])

            # Encode it with different extraArgs
            flac.encode(decoded.name, encoded_default.name)
            flac.encode(decoded.name, encoded_optimum.name,
                        ['--best', '-e'])

            # Ensure the file with higher compression is smaller
            size_default = os.path.getsize(encoded_default.name)
            size_optimum = os.path.getsize(encoded_optimum.name)
            self.assertLess(size_optimum, size_default)

            # Make sure the the contents are identical
            data_original = read_flac(self.original_path)
            data_default = read_flac(encoded_default.name)
            data_optimum = read_flac(encoded_optimum.name)
            self.assertEqual(data_original, data_default)
            self.assertEqual(data_original, data_optimum)
