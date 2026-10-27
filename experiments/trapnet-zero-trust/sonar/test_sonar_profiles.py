import os, unittest
import sonar_profiles
class ProfileTests(unittest.TestCase):
    def test_default(self):
        before=os.environ.pop("TRAPNET_SONAR_PROFILE",None)
        try:self.assertEqual(sonar_profiles.server_banner(),"nginx/1.24.0")
        finally:
            if before is not None:os.environ["TRAPNET_SONAR_PROFILE"]=before
    def test_profiles(self):
        before=os.environ.get("TRAPNET_SONAR_PROFILE")
        try:
            for name,header in sonar_profiles.BANNERS.items():
                os.environ["TRAPNET_SONAR_PROFILE"]=name
                self.assertEqual(sonar_profiles.server_banner(),header)
        finally:
            if before is None:os.environ.pop("TRAPNET_SONAR_PROFILE",None)
            else:os.environ["TRAPNET_SONAR_PROFILE"]=before
if __name__=="__main__": unittest.main()
