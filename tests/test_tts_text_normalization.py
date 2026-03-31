"""Tests for _normalize_text_for_tts() in app_utils/eas.py.

Covers the NWS-specific normalizations added to handle county-disambiguation
state codes (MI, OH), facility abbreviations (AFD), the "ST." saint
abbreviation, and the slash-enclosed alternate-timezone notation used by
NOAA/NWS watches (e.g. "/5 PM CDT/").
"""
import re
import sys
import unittest
from unittest.mock import patch


def _get_normalize():
    """Import _normalize_text_for_tts with the DB layer stubbed out."""
    with patch('app_utils.eas._load_pronunciation_rules', return_value=[]):
        from app_utils.eas import _normalize_text_for_tts
    return _normalize_text_for_tts


class TestSlashAlternateTimezone(unittest.TestCase):
    """NWS alternate-timezone slash notation: /5 PM CDT/ → 5 PM CDT."""

    def setUp(self):
        self.normalize = _get_normalize()

    def test_slash_notation_stripped(self):
        result = self.normalize('UNTIL 6 PM EDT /5 PM CDT/ THIS EVENING')
        self.assertNotIn('/5 PM CDT/', result)
        self.assertNotIn('/5 PM', result)

    def test_cdt_expanded_after_slash_strip(self):
        result = self.normalize('UNTIL 6 PM EDT /5 PM CDT/ THIS EVENING')
        self.assertIn('Central Daylight Time', result)

    def test_edt_expanded(self):
        result = self.normalize('UNTIL 6 PM EDT /5 PM CDT/ THIS EVENING')
        self.assertIn('Eastern Daylight Time', result)

    def test_slash_notation_with_colon_time(self):
        result = self.normalize('UNTIL 6:00 PM EDT /5:00 PM CDT/ THIS EVENING')
        self.assertNotIn('/5:00 PM CDT/', result)
        self.assertIn('Central Daylight Time', result)

    def test_slash_notation_with_est(self):
        result = self.normalize('UNTIL 11 PM EST /10 PM CST/')
        self.assertNotIn('/10 PM CST/', result)
        self.assertIn('Central Standard Time', result)


class TestSaintAbbreviation(unittest.TestCase):
    """ST. → Saint before proper nouns."""

    def setUp(self):
        self.normalize = _get_normalize()

    def test_st_joseph_expanded(self):
        result = self.normalize('KOSCIUSKO ST. JOSEPH IN NORTHERN INDIANA')
        self.assertNotIn('ST. JOSEPH', result)
        self.assertIn('Saint JOSEPH', result)

    def test_st_joseph_michigan(self):
        result = self.normalize('CASS MI HILLSDALE ST. JOSEPH MI')
        self.assertNotIn('ST. JOSEPH', result)
        self.assertIn('Saint JOSEPH', result)

    def test_st_louis(self):
        result = self.normalize('CITIES OF ST. LOUIS AND CHICAGO')
        self.assertNotIn('ST. LOUIS', result)
        self.assertIn('Saint LOUIS', result)

    def test_lowercase_st_expanded(self):
        result = self.normalize('st. Joseph county')
        self.assertNotIn('st. Joseph', result)
        self.assertIn('Saint Joseph', result)


class TestStateCodeExpansion(unittest.TestCase):
    """MI → Michigan, OH → Ohio state disambiguation codes."""

    def setUp(self):
        self.normalize = _get_normalize()

    def test_mi_expanded(self):
        result = self.normalize('BERRIEN BRANCH CASS MI HILLSDALE')
        self.assertIn('CASS Michigan', result)

    def test_oh_expanded(self):
        result = self.normalize('ALLEN OH DEFIANCE FULTON OH HENRY')
        self.assertIn('ALLEN Ohio', result)
        self.assertIn('FULTON Ohio', result)

    def test_miami_not_broken(self):
        """MI word-boundary match must not corrupt MIAMI."""
        result = self.normalize('MIAMI NOBLE PULASKI')
        self.assertIn('MIAMI', result)

    def test_ohio_word_not_double_expanded(self):
        """The spelled-out word OHIO must not be changed."""
        result = self.normalize('IN OHIO THIS WATCH INCLUDES 8 COUNTIES IN NORTHWEST OHIO')
        self.assertIn('IN OHIO', result)

    def test_michigan_word_not_double_expanded(self):
        """The spelled-out word MICHIGAN must not be changed."""
        result = self.normalize('IN MICHIGAN THIS WATCH INCLUDES 5 COUNTIES')
        self.assertIn('IN MICHIGAN', result)

    def test_in_preposition_untouched(self):
        """IN as a common English preposition must be left alone."""
        result = self.normalize('IN EFFECT IN INDIANA IN NORTH CENTRAL INDIANA')
        self.assertIn('IN EFFECT', result)
        self.assertIn('IN INDIANA', result)


class TestAFDExpansion(unittest.TestCase):
    """AFD → Air Force Depot."""

    def setUp(self):
        self.normalize = _get_normalize()

    def test_afd_expanded(self):
        result = self.normalize('CITIES OF GRISSOM AFD, AKRON')
        self.assertNotIn('GRISSOM AFD', result)
        self.assertIn('GRISSOM Air Force Depot', result)

    def test_afd_standalone(self):
        result = self.normalize('AFD')
        self.assertEqual(result, 'Air Force Depot')


class TestFullWatchText(unittest.TestCase):
    """End-to-end test using excerpt from a real NWS watch description."""

    def setUp(self):
        self.normalize = _get_normalize()

    def test_full_watch_excerpt(self):
        text = (
            'THE NATIONAL WEATHER SERVICE HAS ISSUED SEVERE THUNDERSTORM WATCH 78 '
            'IN EFFECT UNTIL 6 PM EDT /5 PM CDT/ THIS EVENING FOR THE FOLLOWING AREAS '
            'IN INDIANA THIS WATCH INCLUDES 24 COUNTIES IN NORTH CENTRAL INDIANA '
            'KOSCIUSKO ST. JOSEPH IN NORTHERN INDIANA ADAMS ALLEN IN BLACKFORD CASS IN '
            'DE KALB ELKHART FULTON IN GRANT HUNTINGTON JAY LA PORTE LAGRANGE MARSHALL '
            'MIAMI NOBLE PULASKI STARKE STEUBEN WABASH WELLS WHITE WHITLEY '
            'IN MICHIGAN THIS WATCH INCLUDES 5 COUNTIES IN SOUTHWEST MICHIGAN '
            'BERRIEN BRANCH CASS MI HILLSDALE ST. JOSEPH MI '
            'IN OHIO THIS WATCH INCLUDES 8 COUNTIES IN NORTHWEST OHIO '
            'ALLEN OH DEFIANCE FULTON OH HENRY PAULDING PUTNAM VAN WERT WILLIAMS '
            'THIS INCLUDES THE CITIES OF GRISSOM AFD, AKRON, MIAMI'
        )
        result = self.normalize(text)

        # Timezone
        self.assertIn('Eastern Daylight Time', result)
        self.assertIn('Central Daylight Time', result)
        self.assertNotIn('/5 PM CDT/', result)

        # Saint abbreviation
        self.assertNotIn('ST. JOSEPH', result)
        self.assertIn('Saint JOSEPH', result)

        # State codes
        self.assertIn('CASS Michigan', result)
        self.assertIn('ALLEN Ohio', result)
        self.assertIn('FULTON Ohio', result)

        # Facility
        self.assertIn('Air Force Depot', result)

        # Untouched words
        self.assertIn('MIAMI', result)       # not broken by MI→Michigan
        self.assertIn('IN EFFECT', result)   # preposition intact
        self.assertIn('IN INDIANA', result)  # preposition intact
        self.assertIn('IN MICHIGAN', result) # preposition intact
        self.assertIn('IN OHIO', result)     # preposition intact


if __name__ == '__main__':
    unittest.main()
