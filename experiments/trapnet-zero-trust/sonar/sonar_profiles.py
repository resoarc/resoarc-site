"""TrapNet static deployment-level HTTP profiles (never selected by remote requests).

Profiles are optional per-node configuration. The default exactly preserves the
previous production Server banner; no runtime changes or per-request randomness.
"""
import os

BANNERS={
    "nginx":"nginx/1.24.0",
    "apache":"Apache/2.4.58",
    "gateway":"envoy",
}
def selected_profile():
    profile=os.environ.get("TRAPNET_SONAR_PROFILE","nginx").strip().lower()
    return profile if profile in BANNERS else "nginx"
def server_banner():
    return BANNERS[selected_profile()]
