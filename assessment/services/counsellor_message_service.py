"""
Counsellor messages — trait-based, domain-specific, no repeated phrases.
Each level has distinct structure. Tradeoff appears once. Decision tension included.
"""
from __future__ import annotations

STREAM_DISPLAY = {
    "science": "Science (PCM/PCB)", "commerce": "Commerce",
    "arts": "Arts & Humanities", "vocational": "Vocational / Skill-based",
    "sports": "Sports & Physical Education", "fine_arts": "Fine Arts & Performing Arts",
    "agriculture": "Agriculture",
}

DOMAIN_DISPLAY = {
    "ai_data": "AI & Data Science", "cloud_computing": "Cloud Computing",
    "cybersecurity": "Cybersecurity", "fintech": "Finance & FinTech",
    "healthtech": "Healthcare Tech", "biotech": "Biotechnology",
    "digital_marketing": "Digital Marketing", "creator_economy": "Content & Media",
    "legaltech": "Law & Legal Tech", "edtech": "Education Technology",
    "robotics": "Robotics & Automation", "manufacturing": "Manufacturing & Engineering",
    "ecommerce": "E-Commerce", "entrepreneurship": "Entrepreneurship",
    "agritech": "AgriTech", "traveltech": "Travel & Hospitality",
    "defense_tech": "Defense & Armed Forces", "space_tech": "Aviation & Aerospace",
    "mental_health": "Psychology & Mental Health", "fashiontech": "Fashion & Design",
    "ar_vr": "AR/VR & Immersive Tech", "gaming": "Gaming",
    "data_engineering": "Data Engineering", "supply_chain": "Supply Chain & Ops",
    "hrtech": "HR & People Management", "insurance_tech": "Insurance & Risk",
    "climate_tech": "Climate Tech", "renewable_energy": "Renewable Energy",
    "ev_mobility": "EV & Mobility", "iot": "IoT & Smart Systems",
    "blockchain": "Blockchain & Web3", "nanotech": "Nanotechnology",
    "quantum": "Quantum Computing", "pharma": "Pharmaceuticals",
    "med_devices": "Medical Devices", "construction_tech": "Construction Tech",
    "urban_tech": "Smart Cities", "water_tech": "Water Technology",
    "energy_storage": "Energy Storage", "ai_ethics": "AI Ethics & Policy",
    "marketing": "Marketing", "sports_tech": "Sports Science", "foodtech": "Food Technology",
    "devops": "DevOps",
}

CAREER_DISPLAY = {
    "data_scientist": "Data Scientist", "ml_engineer": "ML Engineer",
    "data_analyst": "Data Analyst", "software_engineer": "Software Engineer",
    "cybersecurity_analyst": "Cybersecurity Analyst", "ethical_hacker": "Ethical Hacker",
    "financial_analyst": "Financial Analyst", "investment_banker": "Investment Banker",
    "digital_marketer": "Digital Marketer", "seo_specialist": "SEO Specialist",
    "uiux_designer": "UI/UX Designer", "graphic_designer": "Graphic Designer",
    "robotics_engineer": "Robotics Engineer", "cloud_engineer": "Cloud Engineer",
    "product_manager": "Product Manager", "agriculture_officer": "Agriculture Officer",
    "journalist": "Journalist", "content_creator": "Content Creator",
    "doctor": "Doctor", "pharmacist": "Pharmacist", "teacher": "Teacher",
    "defense_officer": "Defense Officer", "pilot": "Pilot", "entrepreneur": "Entrepreneur",
    "hotel_manager": "Hotel Manager", "junior_content_creator": "Junior Content Creator",
    "freelance_designer": "Freelance Designer", "coding_intern": "Junior Developer",
    "junior_sales_executive": "Junior Sales Executive",
    "data_entry_analyst": "Data Entry Analyst", "field_technician": "Field Technician",
}


# ── Domain knowledge: insight, tradeoff, action, tension ─────────────────────
# insight   = what makes this domain genuinely worth pursuing
# tradeoff  = the honest downside
# action    = one specific thing to do right now (domain-specific)
# tension   = the real decision the user faces in this domain

DOMAIN_KNOWLEDGE = {
    "ai_data": (
        "The skills compound fast here — someone who starts building in AI today will be significantly ahead in 3 years.",
        "The field moves so fast that what you learn today may be outdated in 18 months. Staying current is a job in itself.",
        "Pick one real dataset, build one end-to-end project, and put it on GitHub — that single thing will open more doors than 10 certifications.",
        "The tension: do you want to understand the models deeply (research path) or ship products fast (engineering path)? They need different skills.",
    ),
    "data_engineering": (
        "Every company has data. Almost none of them can use it well. Data engineers who can build reliable pipelines are genuinely hard to find.",
        "It's less visible than data science — you're the plumbing, not the product. Recognition can be slow.",
        "Learn dbt and one cloud data warehouse (BigQuery or Snowflake). Those two skills alone will get you interviews.",
        "The tension: pure data engineering vs. analytics engineering. One is infrastructure, the other is closer to the business. Know which you want.",
    ),
    "cloud_computing": (
        "Cloud skills travel across every industry — finance, healthcare, retail, government. You're never stuck in one sector.",
        "It can feel abstract at first. You're managing infrastructure you can't physically touch, and the cost of mistakes is real.",
        "Get the AWS Cloud Practitioner cert first — it's the fastest way to prove baseline knowledge and costs under ₹5,000.",
        "The tension: generalist cloud engineer vs. specialist (DevOps, security, ML infrastructure). Generalists get hired faster; specialists earn more.",
    ),
    "devops": (
        "DevOps engineers see the full picture of how software ships — you're the bridge between building and running.",
        "You're often the person on call when things break at 2am. The responsibility is real and the pressure doesn't go away.",
        "Set up a CI/CD pipeline for a personal project using GitHub Actions — it's free and shows you understand the core loop.",
        "The tension: platform engineering (building internal tools) vs. site reliability (keeping things running). Very different day-to-day.",
    ),
    "cybersecurity": (
        "Every organisation needs it, and there's a genuine global shortage. Job security in this field is unusually strong.",
        "It's a cat-and-mouse game that never ends. Staying current requires constant learning, and the stakes of getting it wrong are high.",
        "Set up a home lab using TryHackMe or HackTheBox — hands-on practice is what separates candidates in this field.",
        "The tension: offensive security (ethical hacking, red team) vs. defensive security (SOC, blue team). They attract very different personalities.",
    ),
    "fintech": (
        "Finance is being rebuilt with technology — there's room to do genuinely interesting work at the intersection of both.",
        "It's heavily regulated, which slows everything down. If you want to move fast and break things, fintech will frustrate you.",
        "Learn SQL and basic financial modelling — those two skills together make you immediately useful in any fintech role.",
        "The tension: working at a bank's tech team (stable, slower) vs. a fintech startup (faster, riskier). The culture gap is enormous.",
    ),
    "healthtech": (
        "The impact is tangible — the work you do can directly affect patient outcomes and healthcare access.",
        "Healthcare moves slowly by design. Regulatory approvals and hospital procurement cycles take years.",
        "Talk to one doctor or nurse about their biggest workflow frustration — that conversation will give you more product ideas than any research report.",
        "The tension: clinical tools (high regulation, high impact) vs. wellness apps (faster to build, harder to monetise).",
    ),
    "biotech": (
        "You're working at the frontier of what's scientifically possible — genomics, drug discovery, synthetic biology.",
        "Research timelines are long and failure rates are high. Most breakthroughs take years, and many don't pan out.",
        "Learn Python for bioinformatics (Biopython, pandas) — it's the fastest way to make yourself useful in a biotech lab.",
        "The tension: staying in research (slower, deeper) vs. moving to industry (faster, more applied). Both are valid but need different positioning.",
    ),
    "ev_mobility": (
        "The automotive industry is going through its biggest transformation in a century — there's genuine ground-floor opportunity.",
        "It's capital-intensive and dominated by a few large players. Breaking in without the right credentials is harder than it looks.",
        "Get familiar with battery management systems and CAN bus protocols — those are the two technical areas most EV companies hire for.",
        "The tension: hardware (battery, motor, chassis) vs. software (firmware, fleet management, charging infrastructure). Very different career paths.",
    ),
    "manufacturing": (
        "Skilled trades are genuinely undervalued — and automation is creating new roles that blend hands-on work with technology.",
        "Physical work environments can be demanding, and career progression often requires additional qualifications.",
        "Get an NSDC certification in your specific trade — it's recognised by most large manufacturers and opens apprenticeship doors.",
        "The tension: staying on the shop floor (hands-on, stable) vs. moving into process engineering or management (more desk work, higher ceiling).",
    ),
    "robotics": (
        "Robotics is moving from factory floors to hospitals, homes, and agriculture — the application space is expanding fast.",
        "It requires a mix of mechanical, electrical, and software skills. Being strong in all three takes time.",
        "Build something physical — even a simple Arduino or Raspberry Pi project. Employers in robotics want to see you've actually built things.",
        "The tension: industrial robotics (stable, well-paying) vs. research robotics (cutting-edge, uncertain). The job markets are very different.",
    ),
    "iot": (
        "IoT connects the physical and digital worlds — it's showing up in everything from smart homes to industrial automation.",
        "Security and interoperability are constant headaches. The ecosystem is fragmented and standards are still evolving.",
        "Learn MQTT and one microcontroller platform (ESP32 or Arduino) — those are the entry points for most IoT roles.",
        "The tension: consumer IoT (smart home, wearables) vs. industrial IoT (manufacturing, logistics). Very different scale and complexity.",
    ),
    "digital_marketing": (
        "Every business needs it, and the tools keep evolving — there's always something new to learn.",
        "Platform changes can wipe out strategies overnight. You're always chasing algorithms.",
        "Run a real campaign — even ₹500 on Google or Meta ads. The learning from spending real money is worth more than any course.",
        "The tension: performance marketing (data-driven, measurable) vs. brand marketing (creative, harder to measure). Know which you prefer.",
    ),
    "creator_economy": (
        "The barrier to entry is low and the upside is real — you can build an audience and a business with just a phone.",
        "Income is unpredictable, especially early on. Building a sustainable audience takes longer than most people expect.",
        "Post consistently for 90 days before judging results — most people quit before the algorithm starts working for them.",
        "The tension: building your own brand (high upside, slow start) vs. working for brands as a creator (faster income, less ownership).",
    ),
    "legaltech": (
        "Law is one of the last industries to be disrupted by technology — there's a lot of low-hanging fruit.",
        "Legal work is detail-intensive and high-stakes. Mistakes have real consequences.",
        "Learn contract analysis tools and basic legal research platforms — those are the two areas where tech is replacing manual work fastest.",
        "The tension: building legal tech products (needs both legal and tech knowledge) vs. practising law with tech skills (more traditional path).",
    ),
    "edtech": (
        "Education is a massive market and genuinely underserved — there's real room to build things that matter.",
        "Monetisation is hard. Schools and institutions are slow to adopt new tools.",
        "Teach one thing online — a YouTube video, a short course, anything. The feedback you get will tell you more than any market research.",
        "The tension: B2C (selling to students directly, faster feedback) vs. B2B (selling to schools, slower but more scalable).",
    ),
    "entrepreneurship": (
        "You get to build something from scratch and own the outcome — the learning curve is steep but the upside is uncapped.",
        "Most startups fail. The emotional and financial risk is real, and it takes longer than you think to get traction.",
        "Talk to 10 potential customers before writing a single line of code or spending any money — most startup failures are solved by this step.",
        "The tension: building a lifestyle business (sustainable, lower risk) vs. a venture-backed startup (high risk, high reward). They need completely different strategies.",
    ),
    "mental_health": (
        "There's a massive unmet need globally — and the stigma around mental health is finally starting to reduce.",
        "It's emotionally demanding work. Burnout is common, and the pay in clinical roles often doesn't reflect the difficulty.",
        "Get supervised clinical hours as early as possible — they're required for licensure and the waiting lists are long.",
        "The tension: clinical practice (direct patient work, regulated) vs. mental health tech (product work, less regulated but less direct impact).",
    ),
    "defense_tech": (
        "The work is high-stakes and the technology is cutting-edge — defense is one of the few sectors with unlimited R&D budgets.",
        "It's a closed ecosystem with strict clearance requirements. Career mobility outside defense can be limited.",
        "Look into DRDO or defense PSU recruitment — they have structured entry paths that most people don't know about.",
        "The tension: government defense (job security, slower pace) vs. private defense contractors (faster, more commercial).",
    ),
    "space_tech": (
        "Commercial space is growing fast — ISRO, SpaceX, and dozens of startups are hiring.",
        "The path in is narrow and competitive. Most roles require very specific technical backgrounds.",
        "Follow ISRO's Young Scientist Programme and IIST admissions — those are the two most direct paths into Indian space careers.",
        "The tension: government space agencies (stable, prestigious) vs. commercial space startups (riskier, faster-moving).",
    ),
    "climate_tech": (
        "The urgency is real and the investment is following — climate tech is one of the fastest-growing sectors globally.",
        "Many climate solutions are still pre-commercial. You may spend years on something that doesn't reach scale.",
        "Map the climate tech ecosystem in India — there are more funded startups than most people realise, and they're hiring.",
        "The tension: working on mitigation (reducing emissions) vs. adaptation (dealing with climate impacts). Very different problem spaces.",
    ),
    "renewable_energy": (
        "Solar, wind, and storage are now cost-competitive with fossil fuels — the transition is happening and it needs engineers.",
        "Project timelines are long and heavily dependent on policy and regulation.",
        "Get familiar with solar PV system design tools (PVsyst, Helioscope) — those are the entry-level skills most renewable energy firms hire for.",
        "The tension: project development (business-heavy) vs. engineering design (technical-heavy). Know which side you want to be on.",
    ),
    "quantum": (
        "You'd be working on technology that could fundamentally change computing, cryptography, and materials science.",
        "It's still largely research-stage. Practical commercial applications are 5-10 years away for most use cases.",
        "Learn Qiskit (IBM's quantum computing framework) — it's free, well-documented, and the most common entry point for quantum computing roles.",
        "The tension: quantum hardware (physics-heavy, very specialised) vs. quantum software/algorithms (more accessible, growing faster).",
    ),
    "nanotech": (
        "Nanotechnology is enabling breakthroughs in medicine, materials, and electronics.",
        "It's a long-horizon field — most applications are still in research. Patience and tolerance for uncertainty are essential.",
        "Focus on one application area (drug delivery, materials, or semiconductors) rather than nanotechnology broadly — the job markets are very different.",
        "The tension: academic research (deep, slow) vs. industry R&D (applied, faster). The skills overlap but the culture doesn't.",
    ),
    "pharma": (
        "Drug development is one of the most impactful things you can work on — and the industry is being transformed by AI.",
        "The timelines are brutal. A drug can take 10-15 years from discovery to market, and most candidates fail in trials.",
        "Learn regulatory affairs basics (FDA, CDSCO guidelines) — it's an underrated skill that makes you immediately useful in any pharma company.",
        "The tension: research and development (scientific, long-horizon) vs. commercial pharma (sales, marketing, faster feedback).",
    ),
    "agritech": (
        "Agriculture feeds the world and it's massively underdigitised — there's a lot of room to build things that have real impact.",
        "Rural adoption is slow and the market is fragmented. Getting farmers to change behaviour is genuinely hard.",
        "Spend time in a rural area talking to farmers before building anything — the gap between what urban founders think farmers need and what they actually need is enormous.",
        "The tension: building for large commercial farms (easier to sell to, less impact) vs. smallholder farmers (harder, more impact).",
    ),
    "traveltech": (
        "Travel is one of the most resilient industries — people always find a way to travel.",
        "It's highly cyclical and vulnerable to external shocks like pandemics or geopolitical events.",
        "Learn revenue management and dynamic pricing — those are the two skills that travel companies consistently struggle to hire for.",
        "The tension: OTA/booking platforms (scale, competitive) vs. experience and hospitality tech (niche, more differentiated).",
    ),
    "supply_chain": (
        "Supply chains are the backbone of the global economy — and the pandemic showed how fragile and important they are.",
        "It's often unglamorous work. The wins are invisible when things go right.",
        "Get certified in SAP or Oracle SCM — those two platforms run most large supply chains and the certification pays for itself quickly.",
        "The tension: logistics and operations (execution-focused) vs. supply chain strategy and consulting (planning-focused).",
    ),
    "hrtech": (
        "People operations is finally getting the data-driven treatment it deserves.",
        "HR tech is often the last budget to get approved and the first to get cut.",
        "Learn people analytics basics — even Excel-level workforce data analysis makes you stand out in most HR roles.",
        "The tension: HR generalist with tech skills (broader, more stable) vs. HR tech product roles (narrower, higher ceiling).",
    ),
    "ar_vr": (
        "Immersive tech is moving from gaming into training, healthcare, and retail.",
        "Consumer adoption has been slower than expected. The hardware is still clunky.",
        "Build one Unity or Unreal project — even a simple one. It's the fastest way to show you can actually create immersive experiences.",
        "The tension: consumer AR/VR (exciting, uncertain market) vs. enterprise AR/VR (less glamorous, but companies are actually paying for it).",
    ),
    "gaming": (
        "Gaming is the largest entertainment industry in the world — and it's increasingly intersecting with AI, social, and education.",
        "It's a hit-driven business. Most games don't make money, and the industry has a well-documented crunch culture problem.",
        "Build and ship one small game — even a mobile game or a browser game. Shipping something real is what separates game developers from people who want to make games.",
        "The tension: AAA studios (big budgets, high pressure, less creative control) vs. indie development (creative freedom, financial risk).",
    ),
    "fashiontech": (
        "Fashion is one of the most creative industries — and technology is opening up new ways to design, produce, and sell.",
        "It's trend-driven and unpredictable. What's hot today may not be tomorrow.",
        "Build a portfolio of 5-10 strong pieces before applying anywhere — fashion is a visual industry and your work speaks louder than your resume.",
        "The tension: working for established fashion brands (stable, slower) vs. fashion startups (faster, riskier, more creative).",
    ),
    "construction_tech": (
        "Construction is one of the least digitised industries — which means there's a lot of room to improve productivity.",
        "Adoption is slow. Construction companies are conservative and change-resistant.",
        "Learn AutoCAD or Revit — those are the two tools that get you in the door at most construction tech companies.",
        "The tension: software for construction (product work, less site time) vs. construction management with tech skills (more site time, more operational).",
    ),
    "insurance_tech": (
        "Insurance is a massive industry that's been slow to modernise — there's a lot of value to unlock.",
        "It's heavily regulated and the sales cycles are long.",
        "Learn actuarial basics and claims processing workflows — those are the two areas where tech is replacing manual work fastest in insurance.",
        "The tension: underwriting tech (risk-focused, analytical) vs. distribution tech (sales-focused, customer-facing).",
    ),
    "blockchain": (
        "Decentralised systems have real applications in finance, supply chain, and identity — beyond the crypto hype.",
        "The space is noisy and speculative. Separating genuine use cases from hype requires a lot of critical thinking.",
        "Learn Solidity and deploy one smart contract on a testnet — it's the fastest way to show you can actually build on blockchain.",
        "The tension: DeFi and crypto (high risk, high reward, volatile) vs. enterprise blockchain (stable, less exciting, actually being used).",
    ),
    "ai_ethics": (
        "As AI gets deployed everywhere, the people who understand its risks and governance are becoming genuinely important.",
        "It's a new field without clear career paths. Roles are often hybrid — part policy, part technical, part philosophy.",
        "Read the EU AI Act and India's draft AI policy — understanding the regulatory landscape is the fastest way to add value in this space.",
        "The tension: technical AI safety (requires deep ML knowledge) vs. AI policy and governance (requires policy and communication skills). Very different entry points.",
    ),
    "marketing": (
        "Good marketing is what separates products that succeed from ones that don't — it's a skill that transfers across every industry.",
        "It can be hard to measure impact directly, and creative work is subjective.",
        "Run one real campaign with a measurable goal — even a small one. The ability to show results is what separates marketers who get hired from those who don't.",
        "The tension: brand marketing (creative, long-term) vs. performance marketing (data-driven, short-term). Most companies need both but hire for one.",
    ),
    "sports_tech": (
        "Sports science is transforming how athletes train, recover, and perform — and the data side is growing fast.",
        "It's a niche market. Roles are competitive and often tied to specific teams or organisations.",
        "Get certified in sports science or strength and conditioning — those credentials open doors that a general fitness background doesn't.",
        "The tension: working with elite athletes (high pressure, high visibility) vs. mass market fitness tech (larger market, less prestige).",
    ),
    "foodtech": (
        "Food is a universal need and the industry is being reinvented — from alternative proteins to supply chain transparency.",
        "Consumer behaviour is hard to change. People are conservative about what they eat.",
        "Understand food safety regulations (FSSAI in India) — it's the one area where most food tech founders get caught out.",
        "The tension: alternative proteins and deep food tech (long R&D cycles) vs. food delivery and restaurant tech (faster, more competitive).",
    ),
    "med_devices": (
        "Medical devices sit at the intersection of engineering and healthcare — the work has direct patient impact.",
        "Regulatory approval is slow and expensive. Getting a device to market can take years.",
        "Learn ISO 13485 (quality management for medical devices) — it's the standard that every medical device company operates under.",
        "The tension: diagnostic devices (high regulatory bar, high impact) vs. wellness devices (lower bar, larger consumer market).",
    ),
}

_DEFAULT_KNOWLEDGE = (
    "This is a growing field with real demand for skilled people.",
    "Like any specialisation, it takes time to build credibility and the early years can be slow.",
    "Find one person working in this field and have a real conversation with them — it's worth more than any research.",
    "The tension: going deep in this specific area vs. keeping your options open. Both are valid, but they need different strategies.",
)

STREAM_KNOWLEDGE = {
    "science": (
        "Science opens the most doors — engineering, medicine, research, even finance and law later.",
        "The workload in 11th-12th is genuinely heavy. Physics, Chemistry, Maths together is a lot.",
        "Sit in on a class or watch a few lectures in the subjects you'd actually study — not the career outcomes, the actual content.",
        "The tension: PCM (engineering path) vs. PCB (medical path). You can't easily switch after 11th, so this decision matters.",
    ),
    "commerce": (
        "Commerce is more flexible than people think — it leads to CA, MBA, banking, marketing, and even tech roles.",
        "It's often chosen as a 'safe' option, which means some students end up in it without real interest.",
        "Talk to a CA or MBA student about what their day actually looks like — not the salary, the work.",
        "The tension: CA route (structured, long, high reward) vs. MBA route (faster, broader, more expensive). Very different commitments.",
    ),
    "arts": (
        "Arts gives you the most freedom to explore — history, psychology, political science, literature, all in one stream.",
        "The career paths are less linear, which requires more self-direction than most 16-year-olds are ready for.",
        "Pick one subject from the arts stream and go deep on it for a month — see if the depth excites you or bores you.",
        "The tension: humanities for its own sake (fulfilling, harder to monetise) vs. humanities as a path to law, civil services, or media (more structured).",
    ),
    "vocational": (
        "Vocational streams are underrated — you come out with a real, marketable skill and can start earning faster than most.",
        "The social perception is still catching up. Some doors (like certain college programs) may require additional qualifications later.",
        "Research which specific trade has the best job market in your city right now — the difference between trades can be significant.",
        "The tension: starting work early (faster income, less flexibility) vs. upgrading to a diploma or degree later (slower, more options).",
    ),
    "sports": (
        "If you're serious about sports, this is the right path — it gives you structured training alongside academics.",
        "The window for professional sports is narrow. Having a backup plan isn't giving up — it's being smart.",
        "Get a realistic assessment from your coach about your competitive level — not encouragement, an honest evaluation.",
        "The tension: pursuing sports as a career (high risk, high reward) vs. sports science or coaching (more stable, still in the field).",
    ),
    "fine_arts": (
        "Creative fields are growing — design, animation, film, and digital art are all in demand.",
        "Building a portfolio takes years, and the early income can be unpredictable.",
        "Start building a portfolio now, before you even finish 10th — the earlier you start, the better your options at 12th.",
        "The tension: fine arts as a craft (painting, sculpture, performance) vs. applied arts (design, animation, UX). Very different career markets.",
    ),
    "agriculture": (
        "Agriculture is being transformed by technology — agritech, food science, and sustainable farming are real career paths.",
        "Traditional agriculture is hard work with uncertain income. The opportunity is in the tech and business side of it.",
        "Visit one agritech startup or agricultural research institute — seeing what modern agriculture looks like changes the perception completely.",
        "The tension: traditional farming (land-dependent, uncertain) vs. agritech and food science (urban-friendly, growing fast).",
    ),
}

_DEFAULT_STREAM_KNOWLEDGE = (
    "This stream has real career potential if it aligns with your interests.",
    "Every stream has trade-offs — make sure you're choosing based on what you enjoy, not just what seems safe.",
    "Talk to someone already in this stream and ask them what they wish they'd known before choosing.",
    "The tension: choosing what you're good at vs. choosing what you enjoy. Ideally both, but if you have to pick one, enjoy wins long-term.",
)


def _d(code: str, mapping: dict) -> str:
    clean = code.split("__", 1)[-1].lower() if "__" in code else code.lower()
    return mapping.get(clean, clean.replace("_", " ").title())

def _clean(code: str) -> str:
    return code.split("__", 1)[-1].lower() if "__" in code else code.lower()

def _dk(code: str):
    return DOMAIN_KNOWLEDGE.get(_clean(code), _DEFAULT_KNOWLEDGE)

def _sk(code: str):
    return STREAM_KNOWLEDGE.get(_clean(code), _DEFAULT_STREAM_KNOWLEDGE)

def _confidence_label(confidence: int) -> str:
    if confidence >= 72: return "Strong match"
    if confidence >= 55: return "Good match"
    if confidence >= 38: return "Moderate match"
    if confidence >= 20: return "Early signal"
    return "Not enough data yet"
