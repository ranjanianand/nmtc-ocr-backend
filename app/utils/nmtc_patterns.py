"""
NMTC Document Type Identification Patterns
This module contains patterns and rules for identifying different types of NMTC documents
based on text content, structure, and key terminology.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class NMTCDocumentType(str, Enum):
    """NMTC Document Types based on your seed data"""
    ALLOCATION_AGREEMENT = "allocation_agreement"
    QLICI_LOAN = "qlici_loan"
    QALICB_CERTIFICATION = "qalicb_certification"
    COMMUNITY_BENEFITS_AGREEMENT = "cba"
    ANNUAL_COMPLIANCE_REPORT = "annual_compliance_report"
    FINANCIAL_STATEMENT = "financial_statement"
    PROMISSORY_NOTE = "promissory_note"
    INSURANCE_DOCUMENT = "insurance"
    UNKNOWN = "unknown"


@dataclass
class PatternMatch:
    """Represents a pattern match with confidence"""
    pattern_type: str
    match_text: str
    confidence: float
    location: str  # Where in document the match was found
    context: str   # Surrounding text for context


@dataclass
class DocumentTypeResult:
    """Result of document type detection"""
    document_type: NMTCDocumentType
    confidence: float
    primary_indicators: List[PatternMatch]
    secondary_indicators: List[PatternMatch]
    metadata: Dict[str, Any]
    reasoning: str


class NMTCPatterns:
    """NMTC document identification patterns"""
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for better performance"""
        self.compiled_patterns = {}
        
        for doc_type, patterns in self.DOCUMENT_PATTERNS.items():
            self.compiled_patterns[doc_type] = {}
            
            for pattern_type, pattern_list in patterns.items():
                if isinstance(pattern_list, list):
                    self.compiled_patterns[doc_type][pattern_type] = [
                        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                        for pattern in pattern_list
                    ]
                else:
                    self.compiled_patterns[doc_type][pattern_type] = re.compile(
                        pattern_list, re.IGNORECASE | re.MULTILINE
                    )
    
    # Document identification patterns
    DOCUMENT_PATTERNS = {
        NMTCDocumentType.ALLOCATION_AGREEMENT: {
            'title_patterns': [
                r'allocation\s+agreement',
                r'new\s+markets\s+tax\s+credit\s+allocation\s+agreement',
                r'nmtc\s+allocation\s+agreement',
                r'tax\s+credit\s+allocation\s+agreement'
            ],
            'key_terms': [
                r'qualified\s+equity\s+investment',
                r'qei\s+amount',
                r'cde\s+allocation',
                r'cdfi\s+fund',
                r'allocation\s+amount',
                r'7\s+year\s+compliance\s+period',
                r'recapture\s+event',
                r'qualified\s+low-income\s+community\s+investment',
                r'qlici'
            ],
            'structural_patterns': [
                r'section\s+\d+(\.\d+)*\.\s*qualified\s+equity\s+investment',
                r'schedule\s+[a-zA-Z]\s*-\s*allocation\s+details',
                r'exhibit\s+[a-zA-Z]\s*-.*allocation',
                r'compliance\s+period\s+begins',
                r'initial\s+investment\s+date'
            ]
        },
        
        NMTCDocumentType.QLICI_LOAN: {
            'title_patterns': [
                r'qualified\s+low-income\s+community\s+investment\s+loan\s+agreement',
                r'qlici\s+loan\s+agreement',
                r'qualified\s+low.income\s+community\s+investment',
                r'qlici\s+loan\s+and\s+security\s+agreement'
            ],
            'key_terms': [
                r'qualified\s+active\s+low-income\s+community\s+business',
                r'qalicb',
                r'substantially\s+all\s+test',
                r'70%.*income\s+test',
                r'40%.*property\s+test',
                r'qualified\s+low-income\s+community\s+investment',
                r'qlici',
                r'loan\s+principal',
                r'interest\s+rate',
                r'maturity\s+date'
            ],
            'financial_patterns': [
                r'\$[\d,]+\.?\d*\s+principal\s+amount',
                r'\d+(\.\d+)?%\s+per\s+annum',
                r'interest.*rate.*\d+(\.\d+)?%',
                r'loan\s+amount.*\$[\d,]+',
                r'principal.*\$[\d,]+',
                r'maturity.*\d{1,2}/\d{1,2}/\d{4}'
            ]
        },
        
        NMTCDocumentType.QALICB_CERTIFICATION: {
            'title_patterns': [
                r'qualified\s+active\s+low-income\s+community\s+business\s+certification',
                r'qalicb\s+certification',
                r'qalicb\s+certificate',
                r'qualified\s+active\s+low.income\s+community\s+business'
            ],
            'key_terms': [
                r'substantially\s+all\s+test',
                r'qualified\s+business',
                r'low-income\s+community',
                r'census\s+tract',
                r'median\s+family\s+income',
                r'poverty\s+rate',
                r'qualifying\s+business\s+activities',
                r'40%.*property\s+test',
                r'70%.*income\s+test'
            ],
            'certification_patterns': [
                r'hereby\s+certifies?\s+that',
                r'certification\s+is\s+valid',
                r'certification\s+period',
                r'effective\s+date\s+of\s+certification',
                r'this\s+certification\s+shall\s+remain'
            ]
        },
        
        NMTCDocumentType.COMMUNITY_BENEFITS_AGREEMENT: {
            'title_patterns': [
                r'community\s+benefits?\s+agreement',
                r'community\s+development\s+agreement',
                r'cba',
                r'community\s+impact\s+agreement'
            ],
            'key_terms': [
                r'community\s+benefits?',
                r'local\s+hiring',
                r'job\s+creation',
                r'workforce\s+development',
                r'affordable\s+housing',
                r'community\s+impact',
                r'local\s+procurement',
                r'minority.*business\s+enterprise',
                r'disadvantaged\s+business\s+enterprise'
            ],
            'commitment_patterns': [
                r'agrees?\s+to\s+provide',
                r'commits?\s+to',
                r'shall\s+ensure',
                r'minimum\s+of\s+\d+%',
                r'target\s+of\s+\d+%',
                r'shall\s+hire\s+at\s+least'
            ]
        },
        
        NMTCDocumentType.ANNUAL_COMPLIANCE_REPORT: {
            'title_patterns': [
                r'annual\s+compliance\s+report',
                r'nmtc\s+compliance\s+report',
                r'annual\s+nmtc\s+report',
                r'compliance\s+monitoring\s+report'
            ],
            'key_terms': [
                r'compliance\s+period',
                r'qualified\s+equity\s+investments?',
                r'substantially\s+all\s+test',
                r'qalicb\s+status',
                r'community\s+impact\s+metrics',
                r'jobs\s+created',
                r'jobs\s+retained',
                r'recapture\s+event',
                r'non-compliance'
            ],
            'reporting_patterns': [
                r'for\s+the\s+year\s+ended',
                r'reporting\s+period',
                r'as\s+of\s+\w+\s+\d{1,2},?\s+\d{4}',
                r'annual\s+certification',
                r'compliance\s+status'
            ]
        },
        
        NMTCDocumentType.FINANCIAL_STATEMENT: {
            'title_patterns': [
                r'financial\s+statements?',
                r'audited\s+financial\s+statements?',
                r'balance\s+sheet',
                r'income\s+statement',
                r'statement\s+of.*operations',
                r'cash\s+flow\s+statement'
            ],
            'key_terms': [
                r'assets',
                r'liabilities',
                r'equity',
                r'revenue',
                r'expenses',
                r'net\s+income',
                r'cash\s+flows?',
                r'operating\s+activities',
                r'financing\s+activities',
                r'investing\s+activities'
            ],
            'financial_patterns': [
                r'\$\s*[\d,]+\.?\d*\s*\(\d+\)',  # Financial amounts
                r'total\s+assets.*\$[\d,]+',
                r'total\s+liabilities.*\$[\d,]+',
                r'net\s+income.*\$[\d,]+',
                r'for\s+the\s+years?\s+ended',
                r'december\s+31,\s+\d{4}'
            ]
        },
        
        NMTCDocumentType.PROMISSORY_NOTE: {
            'title_patterns': [
                r'promissory\s+note',
                r'secured\s+promissory\s+note',
                r'unsecured\s+promissory\s+note'
            ],
            'key_terms': [
                r'principal\s+sum',
                r'interest\s+rate',
                r'maturity\s+date',
                r'maker',
                r'payee',
                r'payment\s+terms',
                r'default',
                r'acceleration',
                r'collateral'
            ],
            'legal_patterns': [
                r'for\s+value\s+received',
                r'hereby\s+promises?\s+to\s+pay',
                r'on\s+demand\s+or',
                r'with\s+interest\s+at',
                r'event\s+of\s+default'
            ]
        },
        
        NMTCDocumentType.INSURANCE_DOCUMENT: {
            'title_patterns': [
                r'certificate\s+of\s+insurance',
                r'insurance\s+policy',
                r'evidence\s+of\s+insurance'
            ],
            'key_terms': [
                r'insured',
                r'insurer',
                r'policy\s+number',
                r'coverage\s+limits?',
                r'effective\s+date',
                r'expiration\s+date',
                r'premium',
                r'deductible'
            ],
            'insurance_patterns': [
                r'policy\s+#?\s*[\w\d-]+',
                r'limits?.*\$[\d,]+',
                r'effective.*\d{1,2}/\d{1,2}/\d{4}',
                r'expires?.*\d{1,2}/\d{1,2}/\d{4}'
            ]
        }
    }
    
    # Confidence scoring weights
    SCORING_WEIGHTS = {
        'title_patterns': 0.4,      # High weight for title matches
        'key_terms': 0.3,           # Medium-high weight for key terms
        'structural_patterns': 0.2,  # Medium weight for structure
        'financial_patterns': 0.15, # Medium weight for financial patterns
        'certification_patterns': 0.15,
        'commitment_patterns': 0.15,
        'reporting_patterns': 0.15,
        'legal_patterns': 0.15,
        'insurance_patterns': 0.15
    }
    
    # Minimum confidence thresholds
    MIN_CONFIDENCE_THRESHOLDS = {
        'high_confidence': 0.7,    # Very confident in classification
        'medium_confidence': 0.4,  # Moderately confident
        'low_confidence': 0.2      # Low confidence, needs human review
    }
    
    def get_document_patterns(self, doc_type: NMTCDocumentType) -> Dict[str, List[re.Pattern]]:
        """Get compiled patterns for a specific document type"""
        return self.compiled_patterns.get(doc_type, {})
    
    def get_all_document_types(self) -> List[NMTCDocumentType]:
        """Get all supported document types"""
        return [doc_type for doc_type in NMTCDocumentType if doc_type != NMTCDocumentType.UNKNOWN]


# Key field extraction patterns
NMTC_KEY_FIELDS = {
    'dates': {
        'patterns': [
            r'(?:effective|start|begin|commencement)\s+date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'(?:maturity|expiration|end)\s+date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'(?:initial|first)\s+investment\s+date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'compliance\s+period\s+begins?[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})'
        ],
        'field_type': 'date'
    },
    
    'amounts': {
        'patterns': [
            r'(?:allocation|qei)\s+amount[:\s]*\$?([\d,]+\.?\d*)',
            r'(?:loan|principal)\s+amount[:\s]*\$?([\d,]+\.?\d*)',
            r'total\s+(?:allocation|investment)[:\s]*\$?([\d,]+\.?\d*)'
        ],
        'field_type': 'currency'
    },
    
    'percentages': {
        'patterns': [
            r'interest\s+rate[:\s]*([\d.]+)%',
            r'(\d{1,2}(?:\.\d+)?)%\s+per\s+annum',
            r'substantially\s+all.*(\d{1,2})%'
        ],
        'field_type': 'percentage'
    },
    
    'entities': {
        'patterns': [
            r'(?:cde|community\s+development\s+entity)[:\s]*([A-Z].*?)(?:\n|$)',
            r'(?:qalicb|qualified.*business)[:\s]*([A-Z].*?)(?:\n|$)',
            r'(?:borrower|maker)[:\s]*([A-Z].*?)(?:\n|$)',
            r'(?:lender|payee)[:\s]*([A-Z].*?)(?:\n|$)'
        ],
        'field_type': 'entity'
    },
    
    'locations': {
        'patterns': [
            r'census\s+tract[:\s]*(\d+(?:\.\d+)?)',
            r'(?:state|located\s+in)[:\s]*([A-Z]{2})\b',
            r'(?:city|municipality)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ],
        'field_type': 'location'
    }
}


# Document structure indicators
DOCUMENT_STRUCTURE_INDICATORS = {
    'has_schedules': r'schedule\s+[a-zA-Z]\s*[-:]',
    'has_exhibits': r'exhibit\s+[a-zA-Z]\s*[-:]',
    'has_signatures': r'(?:signature|signed|executed).*(?:date|this)',
    'has_notarization': r'notary\s+public|acknowledged\s+before\s+me',
    'has_witness': r'witness.*signature|in\s+the\s+presence\s+of',
    'has_financial_tables': r'(?:total|subtotal).*\$[\d,]+\.?\d*',
    'has_legal_disclaimers': r'(?:disclaimer|limitation\s+of\s+liability)',
    'multi_party': r'(?:party|parties)\s+(?:of\s+the\s+)?(?:first|second|third)\s+part'
}


# Compliance and regulatory terms
COMPLIANCE_TERMS = {
    'nmtc_regulations': [
        'section 45d', 'treasury regulation', 'cdfi fund', 'notice 2004-83',
        'revenue ruling', 'nmtc program', 'qualified equity investment',
        'recapture event', 'compliance period'
    ],
    
    'financial_terms': [
        'substantially all test', 'working capital', 'tangible property',
        'qualified business', 'safe harbor', 'arm\'s length', 'fair market value'
    ],
    
    'geographic_terms': [
        'low-income community', 'census tract', 'median family income',
        'poverty rate', 'non-metropolitan area', 'targeted population'
    ]
}


def get_confidence_level_description(confidence: float) -> str:
    """Get human-readable confidence level description"""
    patterns = NMTCPatterns()
    
    if confidence >= patterns.MIN_CONFIDENCE_THRESHOLDS['high_confidence']:
        return "High - Very confident in document type classification"
    elif confidence >= patterns.MIN_CONFIDENCE_THRESHOLDS['medium_confidence']:
        return "Medium - Moderately confident, some indicators present"
    elif confidence >= patterns.MIN_CONFIDENCE_THRESHOLDS['low_confidence']:
        return "Low - Weak indicators, may need human review"
    else:
        return "Very Low - Insufficient indicators for reliable classification"