# python -m unittest discover -s tests -t .
import re
import unittest

from src.events import _title_has, filter_events_kw


def old_rule(summary, kw):
	title = re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9]", " ", summary)).strip().lower()
	return bool(kw.strip()) and re.search(r"\b" + re.escape(kw.lower()) + r"\b", title) is not None


class TitleHas(unittest.TestCase):
	def test_word_after_lone_digit(self):
		self.assertTrue(_title_has("CLASSI 4 e 5 - ORIENTAMENTO", "4"))
		self.assertTrue(_title_has("RAPPRESENTANTI DI CLASSE 4 LICEO E 4 IT - AULA MAGNA", "LICEO"))
		self.assertTrue(_title_has("CLASSE 3 CIIN - AULA 94", "3CIIN"))
		self.assertFalse(_title_has("CLASSE 5CIIN - AULA 94", "4"))
		self.assertFalse(_title_has("CLASSE 5CIIN - AULA 94", " "))

	def test_never_fewer_than_old_notifier(self):
		titles = [
			"CLASSI 4 e 5 - ORIENTAMENTO",
			"RAPPRESENTANTI DI CLASSE 4 LICEO E 4 IT - AULA MAGNA",
			"CLASSE 3 CIIN - AULA 94 - PROF.SSA DEL MODELLO",
			"CLASSE 5ºCIIN - USCITA ANTICIPATA ORE 12",
			"CLASSE 1AIIN - (PROF. PIPPÒ: ASSENTE) - AULA 94",
			"CLASSE 2A - ATTIVITA' 2 ORE - AULA 1-3 DEBATE",
		]
		kws = ["4", "5", "LICEO", "IT", "E", "CIIN", "3 CIIN", "5CIIN", "ORE", "2 ORE", "MODELLO", "AULA 94", "1AIIN", "DEBATE", "1", "3"]
		for s in titles:
			for kw in kws:
				if old_rule(s, kw):
					self.assertTrue(_title_has(s, kw), f"{kw} | {s}")


class FilterOptIn(unittest.TestCase):
	events = [{"uid": u, "summary": s} for u, s in [
		("a", "CLASSE 5CIIN - AULA 94"),
		("b", "SPORTELLO MATEMATICA - CLASSE 5CIIN"),
		("c", "CLASSI QUINTE - ASSEMBLEA"),
		("d", "SPORTELLO FISICA - CLASSI 5^ IT"),
	]]
	matches = {"matches": {"5CIIN": {"a"}}, "optional": {"5CIIN": {"sportelli": {"b"}, "gruppo": {"c"}, "sportelli+gruppo": {"d"}}}}

	def uids(self, optin):
		return sorted(e["uid"] for e in filter_events_kw(self.events, ["5CIIN"], self.matches, optin))

	def test_categories(self):
		self.assertEqual(self.uids([]), ["a"])
		self.assertEqual(self.uids(["sportelli"]), ["a", "b"])
		self.assertEqual(self.uids(["gruppo"]), ["a", "c"])
		self.assertEqual(self.uids(["sportelli", "gruppo"]), ["a", "b", "c", "d"])


if __name__ == "__main__":
	unittest.main()
