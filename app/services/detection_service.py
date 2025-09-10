"""
NMTC Document Type Detection Service
This service analyzes OCR text to identify NMTC document types and extract metadata.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import uuid

from app.utils.nmtc_patterns import (
    NMTCPatterns, 
    NMTCDocumentType, 
    PatternMatch, 
    DocumentTypeResult,
    NMTC_KEY_FIELDS,
    DOCUMENT_STRUCTURE_INDICATORS,
    COMPLIANCE_TERMS,
    get_confidence_level_description
)
from app.utils.exceptions import DocumentProcessingError
import logging

logger = logging.getLogger(__name__)


class NMTCDetectionService:
    """Service for detecting NMTC document types and extracting metadata"""
    
    def __init__(self):
        self.patterns = NMTCPatterns()
        logger.info("NMTC Detection Service initialized")
    
    def detect_document_type(
        self, 
        text_content: str, 
        document_id: Optional[uuid.UUID] = None,
        filename: Optional[str] = None
    ) -> DocumentTypeResult:
        """
        Detect the document type based on text content
        
        Args:
            text_content: OCR extracted text
            document_id: Optional document ID for logging
            filename: Optional filename for additional context
            
        Returns:
            DocumentTypeResult with classification and metadata
        """
        try:
            logger.info("Starting document type detection",
                                 document_id=str(document_id) if document_id else None,
                                 filename=filename,
                                 text_length=len(text_content))
            
            if not text_content or len(text_content.strip()) < 50:
                return self._create_unknown_result("Insufficient text content for classification")
            
            # Score each document type
            type_scores = {}
            all_matches = {}
            
            for doc_type in self.patterns.get_all_document_types():
                score, matches = self._score_document_type(text_content, doc_type)
                type_scores[doc_type] = score
                all_matches[doc_type] = matches
                
                logger.debug("Document type scoring",
                                      doc_type=doc_type.value,
                                      score=score,
                                      match_count=len(matches))
            
            # Find the best match
            best_type = max(type_scores, key=type_scores.get)
            best_score = type_scores[best_type]
            best_matches = all_matches[best_type]
            
            # If confidence is too low, return unknown
            min_threshold = self.patterns.MIN_CONFIDENCE_THRESHOLDS['low_confidence']
            if best_score < min_threshold:
                return self._create_unknown_result(
                    f"Low confidence score: {best_score:.3f} (threshold: {min_threshold})"
                )
            
            # Extract metadata based on document type
            metadata = self._extract_metadata(text_content, best_type, filename)
            
            # Create result
            result = DocumentTypeResult(
                document_type=best_type,
                confidence=best_score,
                primary_indicators=[m for m in best_matches if m.confidence > 0.5],
                secondary_indicators=[m for m in best_matches if m.confidence <= 0.5],
                metadata=metadata,
                reasoning=self._generate_reasoning(best_type, best_score, best_matches)
            )
            
            logger.info("Document type detection completed",
                                 document_id=str(document_id) if document_id else None,
                                 detected_type=best_type.value,
                                 confidence=best_score,
                                 primary_indicators=len(result.primary_indicators),
                                 secondary_indicators=len(result.secondary_indicators))
            
            return result
            
        except Exception as e:
            logger.error("Document type detection failed",
                                  document_id=str(document_id) if document_id else None,
                                  error=str(e))
            raise DocumentProcessingError(f"Document type detection failed: {e}", document_id)
    
    def _score_document_type(self, text_content: str, doc_type: NMTCDocumentType) -> Tuple[float, List[PatternMatch]]:
        """Score how well the text matches a specific document type"""
        patterns = self.patterns.get_document_patterns(doc_type)
        matches = []
        total_score = 0.0
        
        for pattern_category, pattern_list in patterns.items():
            category_weight = self.patterns.SCORING_WEIGHTS.get(pattern_category, 0.1)
            category_matches = []
            
            for pattern in pattern_list:
                pattern_matches = list(pattern.finditer(text_content))
                
                for match in pattern_matches:
                    # Calculate confidence based on match quality
                    match_confidence = self._calculate_match_confidence(match, text_content, pattern_category)
                    
                    # Get context around the match
                    context = self._extract_context(text_content, match.start(), match.end())
                    
                    pattern_match = PatternMatch(
                        pattern_type=pattern_category,
                        match_text=match.group(0),
                        confidence=match_confidence,
                        location=f"Position {match.start()}-{match.end()}",
                        context=context
                    )
                    
                    category_matches.append(pattern_match)
            
            # Score this category
            if category_matches:
                # Use the best match from this category
                best_match = max(category_matches, key=lambda m: m.confidence)
                category_score = best_match.confidence * category_weight
                total_score += category_score
                matches.extend(category_matches)
        
        return min(total_score, 1.0), matches  # Cap at 1.0
    
    def _calculate_match_confidence(self, match: re.Match, text_content: str, pattern_category: str) -> float:
        """Calculate confidence score for a specific pattern match"""
        base_confidence = 0.7
        
        # Adjust based on pattern category importance
        category_multipliers = {
            'title_patterns': 1.2,
            'key_terms': 1.0,
            'structural_patterns': 0.9,
            'financial_patterns': 0.8,
            'certification_patterns': 0.9,
            'commitment_patterns': 0.8,
            'reporting_patterns': 0.8,
            'legal_patterns': 0.8,
            'insurance_patterns': 0.8
        }
        
        multiplier = category_multipliers.get(pattern_category, 1.0)
        
        # Adjust based on match position (title matches are more important)
        match_position = match.start() / len(text_content) if text_content else 0
        if match_position < 0.1:  # First 10% of document
            position_bonus = 0.1
        elif match_position < 0.3:  # First 30%
            position_bonus = 0.05
        else:
            position_bonus = 0.0
        
        # Adjust based on match length (longer matches generally better)
        match_length = len(match.group(0))
        if match_length > 50:
            length_bonus = 0.1
        elif match_length > 20:
            length_bonus = 0.05
        else:
            length_bonus = 0.0
        
        final_confidence = min((base_confidence * multiplier) + position_bonus + length_bonus, 1.0)
        return final_confidence
    
    def _extract_context(self, text_content: str, start: int, end: int, context_size: int = 100) -> str:
        """Extract context around a match for better understanding"""
        context_start = max(0, start - context_size)
        context_end = min(len(text_content), end + context_size)
        
        context = text_content[context_start:context_end]
        
        # Clean up context
        context = re.sub(r'\s+', ' ', context).strip()
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text_content):
            context = context + "..."
        
        return context
    
    def _extract_metadata(self, text_content: str, doc_type: NMTCDocumentType, filename: Optional[str] = None) -> Dict[str, Any]:
        """Extract document-specific metadata"""
        metadata = {
            "detection_timestamp": datetime.utcnow().isoformat(),
            "filename": filename,
            "document_type": doc_type.value,
            "text_length": len(text_content),
            "extracted_fields": {},
            "structure_indicators": {},
            "compliance_terms": []
        }
        
        # Extract key fields
        metadata["extracted_fields"] = self._extract_key_fields(text_content)
        
        # Check document structure
        metadata["structure_indicators"] = self._check_document_structure(text_content)
        
        # Find compliance terms
        metadata["compliance_terms"] = self._find_compliance_terms(text_content)
        
        # Document type specific metadata
        if doc_type == NMTCDocumentType.ALLOCATION_AGREEMENT:
            metadata.update(self._extract_allocation_metadata(text_content))
        elif doc_type == NMTCDocumentType.QLICI_LOAN:
            metadata.update(self._extract_loan_metadata(text_content))
        elif doc_type == NMTCDocumentType.QALICB_CERTIFICATION:
            metadata.update(self._extract_certification_metadata(text_content))
        elif doc_type == NMTCDocumentType.FINANCIAL_STATEMENT:
            metadata.update(self._extract_financial_metadata(text_content))
        
        return metadata
    
    def _extract_key_fields(self, text_content: str) -> Dict[str, List[str]]:
        """Extract key fields like dates, amounts, entities"""
        extracted_fields = {}
        
        for field_category, field_config in NMTC_KEY_FIELDS.items():
            field_matches = []
            
            for pattern_str in field_config['patterns']:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                matches = pattern.findall(text_content)
                
                # Clean and deduplicate matches
                clean_matches = list(set([match.strip() for match in matches if match.strip()]))
                field_matches.extend(clean_matches)
            
            if field_matches:
                extracted_fields[field_category] = field_matches
        
        return extracted_fields
    
    def _check_document_structure(self, text_content: str) -> Dict[str, bool]:
        """Check for document structure indicators"""
        structure_indicators = {}
        
        for indicator_name, pattern_str in DOCUMENT_STRUCTURE_INDICATORS.items():
            pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            has_indicator = bool(pattern.search(text_content))
            structure_indicators[indicator_name] = has_indicator
        
        return structure_indicators
    
    def _find_compliance_terms(self, text_content: str) -> List[Dict[str, Any]]:
        """Find NMTC compliance and regulatory terms"""
        found_terms = []
        
        for category, terms in COMPLIANCE_TERMS.items():
            for term in terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                matches = list(pattern.finditer(text_content))
                
                if matches:
                    found_terms.append({
                        "category": category,
                        "term": term,
                        "count": len(matches),
                        "positions": [match.start() for match in matches]
                    })
        
        return found_terms
    
    def _extract_allocation_metadata(self, text_content: str) -> Dict[str, Any]:
        """Extract allocation agreement specific metadata"""
        return {
            "allocation_specific": {
                "has_qei_amount": bool(re.search(r'qei.*amount', text_content, re.IGNORECASE)),
                "has_compliance_period": bool(re.search(r'7.*year.*compliance', text_content, re.IGNORECASE)),
                "has_recapture_terms": bool(re.search(r'recapture', text_content, re.IGNORECASE)),
                "mentions_cdfi_fund": bool(re.search(r'cdfi.*fund', text_content, re.IGNORECASE))
            }
        }
    
    def _extract_loan_metadata(self, text_content: str) -> Dict[str, Any]:
        """Extract loan agreement specific metadata"""
        return {
            "loan_specific": {
                "has_principal_amount": bool(re.search(r'principal.*amount', text_content, re.IGNORECASE)),
                "has_interest_rate": bool(re.search(r'interest.*rate', text_content, re.IGNORECASE)),
                "has_maturity_date": bool(re.search(r'maturity.*date', text_content, re.IGNORECASE)),
                "mentions_qalicb_tests": bool(re.search(r'(?:70%|40%).*test', text_content, re.IGNORECASE)),
                "has_security_provisions": bool(re.search(r'security|collateral', text_content, re.IGNORECASE))
            }
        }
    
    def _extract_certification_metadata(self, text_content: str) -> Dict[str, Any]:
        """Extract QALICB certification specific metadata"""
        return {
            "certification_specific": {
                "has_census_tract": bool(re.search(r'census.*tract', text_content, re.IGNORECASE)),
                "mentions_income_test": bool(re.search(r'70%.*income', text_content, re.IGNORECASE)),
                "mentions_property_test": bool(re.search(r'40%.*property', text_content, re.IGNORECASE)),
                "has_certification_period": bool(re.search(r'certification.*period', text_content, re.IGNORECASE)),
                "mentions_substantially_all": bool(re.search(r'substantially.*all', text_content, re.IGNORECASE))
            }
        }
    
    def _extract_financial_metadata(self, text_content: str) -> Dict[str, Any]:
        """Extract financial statement specific metadata"""
        return {
            "financial_specific": {
                "has_balance_sheet": bool(re.search(r'balance.*sheet', text_content, re.IGNORECASE)),
                "has_income_statement": bool(re.search(r'income.*statement', text_content, re.IGNORECASE)),
                "has_cash_flow": bool(re.search(r'cash.*flow', text_content, re.IGNORECASE)),
                "has_audit_opinion": bool(re.search(r'(?:audit|opinion|independent)', text_content, re.IGNORECASE)),
                "mentions_fiscal_year": bool(re.search(r'(?:fiscal.*year|year.*ended)', text_content, re.IGNORECASE))
            }
        }
    
    def _generate_reasoning(self, doc_type: NMTCDocumentType, confidence: float, matches: List[PatternMatch]) -> str:
        """Generate human-readable reasoning for the classification"""
        confidence_desc = get_confidence_level_description(confidence)
        
        primary_matches = [m for m in matches if m.confidence > 0.5]
        secondary_matches = [m for m in matches if m.confidence <= 0.5]
        
        reasoning_parts = [
            f"Document classified as {doc_type.value.replace('_', ' ').title()} with {confidence:.1%} confidence.",
            f"Confidence Level: {confidence_desc}"
        ]
        
        if primary_matches:
            strong_indicators = list(set([m.pattern_type for m in primary_matches]))
            reasoning_parts.append(f"Strong indicators found: {', '.join(strong_indicators)}")
        
        if secondary_matches:
            weak_indicators = list(set([m.pattern_type for m in secondary_matches]))
            reasoning_parts.append(f"Supporting indicators: {', '.join(weak_indicators)}")
        
        # Add specific reasoning based on document type
        if doc_type == NMTCDocumentType.ALLOCATION_AGREEMENT:
            reasoning_parts.append("Key NMTC allocation terms and structures identified.")
        elif doc_type == NMTCDocumentType.QLICI_LOAN:
            reasoning_parts.append("QLICI loan terms and QALICB compliance requirements detected.")
        elif doc_type == NMTCDocumentType.QALICB_CERTIFICATION:
            reasoning_parts.append("QALICB certification language and compliance tests found.")
        
        return " ".join(reasoning_parts)
    
    def _create_unknown_result(self, reason: str) -> DocumentTypeResult:
        """Create a result for unknown/unclassifiable documents"""
        return DocumentTypeResult(
            document_type=NMTCDocumentType.UNKNOWN,
            confidence=0.0,
            primary_indicators=[],
            secondary_indicators=[],
            metadata={
                "detection_timestamp": datetime.utcnow().isoformat(),
                "classification_failed": True,
                "failure_reason": reason
            },
            reasoning=f"Document could not be classified: {reason}"
        )
    
    def get_supported_document_types(self) -> List[Dict[str, str]]:
        """Get list of supported document types with descriptions"""
        return [
            {
                "type": doc_type.value,
                "name": doc_type.value.replace('_', ' ').title(),
                "description": self._get_document_type_description(doc_type)
            }
            for doc_type in self.patterns.get_all_document_types()
        ]
    
    def _get_document_type_description(self, doc_type: NMTCDocumentType) -> str:
        """Get description for a document type"""
        descriptions = {
            NMTCDocumentType.ALLOCATION_AGREEMENT: "NMTC allocation agreement from CDE to investor",
            NMTCDocumentType.QLICI_LOAN: "Qualified Low-Income Community Investment loan agreement",
            NMTCDocumentType.QALICB_CERTIFICATION: "Qualified Active Low-Income Community Business certification",
            NMTCDocumentType.COMMUNITY_BENEFITS_AGREEMENT: "Community Benefits Agreement with local commitments",
            NMTCDocumentType.ANNUAL_COMPLIANCE_REPORT: "Annual NMTC compliance monitoring report",
            NMTCDocumentType.FINANCIAL_STATEMENT: "Audited financial statements",
            NMTCDocumentType.PROMISSORY_NOTE: "Promissory note or loan document",
            NMTCDocumentType.INSURANCE_DOCUMENT: "Insurance certificate or policy document"
        }
        return descriptions.get(doc_type, "NMTC-related document")


# Global service instance
detection_service = NMTCDetectionService()