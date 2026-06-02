from django.db import transaction
from django.core.management.base import BaseCommand

from assessment.models import Question, Option
from domain.models import Domain


# ── Free-text questions (general, shown for any domain) ──
FREE_TEXT_QUESTIONS: list[dict] = [
    {
        "question_text": "What excites you most about this field? Tell us in a few words.",
        "dimension": "interest",
        "question_type": "text",
        "sequence_order": 1,
        "signal_strength": 5,
    },
]

RETIRED_FREE_TEXT_QUESTION_TEXTS = {
    "Tell us about a time you worked on something you really enjoyed. What did you learn from it?",
}


# ── Personality questions unique to each child domain ──
UNIQUE_PERSONALITY_QUESTIONS: dict[str, str] = {
    # Science & Technology
    "AI_ML": "If a machine learning model you trained keeps giving wrong answers after hours of work, how would you feel?",
    "DATA_SCIENCE": "If you found a mistake in a dataset that changes everything, how would you handle it?",
    "WEB_DEV": "When a website you built looks broken on someone's phone, what goes through your mind?",
    "SOFTWARE_DEV": "If your code crashes right before a deadline, how do you react?",
    "CYBER_SECURITY": "If you discovered a security flaw in a system you were protecting, what would you do?",
    "ROBOTICS": "If your robot keeps falling over during a demo, how do you respond?",
    "PURE_SCIENCES": "If your experiment fails for the tenth time, what keeps you going?",
    "ENV_SCIENCE": "If people ignore your environmental findings, how do you respond?",
    "MATH_STATS": "If a problem has no clear answer, how long would you keep working on it?",
    "AEROSPACE_SPACE": "If a model rocket you built crashes, how do you feel about trying again?",
    "MECHANICAL_ENG": "If a machine you designed breaks during testing, what do you do next?",
    "ELECTRICAL_ENG": "If a circuit you built keeps shorting, how do you approach fixing it?",

    # Medical & Health
    "DOCTOR_MEDICINE": "If a patient does not follow your advice, how do you handle it?",
    "NURSING": "If a patient is in pain and treatments are not working, how do you stay calm?",
    "PHARMACY": "If someone asks about a medicine you are not sure about, what do you do?",
    "DENTISTRY": "If a patient is scared of dental treatment, how do you help them feel safe?",
    "PHYSIOTHERAPY": "If a patient is not improving despite exercises, how do you adjust?",
    "PUBLIC_HEALTH": "If a community does not trust your health campaign, what do you do?",
    "MEDICAL_RESEARCH": "If your research findings contradict what everyone believes, how do you proceed?",
    "MENTAL_HEALTH": "If someone shares a painful story with you, how do you respond?",
    "BIOTECH": "If a lab experiment gives unexpected results, how do you react?",
    "HEALTHCARE_ADMIN": "If staff are unhappy with a new policy you implemented, how do you handle it?",

    # Sports & Fitness
    "SPORTS_COACHING": "If your star player is unmotivated at practice, what do you do?",
    "ATHLETIC_TRAINING": "If an athlete pushes too hard and gets injured, how do you handle it?",
    "FITNESS_TRAINING": "If a client skips workouts for weeks, how do you motivate them?",
    "SPORTS_MEDICINE": "If an athlete hides their injury to keep playing, what do you do?",
    "SPORTS_MANAGEMENT": "If a big event faces a last-minute crisis, how do you react?",
    "PHYSICAL_EDUCATION": "If a student hates sports class, how do you change their mind?",
    "NUTRITION_WELLNESS": "If a client refuses to eat healthy foods, how do you help them?",
    "YOGA_WELLNESS": "If a student struggles to stay calm during meditation, what do you suggest?",

    # Business & Management
    "BUSINESS_ADMIN": "If a team project is falling behind, how do you get things back on track?",
    "ENTREPRENEURSHIP": "If your first business idea fails completely, what do you do next?",
    "HUMAN_RESOURCES": "If two employees are in conflict, how do you help resolve it?",
    "OPERATIONS_MANAGEMENT": "If a delivery is delayed and customers are angry, how do you respond?",
    "PROJECT_MANAGEMENT": "If your project goes over budget, how do you handle the situation?",
    "BUSINESS_ANALYSIS": "If data shows your recommendation was wrong, how do you react?",
    "ACCOUNTING_FINANCE": "If you find a small accounting error from months ago, what do you do?",
    "FINANCIAL_ANALYSIS": "If your financial prediction is completely wrong, how do you learn from it?",
    "MARKETING_SALES": "If a campaign you created gets no response, how do you fix it?",
    "ADVERTISING": "If your ad is criticized by the public, how do you handle the feedback?",
    "PUBLIC_RELATIONS": "If your organization faces bad press, how do you respond?",
    "DIGITAL_MEDIA": "If your content gets negative comments, how do you handle it?",
    "EVENT_MANAGEMENT": "If bad weather ruins your outdoor event, what do you do?",
    "HOSPITALITY_MGMT": "If a guest complains loudly in front of others, how do you respond?",
    "CULINARY_ARTS": "If a customer sends their food back, how do you feel about it?",
    "TRAVEL_HOSP": "If a traveler's booking is lost, how do you make it right?",
    "TRANSPORT_LOG": "If a shipment is lost, how do you find a solution?",
    "SUPPLY_CHAIN": "If a supplier fails to deliver on time, what do you do?",
    "LOGISTICS": "If a delivery truck breaks down mid-route, how do you react?",
    "RAIL_TRANSPORT": "If a train is delayed and passengers are upset, how do you handle it?",
    "AVIATION_MGMT": "If a flight is cancelled at the last minute, what do you do?",
    "URBAN_PLANNING": "If residents reject your city plan, how do you respond?",

    # Social Sciences & Law
    "PSYCHOLOGY": "If a client cries during a session, how do you respond?",
    "COUNSELING_SERVICES": "If someone asks for advice on a topic you know little about, what do you do?",
    "SOCIAL_WORK": "If a family refuses help even though they need it, how do you handle it?",
    "LAW_JUSTICE": "If you believe your client is guilty but they ask you to defend them, how do you feel?",
    "POLICE_CRIMINOLOGY": "If a witness changes their story, how do you investigate further?",
    "GOVERNMENT_POLICY": "If a policy you helped create hurts the people it was meant to help, what do you do?",
    "INTERNATIONAL_RELATIONS": "If two countries you work with are in conflict, how do you proceed?",
    "ECONOMICS": "If your economic forecast is wrong, how do you adjust your thinking?",
    "SOCIOLOGY": "If a community you study does not trust your research, how do you respond?",
    "ANTHROPOLOGY": "If your cultural observations offend someone, how do you handle it?",
    "ARCHAEOLOGY": "If a precious artifact breaks during excavation, how do you feel?",
    "PHILOSOPHY": "If someone strongly disagrees with your worldview, how do you discuss it?",
    "THEOLOGY": "If your beliefs are questioned, how do you respond?",
    "LINGUISTICS": "If you make a mistake while translating for someone, what do you do?",
    "LIBRARY_SCIENCE": "If a student cannot find what they are looking for, how do you help?",
    "EDUCATION_TEACHING": "If a student is not interested in your class, how do you reach them?",
    "SPECIAL_EDUCATION": "If a child with special needs is struggling, how do you adapt your approach?",
    "EARLY_CHILDHOOD": "If a toddler has a meltdown, how do you calm them down?",
    "SPORTS_MANAGEMENT_EDU": "If PE students are not participating, how do you engage them?",

    # Creative Arts & Media
    "FINE_ARTS": "If someone says your art is meaningless, how do you feel?",
    "PERFORMING_ARTS": "If you forget your lines on stage, how do you recover?",
    "MUSIC": "If you make a mistake during a performance, how do you handle it?",
    "DANCE": "If you cannot get a dance move right after many tries, what do you do?",
    "FILM_PHOTOGRAPHY": "If your footage is ruined after a long shoot, how do you react?",
    "GRAPHIC_DESIGN": "If a client rejects your design completely, how do you respond?",
    "FASHION_DESIGN": "If your fashion collection is criticized, how do you handle it?",
    "INTERIOR_DESIGN": "If a client hates your room design, what do you do next?",
    "ARCHITECTURE": "If a building you designed has structural issues, how do you feel?",
    "CREATIVE_WRITING": "If your story is rejected by publishers, how do you keep writing?",
    "JOURNALISM": "If you discover your source gave you wrong information, what do you do?",
    "CONTENT_CREATION": "If your video gets negative comments, how do you handle it?",
    "GAME_DESIGN": "If players hate a game feature you created, how do you improve it?",
    "ANIMATION": "If your animation takes weeks but looks wrong, how do you feel about redoing it?",
    "UX_DESIGN": "If users cannot figure out your design, how do you fix it?",

    # Agriculture & Environment
    "AGRICULTURE_FARMING": "If your crop fails due to bad weather, how do you plan for next season?",
    "FORESTRY": "If you find illegal logging in a protected forest, what do you do?",
    "FISHERIES": "If fish populations drop in the area you manage, how do you respond?",
    "VETERINARY_SCIENCE": "If an animal you are treating does not survive, how do you cope?",
    "DAIRY_TECHNOLOGY": "If milk quality drops at your facility, how do you fix the problem?",
    "FOOD_TECHNOLOGY": "If a new food product tastes bad, how do you improve it?",
    "HORTICULTURE": "If your garden plants get a disease, how do you save them?",
    "AGRICULTURAL_ENG": "If your irrigation system fails during a dry season, what do you do?",

    # Technology & Trades
    "COMPUTER_SCIENCE": "If your algorithm is too slow for real-world use, how do you improve it?",
    "IT_NETWORKING": "If a network goes down at a critical time, how do you troubleshoot?",
    "CLOUD_COMPUTING": "If cloud services go down and users cannot access data, what do you do?",
    "BLOCKCHAIN": "If you find a security flaw in a blockchain system, how do you report it?",
    "IOT_EMBEDDED": "If a smart device stops responding, how do you diagnose the issue?",
    "CONSTRUCTION_MGMT": "If a building material is not delivered on time, how do you keep the project moving?",
    "SURVEYING_GEO": "If your survey measurements are inaccurate, how do you correct them?",
    "ENVIRONMENTAL_ENG": "If a clean-up project causes unexpected pollution, how do you respond?",
    "CHEMICAL_ENG": "If a chemical reaction in your plant is unsafe, what do you do?",
    "BIOMEDICAL_ENG": "If a medical device you helped design fails during testing, how do you react?",
    "PETROCHEMICAL_ENG": "If there is a safety concern at a plant, how do you handle it?",
    "MINING_ENG": "If a mining operation risks environmental damage, what do you do?",
    "MARINE_ENG": "If a ship's engine fails mid-journey, how do you respond?",
    "TEXTILE_ENG": "If fabric quality is poor, how do you find the root cause?",
    "AUTOMOBILE_ENG": "If a car design has a safety flaw, how do you handle the responsibility?",
    "PRINTING_TECH": "If a print job has color errors, how do you fix the process?",
}

# Keep this catalog aligned with the active child domains in domain_hierarchy.csv.
UNIQUE_PERSONALITY_QUESTIONS.update(
    {
        "ACCOUNTING": "If you find a small accounting error from months ago, what do you do?",
        "ACTUARIAL_SCIENCE": "If your risk model misses an important possibility, how do you improve it?",
        "AGRICULTURE": "If your crop fails due to bad weather, how do you plan for next season?",
        "AIRLINE_SERVICES": "If a passenger is stressed after a cancelled flight, how do you help?",
        "ANIMAL_SCIENCE": "If an animal under your care is not improving, how do you decide what to try next?",
        "AUDITING": "If you find a financial irregularity that others want to ignore, how do you respond?",
        "AUTOMOBILE_MANUFACTURING": "If a vehicle component fails a safety check, how do you handle the problem?",
        "AVIATION": "If a flight operation faces a last-minute delay, how do you keep people informed and organized?",
        "BANKING": "If a customer is upset about a banking issue you cannot fix immediately, how do you handle it?",
        "BRAND_MANAGEMENT": "If customers start losing trust in a brand, how would you help rebuild it?",
        "BROADCASTING": "If a live broadcast goes off plan, how do you stay composed?",
        "BUILDING_SAFETY": "If an inspection reveals a safety concern others overlooked, how do you respond?",
        "CHILD_FAMILY_SERVICES": "If a family is hesitant to accept support, how would you build trust?",
        "CIVIL_ENGINEERING": "If a construction design faces an unexpected site problem, how do you adjust?",
        "CIVIL_SERVICES": "If a public-service decision helps some people but creates difficulty for others, how do you respond?",
        "COMMUNICATIONS": "If your message is misunderstood by a large audience, how do you correct it?",
        "COMMUNITY_DEVELOPMENT": "If a community does not agree on its biggest priority, how do you move forward?",
        "CONSTRUCTION_MANAGEMENT": "If building materials are not delivered on time, how do you keep the project moving?",
        "CONTENT_WRITING": "If your writing is heavily edited, how do you respond to the feedback?",
        "CRIMINAL_JUSTICE": "If two accounts of an incident conflict, how do you work toward the truth?",
        "DEFENSE_SERVICES": "If a difficult situation requires discipline under pressure, how do you stay focused?",
        "DIGITAL_MARKETING": "If an online campaign gets clicks but no real results, what would you test next?",
        "DISABILITY_SERVICES": "If someone faces a barrier that others overlook, how would you advocate for them?",
        "EARLY_CHILDHOOD_EDU": "If a young child has a meltdown during class, how do you calm the situation?",
        "EDITING_PUBLISHING": "If you spot a major error just before publication, what do you do?",
        "EDUCATION_ADMIN": "If teachers and parents disagree about a school decision, how do you handle it?",
        "EDUCATION_COUNSELING": "If a student feels lost about their future, how do you help them find a direction?",
        "EMERGENCY_MANAGEMENT": "If an emergency plan fails during a real crisis, how do you respond?",
        "ENVIRONMENTAL_CONSERVATION": "If people ignore your conservation advice, how do you respond?",
        "E_COMMERCE": "If customers leave your online store before buying, how would you investigate the problem?",
        "FILM_VIDEO_PRODUCTION": "If your footage is ruined after a long shoot, how do you react?",
        "FINANCIAL_PLANNING": "If a client's financial goals are unrealistic, how do you guide the conversation?",
        "FIRE_SAFETY": "If people ignore an important fire-safety rule, what do you do?",
        "FOOD_PROCESSING": "If a production batch fails a quality check, what do you do next?",
        "FOOD_SCIENCE": "If a new food product fails a quality test, how do you improve it?",
        "FORENSIC_SCIENCE": "If evidence does not support the obvious explanation, how do you approach the case?",
        "GOVT_BANKING": "If citizens are confused by a government banking process, how do you help clarify it?",
        "HIGHER_EDUCATION": "If college students are disengaged from a topic, how would you make it relevant?",
        "HOSPITALITY_OPERATIONS": "If several guests need help at the same time, how do you prioritize them?",
        "HOTEL_MANAGEMENT": "If a guest complains loudly in front of others, how do you respond?",
        "INDUSTRIAL_ENGINEERING": "If a production process wastes time and materials, how would you improve it?",
        "INSURANCE": "If a customer is confused by policy details, how do you explain the trade-offs clearly?",
        "INTERIOR_ARCHITECTURE": "If a space looks good but does not work well for users, how would you improve it?",
        "INVESTMENT_MANAGEMENT": "If an investment performs poorly during a market downturn, how do you review your decision?",
        "LANDSCAPE_ARCHITECTURE": "If a landscape plan is affected by water limitations, how would you adapt it?",
        "LAW": "If you believe your client is guilty but they ask you to defend them, how do you feel?",
        "LEGAL_SERVICES": "If someone needs legal help but does not understand the process, how do you guide them?",
        "MAINTENANCE_TECH": "If equipment stops working during a busy shift, how do you approach the repair?",
        "MANAGEMENT_CONSULTING": "If a client rejects your recommendation after weeks of analysis, what do you do next?",
        "MANUFACTURING_TECH": "If a machine repeatedly produces faulty items, how do you find the cause?",
        "MARITIME_TRANSPORT": "If a shipping delay affects several customers, how do you manage the situation?",
        "MARKET_RESEARCH": "If customer interviews challenge your original assumption, how do you respond?",
        "MEDIA_PRODUCTION": "If a production falls behind schedule, how do you keep the work moving?",
        "MEDIA_RELATIONS": "If a public statement creates confusion, how do you repair communication?",
        "NATURAL_RESOURCES": "If a community depends on a resource that is running low, how would you help plan its use?",
        "NGO_MANAGEMENT": "If an important community project has limited resources, how do you decide what to prioritize?",
        "OFFICE_ADMINISTRATION": "If several urgent requests arrive at once, how do you decide what to handle first?",
        "PHOTOGRAPHY": "If an important photo shoot does not turn out as planned, how do you adapt?",
        "PLANT_SCIENCE": "If plants in your study develop an unexpected disease, how do you investigate?",
        "POLICE_SERVICES": "If a witness changes their story, how do you investigate further?",
        "PRODUCTION_MANAGEMENT": "If output is falling behind schedule, how do you restore the plan?",
        "PRODUCT_DESIGN": "If users struggle with a product you designed, how would you improve it?",
        "PUBLIC_ADMINISTRATION": "If a public program is not reaching the people who need it, what do you do?",
        "PUBLIC_SAFETY": "If a safety measure is unpopular but necessary, how do you explain its importance?",
        "PUBLIC_SECTOR_UNITS": "If an important public-sector process is inefficient, how would you improve it?",
        "QUALITY_CONTROL": "If you find a quality issue shortly before shipment, how do you respond?",
        "RAILWAY_JOBS": "If passengers are affected by an operational issue, how do you respond under pressure?",
        "REAL_ESTATE": "If a client wants a property that does not fit their needs, how do you advise them?",
        "RURAL_DEVELOPMENT": "If a rural community is skeptical of a new initiative, how do you build trust?",
        "SALES": "If a potential customer repeatedly says no, how do you decide whether to keep trying?",
        "SCHOOL_EDUCATION": "If a school student is falling behind, how would you support them?",
        "SOCIAL_MEDIA_MARKETING": "If a social media post receives negative reactions, how do you respond?",
        "SOCIAL_WORK_FIELD": "If a family refuses help even though they need it, how do you handle it?",
        "STATE_GOVT_SERVICES": "If a citizen has been waiting too long for help, how do you handle the situation?",
        "SUSTAINABILITY": "If a sustainable solution costs more at first, how would you explain its value?",
        "TAXATION": "If tax rules change close to a filing deadline, how do you adjust your work?",
        "TEACHING": "If a student is not interested in your class, how do you reach them?",
        "TEXTILE_MANUFACTURING": "If fabric quality is inconsistent, how do you find the root cause?",
        "TOURISM_MANAGEMENT": "If visitors are disappointed by a tour experience, how would you improve it?",
        "TRAINING_DEVELOPMENT": "If employees are not applying what they learned in training, how do you improve it?",
        "TRANSPORTATION_MANAGEMENT": "If a transport plan is causing repeated delays, how would you improve it?",
        "TRAVEL_SERVICES": "If a traveler's booking is lost, how do you make it right?",
        "UX_UI_DESIGN": "If users cannot figure out your interface, how do you fix it?",
        "VISUAL_ARTS": "If someone says your artwork has no meaning, how do you respond?",
        "WAREHOUSING": "If stock records do not match the items in a warehouse, how do you investigate?",
    }
)

LEGACY_PERSONALITY_QUESTION_TEXTS: set[str] = set()

for legacy_domain_code in (
    "ACCOUNTING_FINANCE",
    "AGRICULTURAL_ENG",
    "AGRICULTURE_FARMING",
    "ANTHROPOLOGY",
    "ARCHAEOLOGY",
    "AUTOMOBILE_ENG",
    "AVIATION_MGMT",
    "BIOMEDICAL_ENG",
    "BLOCKCHAIN",
    "CHEMICAL_ENG",
    "CLOUD_COMPUTING",
    "COMPUTER_SCIENCE",
    "CONSTRUCTION_MGMT",
    "CONTENT_CREATION",
    "CREATIVE_WRITING",
    "DAIRY_TECHNOLOGY",
    "DIGITAL_MEDIA",
    "EARLY_CHILDHOOD",
    "ECONOMICS",
    "EDUCATION_TEACHING",
    "ENVIRONMENTAL_ENG",
    "FILM_PHOTOGRAPHY",
    "FINE_ARTS",
    "FOOD_TECHNOLOGY",
    "GAME_DESIGN",
    "GOVERNMENT_POLICY",
    "HORTICULTURE",
    "HOSPITALITY_MGMT",
    "INTERNATIONAL_RELATIONS",
    "IOT_EMBEDDED",
    "IT_NETWORKING",
    "LAW_JUSTICE",
    "LIBRARY_SCIENCE",
    "LINGUISTICS",
    "MARINE_ENG",
    "MARKETING_SALES",
    "MINING_ENG",
    "PETROCHEMICAL_ENG",
    "PHILOSOPHY",
    "POLICE_CRIMINOLOGY",
    "PRINTING_TECH",
    "PSYCHOLOGY",
    "SOCIAL_WORK",
    "SOCIOLOGY",
    "SPORTS_MANAGEMENT_EDU",
    "SURVEYING_GEO",
    "TEXTILE_ENG",
    "THEOLOGY",
    "TRANSPORT_LOG",
    "TRAVEL_HOSP",
    "UX_DESIGN",
    "VETERINARY_SCIENCE",
):
    legacy_question_text = UNIQUE_PERSONALITY_QUESTIONS.pop(legacy_domain_code, None)
    if legacy_question_text:
        LEGACY_PERSONALITY_QUESTION_TEXTS.add(legacy_question_text)

# A renamed domain may intentionally reuse its original question text.
LEGACY_PERSONALITY_QUESTION_TEXTS.difference_update(
    UNIQUE_PERSONALITY_QUESTIONS.values()
)


class Command(BaseCommand):
    help = "Seed free-text questions (mapped to all child domains) + unique personality questions."

    def handle(self, **options):
        child_domains = list(
            Domain.objects.filter(is_active=True, deleted=False, parent__isnull=False)
        )

        if not child_domains:
            self.stdout.write(self.style.WARNING("No child domains found. Aborting."))
            return

        self._deactivate_stale_personality_questions()
        self._deactivate_retired_free_text_questions()
        self._seed_free_text_questions(child_domains)
        self._seed_unique_personality_questions(child_domains)

        self.stdout.write(self.style.SUCCESS("Done seeding questions."))

    # ------------------------------------------------------------------
    #  Free-text questions (mapped to ALL child domains)
    # ------------------------------------------------------------------
    @transaction.atomic
    def _seed_free_text_questions(self, child_domains: list[Domain]):
        created = 0
        for ftq in FREE_TEXT_QUESTIONS:
            question, was_created = Question.objects.get_or_create(
                question_text=ftq["question_text"],
                dimension=ftq["dimension"],
                question_type=ftq["question_type"],
                defaults={
                    "sequence_order": ftq["sequence_order"],
                    "signal_strength": ftq["signal_strength"],
                    "is_active": True,
                },
            )
            question.mapped_domains.set(child_domains)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} free-text question(s)."))

    # ------------------------------------------------------------------
    #  Retired free-text questions
    # ------------------------------------------------------------------
    @transaction.atomic
    def _deactivate_retired_free_text_questions(self):
        questions = Question.objects.filter(
            question_text__in=RETIRED_FREE_TEXT_QUESTION_TEXTS,
            question_type="text",
            is_active=True,
        )
        retired_count = questions.count()
        if retired_count:
            for question in questions:
                question.mapped_domains.clear()
            questions.update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deactivated {retired_count} retired free-text question(s)."
            )
        )

    # ------------------------------------------------------------------
    #  Retired personality questions from old domain codes
    # ------------------------------------------------------------------
    @transaction.atomic
    def _deactivate_stale_personality_questions(self):
        questions = Question.objects.filter(
            question_text__in=LEGACY_PERSONALITY_QUESTION_TEXTS,
            dimension="personality",
            question_type="mcq",
        )
        stale_count = questions.count()
        if stale_count:
            for question in questions:
                question.mapped_domains.clear()
            questions.update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deactivated {stale_count} retired personality question(s)."
            )
        )

    # ------------------------------------------------------------------
    #  1 unique personality question per child domain
    # ------------------------------------------------------------------
    @transaction.atomic
    def _seed_unique_personality_questions(self, child_domains: list[Domain]):
        created = 0
        for domain in child_domains:
            q_text = UNIQUE_PERSONALITY_QUESTIONS.get(domain.domain_code)
            if not q_text:
                continue

            question, was_created = Question.objects.get_or_create(
                question_text=q_text,
                dimension="personality",
                question_type="mcq",
                defaults={
                    "sequence_order": 3,
                    "signal_strength": 5,
                    "is_active": True,
                },
            )
            question.mapped_domains.set([domain])
            for i, text in enumerate(
                [
                    "I may stop if it feels too hard",
                    "I would continue with guidance",
                    "I would break it down and keep trying",
                    "I enjoy working through difficult learning",
                ],
                start=1,
            ):
                Option.objects.get_or_create(
                    question=question,
                    sequence_order=i,
                    defaults={"option_text": text},
                )

            if was_created:
                created += 1

        if created:
            self.stdout.write(f"  Created {created} new personality question(s).")
        else:
            self.stdout.write("  All personality questions already exist (0 new).")
