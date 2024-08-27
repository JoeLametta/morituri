from whipper.image.toc import _CDTEXT_CANDIDATE_RE, parse_toc_string

from whipper.test import common

class TestTOCStringParsing(common.TestCase):
    def check_string(self, str_with_quotes: str, str_parsed_expected: str):
        text = f"PERFORMER {str_with_quotes}"
        match = _CDTEXT_CANDIDATE_RE.match(text)
        if not match:
            self.fail(f"String wasn't matched: {text}")
        self.assertEquals(match.start(), 0)
        self.assertEquals(match.end(), len(text))

        str_parsed_actual = parse_toc_string(match.group("value"))
        self.assertEquals(str_parsed_actual, str_parsed_expected)

    def test_simple(self):
        self.check_string('"foo bar"', 'foo bar')

    def test_escaped_quotes(self):
        self.check_string(r'"the \"foos\""', r'the "foos"')

    def test_escaped_backslash(self):
        self.check_string(r'"foo\\bar"', r'foo\bar')

    def test_escaped_latin1(self):
        self.check_string(r'"M\330L"', r'MØL')

    def test_incomplete_escape(self):
        self.check_string(r'"M\33a"', r'M\33a')

    def test_trailing_backslash(self):
        self.check_string(r'"foo\\"', 'foo\\')

    def test_unicode(self):
        self.check_string(r'"MØL"', 'MØL')