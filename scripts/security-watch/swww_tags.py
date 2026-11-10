#!/usr/bin/env python3
"""Conservative, source-evidenced technology tags for public advisories.

Tags mean: 'mentioned as a relevant technology in published advisory',
NOT that ResoArc deploys the product or is vulnerable.
"""
from __future__ import annotations
import re

# id, public label, group/color, explicit title/package pattern,
# optional more-specific body pattern to reduce incidental mentions.
RULES = [
    ("oracle", "Oracle", "vendor", r"\boracle(?:\s+(?:database|linux|java|jdk|weblogic|mysql|virtualbox|fusion|cloud|products?))?\b",r"\boracle\s+(?:database|linux|jdk|weblogic|cloud|java|virtualbox|mysql)\b"),
    ("java", "Java", "runtime", r"\bjava(?:\s+(?:se|ee|jdk|runtime|development kit|application|applet|framework))?\b|\bopenjdk\b|\bJDK\b",r"\b(?:java\s+(?:se|ee|jdk|runtime|application)|openjdk|jdk\s*\d+)\b"),
    ("php", "PHP", "runtime", r"\bphp(?:[-\s]?(?:fpm|cgi|runtime))?\b",r"\bphp[-\s]?(?:runtime|fpm|cgi|versions?|\d\.\d)\b"),
    ("python", "Python", "runtime", r"\bpython(?:3|[-\s]\d(?:\.\d+)?)?\b|\bPillow\b|\bDjango\b|\bFlask\b",r"\bpython\s+(?:package|library|module|version|application)\b"),
    ("javascript", "JavaScript", "runtime", r"\bjavascript\b|\btypescript\b|\bECMAScript\b",r"\b(?:javascript|typescript)\s+(?:code|application|runtime|package)\b"),
    ("nodejs", "Node.js", "runtime", r"\bnode\.?js\b|\bnpm\b|\bexpress\.?js\b",r"\bnode\.?js\b|\bnpm\s+(?:package|registry|module)\b"),
    ("dotnet", ".NET", "runtime", r"\b\.net\b|\basp\.?net\b|\bdotnet\b",r"\b(?:asp\.?net|dotnet|\.net\s+(?:core|framework|runtime))\b"),
    ("go", "Go", "runtime", r"\bgolang\b|\bgo\s+(?:language|compiler|module|toolchain|runtime)\b",r"\bgolang\b|\bgo\s+(?:compiler|module|toolchain)\b"),
    ("ruby", "Ruby", "runtime", r"\bruby(?:\s+on\s+rails)?\b|\brails\s+(?:framework|application)\b",r"\bruby\s+(?:gem|package|runtime|application)\b"),
    ("windows", "Windows", "os", r"\b(?:microsoft\s+)?windows(?:\s+(?:server|10|11|kernel))?\b",r"\bwindows\s+(?:server|operating\s+system|kernel|service|platform)\b"),
    ("linux", "Linux", "os", r"\blinux\b|\b(?:ubuntu|debian|rocky linux|red hat enterprise linux|rhel|almalinux|fedora)\b",r"\b(?:linux\s+(?:kernel|distribution|server)|ubuntu|debian|rocky linux|red hat enterprise linux)\b"),
    ("macos", "macOS", "os", r"\bmacos\b|\bmac\s+os\b|\bOS X\b",r"\b(?:macos|mac os)\s+(?:version|server|system)\b"),
    ("android", "Android", "os", r"\bandroid\b",r"\bandroid\s+(?:devices?|system|versions?|application)\b"),
    ("ios", "iOS", "os", r"\b(?:iOS|iPadOS)\b",r"\b(?:iOS|iPadOS)\s+(?:devices?|system|versions?|application)\b"),
    ("gitlab", "GitLab", "devops", r"\bgitlab\b",r"\bgitlab\s+(?:ce|ee|runner|versions?|server)\b"),
    ("github", "GitHub", "devops", r"\bgithub\b",r"\bgithub\s+(?:enterprise|actions|copilot|runner|repository)\b"),
    ("docker", "Docker", "infra", r"\bdocker\b|\bcontainerd\b",r"\b(?:docker|containerd)\s+(?:engine|desktop|container|image|daemon)\b"),
    ("kubernetes", "Kubernetes", "infra", r"\bkubernetes\b|\bk8s\b",r"\bkubernetes\s+(?:cluster|api|controller|server)\b"),
    ("apache", "Apache", "infra", r"\bapache(?:\s+(?:http\s+server|httpd|tomcat|struts|log4j))?\b|\blog4j\b|\btomcat\b",r"\b(?:apache\s+(?:http|tomcat|struts|log4j)|log4j|tomcat)\b"),
    ("nginx", "NGINX", "infra", r"\bnginx\b",r"\bnginx\s+(?:web|server|module|proxy)\b"),
    ("openssl", "OpenSSL", "infra", r"\bopenssl\b",r"\bopenssl\s+(?:library|versions?|package)\b"),
    ("postgresql", "PostgreSQL", "database", r"\bpostgres(?:ql)?\b",r"\bpostgres(?:ql)?\s+(?:database|server|extension)\b"),
    ("mysql", "MySQL", "database", r"\bmysql\b|\bmariadb\b",r"\b(?:mysql|mariadb)\s+(?:database|server|connector)\b"),
    ("sqlserver", "SQL Server", "database", r"\b(?:microsoft\s+)?sql\s+server\b|\bMSSQL\b",r"\b(?:sql\s+server|mssql)\s+(?:database|server|instance)\b"),
    ("redis", "Redis", "database", r"\bredis\b",r"\bredis\s+(?:server|instance|database)\b"),
    ("mongodb", "MongoDB", "database", r"\bmongodb\b",r"\bmongodb\s+(?:server|database|driver)\b"),
    ("wordpress", "WordPress", "cms", r"\bwordpress\b|\bwp[-\s]?(?:plugin|core|theme)\b",r"\bwordpress\s+(?:plugin|theme|core|site)\b"),
    ("drupal", "Drupal", "cms", r"\bdrupal\b",r"\bdrupal\s+(?:core|module|plugin)\b"),
    ("chrome", "Chrome", "browser", r"\b(?:google\s+)?chrome(?:ium)?\b",r"\b(?:google\s+chrome|chromium\s+browser|chrome\s+browser)\b"),
    ("firefox", "Firefox", "browser", r"\bfirefox\b|\bmozilla\s+firefox\b",r"\bfirefox\s+(?:browser|versions?|engine)\b"),
    ("edge", "Microsoft Edge", "browser", r"\bmicrosoft\s+edge\b|\bedge\s+browser\b",r"\bmicrosoft\s+edge\b|\bedge\s+browser\b"),
    ("cloudflare", "Cloudflare", "cloud", r"\bcloudflare\b",r"\bcloudflare\s+(?:workers?|pages|waf|dns|turnstile)\b"),
    ("aws", "AWS", "cloud", r"\baws\b|\bamazon\s+web\s+services\b",r"\b(?:aws\s+(?:lambda|ec2|iam|s3|cloud)|amazon web services)\b"),
    ("azure", "Azure", "cloud", r"\b(?:microsoft\s+)?azure\b",r"\b(?:azure\s+(?:active directory|functions|blob|vm|cloud)|microsoft azure)\b"),
    ("kintone", "kintone", "platform", r"\bkintone\b|\bcybozu\b",r"\bkintone\s+(?:plugin|api|app|platform)\b"),
    ("spring", "Spring", "framework", r"\bspring\s+(?:framework|boot|security|cloud)\b",r"\bspring\s+(?:framework|boot|security|cloud)\b"),
    ("react", "React", "framework", r"\breact(?:\.?js)?\b|\bnext\.?js\b",r"\breact(?:\.?js)?\s+(?:component|application|framework)\b|\bnext\.?js\b"),
    ("vue", "Vue.js", "framework", r"\bvue\.?js\b|\bnuxt(?:\.?js)?\b",r"\bvue\.?js\b|\bnuxt(?:\.?js)?\b"),
    ("laravel", "Laravel", "framework", r"\blaravel\b",r"\blaravel\s+(?:framework|application|package)\b"),
]
_RULES=[(tag,label,group,re.compile(title,re.I),re.compile(body,re.I)) for tag,label,group,title,body in RULES]
TAXONOMY={tag:{"id":tag,"label":label,"group":group} for tag,label,group,_,_ in RULES}

def classify(advisory,maximum=9):
    title=str(advisory.get("title",""))[:700]
    package=str(advisory.get("package",""))[:280]
    summary=str(advisory.get("summary",""))[:5000]
    result=[]
    for tag,label,group,primary,body in _RULES:
        if primary.search(title) or primary.search(package):
            origin="title-or-package"
        elif body.search(summary):
            origin="description"
        else:
            continue
        result.append({"id":tag,"label":label,"group":group,"evidence":origin})
        if len(result)>=maximum:break
    return result
