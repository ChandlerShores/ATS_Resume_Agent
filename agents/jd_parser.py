"""JD_PARSER agent: Extracts prioritized terms and competencies from job descriptions."""

import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer

from ops.llm_client import get_llm_client
from schemas.models import JDSignals

SYSTEM_PROMPT = """You are an expert at analyzing job descriptions and extracting key competencies, skills, and keywords.

Your task is to extract the most important terms that an ATS (Applicant Tracking System) would look for when matching a resume to this job description.

Prioritize:
1. Technical skills and tools
2. Domain expertise and certifications
3. Core competencies and soft skills
4. Industry-specific terminology

Group related terms and provide synonyms to improve matching flexibility."""


USER_PROMPT_TEMPLATE = """Extract and categorize ALL job description keywords from the following job description.

Job Description:
{jd_text}

Return a JSON object with this structure:
{{
  "top_terms": ["term1", "term2", ...],
  "weights": {{"term1": 1.0, "term2": 0.9, ...}},
  "synonyms": {{"term1": ["synonym1", "synonym2"], ...}},
  "themes": {{"theme1": ["term1", "term2"], ...}},
  "soft_skills": ["analytical thinking", "adaptability", ...],
  "hard_tools": ["Marketo", "Google Analytics", ...],
  "domain_terms": ["B2B healthcare", "SaaS", ...]
}}

Guidelines:
- top_terms: Up to 25 most important keywords/phrases
- weights: Importance score 0.0-1.0 (1.0 = must-have, 0.5 = nice-to-have)
- synonyms: Alternative terms that mean the same thing
- themes: Group related terms (e.g., "Technical Skills", "Soft Skills")

CATEGORIZE ALL KEYWORDS into three types:

1. soft_skills: ALL transferable competencies mentioned in JD that can be inferred from work
   Examples (not exhaustive): analytical thinking, problem-solving, communication, adaptability, 
   collaboration, attention to detail, curiosity, stakeholder management
   
2. hard_tools: ALL specific tools/platforms/technologies mentioned in JD (factual claims)
   Examples (not exhaustive): Marketo, Salesforce, Monday.com, Google Analytics, Figma, 
   Tableau, ChatGPT, PowerPoint, Excel
   
3. domain_terms: ALL industry/context terminology mentioned in JD
   Examples (not exhaustive): B2B healthcare, SaaS, multi-channel campaigns, demand generation,
   single-specialty care, patient engagement

IMPORTANT:
- Extract ALL keywords that fit each category, not just examples
- If unsure, categorize conservatively (prefer hard_tool over soft_skill)
- Hard tools are verifiable facts - flag anything with a brand name or specific product
- Domain terms will only be added to bullets if contextually grounded (in original or surrounding bullets)
"""


class JDParser:
    """Agent for parsing job descriptions and extracting signals."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
        self._spacy_model = None
        self._confidence_threshold = float(os.getenv("SPACY_CONFIDENCE_THRESHOLD", "0.7"))
        
        # Common technology/tool patterns
        self.tech_patterns = [
            r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|Swift|Kotlin)\b',
            r'\b(?:React|Angular|Vue|Node\.?js|Express|Django|Flask|Spring|Laravel)\b',
            r'\b(?:AWS|Azure|GCP|Google Cloud|Docker|Kubernetes|Terraform)\b',
            r'\b(?:SQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(?:Git|GitHub|GitLab|Jenkins|CI/CD|DevOps)\b',
            r'\b(?:Salesforce|HubSpot|Marketo|Pardot|Zapier|Monday\.com)\b',
            r'\b(?:Tableau|Power BI|Google Analytics|Mixpanel|Amplitude)\b',
            r'\b(?:Figma|Sketch|Adobe Creative Suite|Canva)\b',
        ]
        
        # Soft skill patterns
        self.soft_skill_patterns = [
            r'\b(?:leadership|teamwork|collaboration|communication|problem.?solving)\b',
            r'\b(?:analytical|critical thinking|attention to detail|adaptability)\b',
            r'\b(?:project management|time management|organizational|strategic)\b',
            r'\b(?:customer service|stakeholder management|cross.functional)\b',
        ]

    def _get_spacy_model(self):
        """Get spaCy model with lazy loading."""
        if self._spacy_model is None:
            try:
                import spacy
                self._spacy_model = spacy.load("en_core_web_sm")
            except OSError:
                from ops.logging import logger
                logger.warn(
                    stage="jd_parser",
                    msg="spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm"
                )
                self._spacy_model = False  # Mark as failed to avoid retries
        return self._spacy_model if self._spacy_model is not False else None

    def extract_signals_local(self, jd_text: str) -> tuple[JDSignals, float]:
        """
        Extract JD signals using local NLP processing (spaCy + TF-IDF).
        
        Args:
            jd_text: Normalized job description text
            
        Returns:
            Tuple of (JDSignals, confidence_score)
        """
        from ops.logging import logger
        
        # Initialize results
        top_terms = []
        weights = {}
        soft_skills = []
        hard_tools = []
        domain_terms = []
        confidence = 0.0
        
        try:
            # 1. Extract entities using spaCy
            spacy_model = self._get_spacy_model()
            if spacy_model:
                doc = spacy_model(jd_text)
                
                # Extract named entities and their types
                entities = []
                for ent in doc.ents:
                    if ent.label_ in ["ORG", "PRODUCT", "TECH", "SKILL"]:
                        entities.append(ent.text)
                
                # Extract noun phrases as potential terms
                noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
                
                # Combine and deduplicate
                all_terms = list(set(entities + noun_phrases))
                confidence += 0.3
                
            else:
                # Fallback: simple word extraction
                words = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b', jd_text)
                all_terms = list(set(words))
                confidence += 0.1
            
            # 2. Extract hard tools using regex patterns
            for pattern in self.tech_patterns:
                matches = re.findall(pattern, jd_text, re.IGNORECASE)
                hard_tools.extend([m.title() for m in matches])
            
            hard_tools = list(set(hard_tools))
            if hard_tools:
                confidence += 0.2
            
            # 3. Extract soft skills using regex patterns
            for pattern in self.soft_skill_patterns:
                matches = re.findall(pattern, jd_text, re.IGNORECASE)
                soft_skills.extend([m.replace('?', '').title() for m in matches])
            
            soft_skills = list(set(soft_skills))
            if soft_skills:
                confidence += 0.2
            
            # 4. TF-IDF for term importance
            if all_terms:
                try:
                    # Create corpus with JD text and common job terms
                    corpus = [jd_text]
                    vectorizer = TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=100,
                        stop_words='english'
                    )
                    tfidf_matrix = vectorizer.fit_transform(corpus)
                    feature_names = vectorizer.get_feature_names_out()
                    tfidf_scores = tfidf_matrix.toarray()[0]
                    
                    # Get top terms by TF-IDF score
                    term_scores = list(zip(feature_names, tfidf_scores, strict=False))
                    term_scores.sort(key=lambda x: x[1], reverse=True)
                    
                    top_terms = [term for term, score in term_scores[:25] if score > 0.1]
                    weights = {term: float(score) for term, score in term_scores if score > 0.1}
                    
                    if top_terms:
                        confidence += 0.3
                        
                except Exception as e:
                    logger.warn(
                        stage="jd_parser",
                        msg=f"TF-IDF processing failed: {e}"
                    )
            
            # 5. Extract domain terms (industry-specific terms)
            domain_patterns = [
                r'\b(?:B2B|B2C|SaaS|PaaS|IaaS|API|SDK|MVP|ROI|KPI)\b',
                r'\b(?:healthcare|fintech|e-commerce|retail|manufacturing)\b',
                r'\b(?:startup|enterprise|SMB|mid-market|enterprise)\b',
                r'\b(?:agile|scrum|waterfall|kanban|lean|devops)\b',
            ]
            
            for pattern in domain_patterns:
                matches = re.findall(pattern, jd_text, re.IGNORECASE)
                domain_terms.extend([m.upper() if len(m) <= 5 else m.title() for m in matches])
            
            domain_terms = list(set(domain_terms))
            if domain_terms:
                confidence += 0.1
            
            # Ensure we have at least some results
            if not top_terms and not hard_tools and not soft_skills:
                confidence = 0.0
            
            # Create JDSignals object
            signals = JDSignals(
                top_terms=top_terms[:25],
                weights=weights,
                synonyms={},  # Local extraction doesn't generate synonyms
                themes={},    # Local extraction doesn't generate themes
                soft_skills=soft_skills,
                hard_tools=hard_tools,
                domain_terms=domain_terms
            )
            
            logger.info(
                stage="jd_parser",
                msg=f"Local extraction completed with confidence {confidence:.2f}",
                top_terms_count=len(top_terms),
                hard_tools_count=len(hard_tools),
                soft_skills_count=len(soft_skills)
            )
            
            return signals, min(confidence, 1.0)
            
        except Exception as e:
            logger.warn(
                stage="jd_parser",
                msg=f"Local extraction failed: {e}"
            )
            # Return empty signals with 0 confidence
            return JDSignals(), 0.0


    def normalize_text(self, text: str) -> str:
        """
        Normalize text for processing.

        Args:
            text: Raw text

        Returns:
            str: Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove HTML tags if present
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def _llm_parse(self, jd_text: str) -> JDSignals:
        """Parse JD using LLM (fallback method)."""
        from ops.logging import logger
        
        logger.info(stage="jd_parser", msg="Using LLM fallback for JD parsing")
        
        # Call LLM to extract signals
        user_prompt = USER_PROMPT_TEMPLATE.format(jd_text=jd_text[:4000])  # Limit length

        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
        )

        # Convert to JDSignals model
        return JDSignals(
            top_terms=response.get("top_terms", [])[:25],  # Ensure max 25
            weights=response.get("weights", {}),
            synonyms=response.get("synonyms", {}),
            themes=response.get("themes", {}),
            soft_skills=response.get("soft_skills", []),
            hard_tools=response.get("hard_tools", []),
            domain_terms=response.get("domain_terms", []),
        )

    def parse(self, jd_text: str) -> JDSignals:
        """
        Parse job description and extract signals using hybrid approach.

        Args:
            jd_text: Job description text

        Returns:
            JDSignals: Extracted signals

        Raises:
            ValueError: If jd_text is empty
        """
        from ops.logging import logger
        
        if not jd_text:
            raise ValueError("jd_text must be provided")

        # Normalize
        normalized_jd = self.normalize_text(jd_text)

        # Try local extraction first
        signals, confidence = self.extract_signals_local(normalized_jd)
        
        # If confidence < threshold, use LLM fallback
        if confidence < self._confidence_threshold:
            logger.info(
                stage="jd_parser", 
                msg=f"Low confidence ({confidence:.2f}), using LLM fallback",
                confidence=confidence,
                threshold=self._confidence_threshold
            )
            signals = self._llm_parse(normalized_jd)
        else:
            logger.info(
                stage="jd_parser",
                msg=f"High confidence ({confidence:.2f}), using local extraction",
                confidence=confidence
            )
        
        return signals
