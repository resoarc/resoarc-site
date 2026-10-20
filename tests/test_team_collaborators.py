"""Guard the public collaborator profile without exposing personal or employer identity."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'site/project/index.html'
CSS=ROOT/'site/assets/team-collaborators.css'
class TeamCollaboratorTests(unittest.TestCase):
    def test_team_frame_exists_exactly_once(self):
        s=PAGE.read_text('utf8')
        self.assertEqual(s.count('※その他協力関係にある構成員'),1)
        self.assertIn('id="team-collaborators-heading"',s)
        self.assertIn('class="team-collaborators" aria-labelledby="team-collaborators-heading"',s)
    def test_known_roles_preserved(self):
        s=PAGE.read_text('utf8')
        for name in ['Aster','Nox','Pax','Iris']:
            self.assertIn('<dt>'+name+'</dt>',s)
    def test_public_facing_role_and_limits(self):
        s=PAGE.read_text('utf8')
        self.assertIn('運営、構築、技術、広報、対外連絡協力',s)
        self.assertIn('Operations / Development / Technology / PR / External Liaison',s)
        self.assertIn('運営、公開環境の構築、技術面の検討・実装支援',s)
        self.assertIn('問い合わせの取次ぎ',s)
        self.assertIn('運営責任者や法的代理人の資格を示すものではありません',s)
        for private in ['佐藤','AJS','zin1985','@gmail.com']:
            self.assertNotIn(private,s[s.index('<section class="team-collaborators"'):s.index('</section></div></div></section>',s.index('<section class="team-collaborators"'))])
    def test_qualifications_are_individual_not_project_certifications(self):
        s=PAGE.read_text('utf8')
        self.assertEqual(s.count('id="team-qualifications-heading"'),1)
        for item in ['kintone認定 アプリデザインスペシャリスト',
                     'kintone認定 アソシエイト',
                     'ITIL&#174; 4 Foundation <span>2026年取得</span>',
                     'ResoArc自体への認定、各認定機関からの推奨や提携を示すものではありません']:
            self.assertIn(item,s)
        self.assertNotIn('2029年',s)
    def test_css_scoped_and_responsive(self):
        page=PAGE.read_text('utf8')
        css=CSS.read_text('utf8')
        self.assertIn('<link rel="stylesheet" href="/assets/team-collaborators.css">',page)
        self.assertIn('@media(max-width:700px)',css)
        self.assertNotIn('position:fixed',css)
        self.assertTrue(all(line.strip().startswith(('/*','.team-collaborators','@media','}')) for line in css.splitlines() if line.strip()))
if __name__=='__main__':
    unittest.main()
