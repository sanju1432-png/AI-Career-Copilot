import json
import os
import re
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

CAREERS = {
    'AI/ML Engineer': ['Python','Machine Learning','Deep Learning','SQL','FastAPI','Git'],
    'Data Scientist': ['Python','SQL','Statistics','Machine Learning','Pandas','Data Visualization'],
    'Full Stack Developer': ['JavaScript','React','Node.js','SQL','REST APIs','Git'],
    'Backend Developer': ['Python','FastAPI','SQL','REST APIs','Docker','Git'],
    'Frontend Developer': ['JavaScript','React','HTML/CSS','TypeScript','Git'],
    'Data Analyst': ['SQL','Excel','Python','Statistics','Data Visualization','Power BI'],
    'DevOps Engineer': ['Linux','Git','Docker','CI/CD','Kubernetes','Cloud'],
    'Cloud Engineer': ['Linux','Networking','Cloud','Docker','Kubernetes','Terraform'],
    'Cybersecurity Analyst': ['Networking','Linux','Python','Security Fundamentals','SIEM','Incident Response'],
    'Mobile App Developer': ['Java/Kotlin','Android','REST APIs','Git','UI Development'],
    'Product Analyst': ['SQL','Excel','Statistics','Product Metrics','Data Visualization'],
    'QA Automation Engineer': ['Python/Java','Selenium','API Testing','SQL','Git','Test Automation'],
}

SKILLS = sorted({s for v in CAREERS.values() for s in v} | {
    'Python','Java','JavaScript','React','SQL','Machine Learning','Deep Learning','NLP','Git','Docker',
    'FastAPI','Node.js','TypeScript','HTML/CSS','Statistics','Pandas','Data Visualization','Excel','Power BI',
    'Linux','Networking','Cloud','Kubernetes','Terraform','CI/CD','REST APIs','Selenium','API Testing',
    'Test Automation','Security Fundamentals','SIEM','Incident Response','Android','Product Metrics','UI Development'
})

RESOURCE_MAP = {
    'Python':'https://docs.python.org/3/tutorial/', 'JavaScript':'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
    'React':'https://react.dev/learn', 'SQL':'https://www.postgresql.org/docs/current/tutorial.html',
    'Machine Learning':'https://scikit-learn.org/stable/user_guide.html', 'Deep Learning':'https://pytorch.org/tutorials/',
    'Git':'https://git-scm.com/book/en/v2', 'Docker':'https://docs.docker.com/get-started/',
    'FastAPI':'https://fastapi.tiangolo.com/tutorial/', 'Node.js':'https://nodejs.org/en/learn',
    'TypeScript':'https://www.typescriptlang.org/docs/', 'Pandas':'https://pandas.pydata.org/docs/getting_started/intro_tutorials/',
    'Statistics':'https://www.khanacademy.org/math/statistics-probability', 'Linux':'https://linuxjourney.com/',
    'Kubernetes':'https://kubernetes.io/docs/tutorials/', 'Cloud':'https://aws.amazon.com/training/',
    'HTML/CSS':'https://developer.mozilla.org/en-US/docs/Learn', 'Data Visualization':'https://public.tableau.com/app/learn',
    'Excel':'https://support.microsoft.com/excel', 'Power BI':'https://learn.microsoft.com/power-bi/',
    'Selenium':'https://www.selenium.dev/documentation/', 'API Testing':'https://learning.postman.com/docs/introduction/overview/',
}

ROADMAPS = {
    'AI/ML Engineer': [('Foundations','Python, statistics and data handling',['Build a data-cleaning notebook','Complete 20 Python exercises']),('Machine Learning','Supervised learning, evaluation and feature engineering',['Train and compare 3 models','Write an evaluation report']),('Deep Learning & APIs','Neural networks and serving models',['Build a small PyTorch model','Expose inference through FastAPI']),('Portfolio & Placement','Production thinking and interviews',['Deploy one AI project','Prepare project story and technical interview answers'])],
    'Data Scientist': [('Data Foundations','Python, SQL and statistics',['Analyze a real dataset','Write 25 SQL queries']),('EDA & Visualization','Pandas, statistics and storytelling',['Create an EDA report','Build a dashboard']),('Machine Learning','Modeling, validation and interpretation',['Build an end-to-end ML pipeline','Compare models with cross-validation']),('Portfolio & Placement','Business impact and communication',['Publish one case study','Practice analytics interviews'])],
    'Full Stack Developer': [('Frontend Core','HTML/CSS, JavaScript and React',['Build a responsive UI','Create reusable React components']),('Frontend Engineering','State, routing and APIs',['Build an authenticated React app','Consume a REST API']),('Backend & Data','Node/FastAPI, REST and SQL',['Build CRUD APIs','Add auth and database persistence']),('Full Product','Testing, deployment and portfolio',['Ship a full-stack project','Document architecture and trade-offs'])],
    'Backend Developer': [('Programming Core','Python/Java, Git and problem solving',['Build CLI utilities','Solve 25 backend coding problems']),('APIs & Databases','REST, SQL and authentication',['Build a production-style API','Design a relational schema']),('Reliability','Testing, Docker and security',['Containerize the service','Add tests and structured logging']),('Deployment','Cloud basics and system design',['Deploy an API','Prepare backend/system-design interview answers'])],
}

class AIServiceError(RuntimeError):
    pass


def norm(s):
    return re.sub(r'[^a-z0-9+#/ ]','',s.lower()).strip()


def match_careers(skills):
    ss={norm(s) for s in skills}
    out=[]
    for career, req in CAREERS.items():
        matched=[x for x in req if norm(x) in ss]
        missing=[x for x in req if norm(x) not in ss]
        score=round(len(matched)/len(req)*100)
        out.append({'career':career,'match':score,'matched':matched,'missing':missing,'required':req})
    return sorted(out,key=lambda x:(x['match'],x['career']),reverse=True)


def analyze_resume(text):
    low=text.lower(); found=[]
    for skill in SKILLS:
        aliases=[skill.lower(), skill.lower().replace('/',' ')]
        if any(a in low for a in aliases): found.append(skill)
    careers=match_careers(found)
    return {'skills':found,'score':min(100,35+len(found)*5),'strengths':found[:8],
            'suggestions':['Quantify project impact with measurable outcomes','Tailor the skills section to your target role','Add links to portfolio/GitHub where relevant'],
            'career_matches':careers[:6]}


def roadmap(skills,target):
    if target not in CAREERS: raise ValueError('Unsupported career')
    ss={norm(x) for x in skills}
    missing=[s for s in CAREERS[target] if norm(s) not in ss]
    base=ROADMAPS.get(target,[])
    if not base:
        base=[('Core Foundations',', '.join(CAREERS[target][:3]),['Learn the highest-priority missing skills','Complete one guided practical exercise']),
              ('Role Skills',', '.join(CAREERS[target][2:5]),['Build a role-aligned mini project','Practice role-specific technical questions']),
              ('Project & Evidence','Portfolio and practical delivery',['Build a portfolio project','Document architecture, decisions and results']),
              ('Placement Preparation','Interview and job readiness',['Complete mock interviews','Tailor resume and applications'])]
    return [{'week':i+1,'title':title,'focus':focus,'tasks':tasks,
             'missing_skills':[s for s in missing if s.lower() in focus.lower() or i<2],
             'resources':[{'name':s,'url':RESOURCE_MAP.get(s,'https://www.google.com/search?q='+s.replace(' ','+'))} for s in CAREERS[target] if s in focus or (i==1 and s in missing)][:3]}
            for i,(title,focus,tasks) in enumerate(base)]


def skill_intelligence(skills,target):
    req=CAREERS.get(target,[]); ss={norm(x) for x in skills}; missing=[x for x in req if norm(x) not in ss]
    priority=[{'skill':x,'priority':'High' if i<2 else 'Medium','reason':f'Core requirement for {target}','resource':RESOURCE_MAP.get(x,'')} for i,x in enumerate(missing)]
    return {'current_skills':skills,'target_role':target,'required_skills':req,'missing_skills':missing,'priority_gaps':priority,'coverage':round((len(req)-len(missing))/len(req)*100) if req else 0}


def _extract_text(data):
    # Current Interactions REST response uses steps -> model_output -> content -> text.
    for step in data.get('steps') or []:
        if step.get('type') != 'model_output':
            continue
        for item in step.get('content') or []:
            if item.get('type') == 'text' and item.get('text'):
                return item['text']
    # Compatibility with older response shapes.
    if data.get('output_text'):
        return data['output_text']
    if isinstance(data.get('output'), str):
        return data['output']
    for item in data.get('outputs') or []:
        if isinstance(item, dict) and item.get('text'):
            return item['text']
    return None


def _request(url, key, payload=None, method='POST', revision=True, timeout=60):
    body=json.dumps(payload).encode() if payload is not None else None
    headers={
        'Content-Type':'application/json',
        'x-goog-api-key':key,
    }
    if revision:
        headers['Api-Revision']='2026-05-20'
    req=urllib.request.Request(url,data=body,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            raw=response.read().decode(errors='replace')
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors='replace')
        raise AIServiceError(f'Gemini HTTP {e.code}: {detail[:1200]}') from e
    except urllib.error.URLError as e:
        raise AIServiceError(f'Gemini connection error: {e.reason}') from e
    except Exception as e:
        raise AIServiceError(f'Gemini request failed: {e}') from e


def _generate_content_text(prompt, key, model):
    """Compatibility fallback for projects where Interactions is unavailable."""
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    payload={
        'contents':[{'role':'user','parts':[{'text':prompt}]}],
        'generationConfig':{'temperature':0.25},
    }
    data=_request(url,key,payload,revision=False,timeout=60)
    candidates=data.get('candidates') or []
    for candidate in candidates:
        content=candidate.get('content') or {}
        for part in content.get('parts') or []:
            if isinstance(part,dict) and part.get('text'):
                return part['text'].strip()
    raise AIServiceError(f'Gemini generateContent returned no text: {json.dumps(data)[:1200]}')


def _interaction_text(prompt, key, model):
    url='https://generativelanguage.googleapis.com/v1beta/interactions'
    try:
        data=_request(url,key,{'model':model,'input':prompt},revision=True,timeout=60)
    except AIServiceError as first_error:
        # Some API gateways reject the revision header. Retry once without it.
        try:
            data=_request(url,key,{'model':model,'input':prompt},revision=False,timeout=60)
        except AIServiceError:
            raise first_error

    if data.get('status') == 'in_progress' and data.get('id'):
        interaction_url=f'{url}/{data["id"]}'
        deadline=time.time()+55
        while time.time() < deadline:
            time.sleep(1.5)
            data=_request(interaction_url,key,method='GET',revision=False,timeout=30)
            if data.get('status') in ('completed','failed','cancelled'):
                break

    if data.get('status') in ('failed','cancelled'):
        raise AIServiceError(f'Gemini interaction {data.get("status")}: {json.dumps(data)[:1200]}')

    output=_extract_text(data)
    if not output:
        raise AIServiceError(f'Gemini returned no text output: {json.dumps(data)[:1200]}')
    return output.strip()


def ai_text(prompt):
    load_dotenv(override=False)
    key=os.getenv('GEMINI_API_KEY','').strip()
    if not key:
        raise AIServiceError('GEMINI_API_KEY is missing from backend/.env')

    model=os.getenv('GEMINI_MODEL','gemini-3.6-flash').strip() or 'gemini-3.6-flash'
    fallback_model=os.getenv('GEMINI_FALLBACK_MODEL',model).strip() or model

    errors=[]
    try:
        return _interaction_text(prompt,key,model)
    except AIServiceError as e:
        errors.append(str(e))

    # Fallback to the standard Gemini generateContent endpoint. This keeps the
    # application working when Interactions is unavailable for the API project.
    for candidate_model in dict.fromkeys([fallback_model,model]):
        try:
            return _generate_content_text(prompt,key,candidate_model)
        except AIServiceError as e:
            errors.append(str(e))

    raise AIServiceError('Gemini AI call failed. | '.join(errors[-3:]))


def ai_json(prompt):
    raw=ai_text(prompt + '\nReturn ONLY valid JSON. Do not use markdown fences or explanatory text.')
    text=raw.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text,flags=re.I)
        text=re.sub(r'\s*```$','',text)
    try:
        value=json.loads(text)
        if isinstance(value,dict):
            return value
    except json.JSONDecodeError:
        pass
    match=re.search(r'\{.*\}',text,re.S)
    if match:
        try:
            value=json.loads(match.group(0))
            if isinstance(value,dict): return value
        except json.JSONDecodeError:
            pass
    raise AIServiceError('Gemini returned text that was not valid JSON for this evaluation.')
