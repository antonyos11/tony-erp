from django.test import TestCase

from core.sequence_utils import Sequence, next_sequence, format_code


class SequenceUtilsTests(TestCase):
    def test_next_sequence_starts_and_increments(self):
        first = next_sequence('UNITTEST', initial=5)
        self.assertEqual(first, 5)
        second = next_sequence('UNITTEST')
        self.assertEqual(second, 6)
        seq = Sequence.objects.get(name='UNITTEST')
        self.assertEqual(seq.value, 6)

    def test_format_code_zero_pads(self):
        code = format_code('INV', 42, width=4)
        self.assertEqual(code, 'INV-0042')
