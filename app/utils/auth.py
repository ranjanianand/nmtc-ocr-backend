from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
from app.models.database import *
from app.services.database_service import database_service
import logging
from datetime import datetime
import uuid
import json
import base64

logger = logging.getLogger(__name__)

# Initialize HTTP Bearer for JWT token authentication
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Authentication failed"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    """Authorization/permission denied"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail)


class UserContext:
    """Represents the current user's authentication and authorization context"""
    
    def __init__(
        self, 
        user_id: uuid.UUID, 
        email: str, 
        full_name: str = "",
        is_superadmin: bool = False, 
        jwt_claims: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.email = email
        self.full_name = full_name or email
        self.is_superadmin = is_superadmin
        self.jwt_claims = jwt_claims or {}
        self._organizations: Optional[List[Organization]] = None
        self._current_org: Optional[Organization] = None
        self._org_memberships: Dict[str, Dict[str, Any]] = {}

    async def get_organizations(self) -> List[Organization]:
        """Get all organizations the user belongs to"""
        if self._organizations is None:
            try:
                self._organizations = await database_service.get_organizations_by_user(self.user_id)
                logger.info(f"User {self.user_id} has access to {len(self._organizations)} organizations")
            except Exception as e:
                logger.error(f"Error getting organizations for user {self.user_id}: {e}")
                self._organizations = []
        return self._organizations

    async def set_current_organization(self, org_id: uuid.UUID):
        """Set the current organization context"""
        try:
            organizations = await self.get_organizations()
            org = next((o for o in organizations if o.id == org_id), None)
            
            if not org and not self.is_superadmin:
                raise AuthorizationError(f"User does not have access to organization {org_id}")
            
            # If superadmin, get org even if not a member
            if not org and self.is_superadmin:
                org = await database_service.get_organization(org_id)
                if not org:
                    raise AuthorizationError(f"Organization {org_id} not found")
            
            self._current_org = org
            await self._load_org_membership(org_id)
            logger.info(f"Set organization context for user {self.user_id} to org {org_id}")
        except Exception as e:
            logger.error(f"Error setting organization context: {e}")
            raise

    async def get_current_organization(self) -> Optional[Organization]:
        """Get the current organization context"""
        return self._current_org

    async def require_organization_context(self) -> Organization:
        """Require that an organization context is set"""
        if not self._current_org:
            raise AuthorizationError("Organization context is required for this operation")
        return self._current_org

    async def _load_org_membership(self, org_id: uuid.UUID):
        """Load user membership details for the organization"""
        try:
            if self.is_superadmin:
                # Superadmin has all permissions
                self._org_memberships[str(org_id)] = {
                    'role': 'owner',
                    'can_manage_users': True,
                    'can_view_billing': True,
                    'can_upload_documents': True,
                    'can_generate_reports': True,
                    'can_view_analytics': True,
                    'permissions': {}
                }
                return
            
            members = await database_service.get_org_members(org_id)
            user_member = next((m for m in members if m['user_id'] == str(self.user_id)), None)
            
            if user_member:
                # Get role details - in a real implementation, you'd join with user_roles table
                self._org_memberships[str(org_id)] = {
                    'role': user_member.get('role', 'viewer'),
                    'can_manage_users': user_member.get('role') in ['admin', 'owner'],
                    'can_view_billing': user_member.get('role') in ['admin', 'owner'], 
                    'can_upload_documents': True,  # Most roles can upload
                    'can_generate_reports': True,  # Most roles can generate reports
                    'can_view_analytics': user_member.get('role') in ['admin', 'owner'],
                    'permissions': {}
                }
            else:
                # Default viewer permissions
                self._org_memberships[str(org_id)] = {
                    'role': 'viewer',
                    'can_manage_users': False,
                    'can_view_billing': False,
                    'can_upload_documents': False,
                    'can_generate_reports': False,
                    'can_view_analytics': False,
                    'permissions': {}
                }
        except Exception as e:
            logger.error(f"Error loading org membership for user {self.user_id} in org {org_id}: {e}")
            # Default to minimal permissions on error
            self._org_memberships[str(org_id)] = {
                'role': 'viewer',
                'can_manage_users': False,
                'can_view_billing': False,
                'can_upload_documents': False,
                'can_generate_reports': False,
                'can_view_analytics': False,
                'permissions': {}
            }

    def has_organization_permission(self, permission: str, org_id: Optional[uuid.UUID] = None) -> bool:
        """Check if user has a specific permission in the organization"""
        if self.is_superadmin:
            return True
        
        org_id_str = str(org_id or (self._current_org.id if self._current_org else ''))
        if not org_id_str or org_id_str not in self._org_memberships:
            return False
        
        org_membership = self._org_memberships[org_id_str]
        return org_membership.get(permission, False)

    def get_organization_role(self, org_id: Optional[uuid.UUID] = None) -> str:
        """Get user's role in the organization"""
        if self.is_superadmin:
            return 'owner'
        
        org_id_str = str(org_id or (self._current_org.id if self._current_org else ''))
        if not org_id_str or org_id_str not in self._org_memberships:
            return 'viewer'
        
        return self._org_memberships[org_id_str].get('role', 'viewer')

    def can_access_document(self, document: Document) -> bool:
        """Check if user can access a specific document"""
        if self.is_superadmin:
            return True
        
        # Must be in the same organization as the document
        if not self._current_org or document.org_id != self._current_org.id:
            return False
        
        return True

    def can_modify_document(self, document: Document) -> bool:
        """Check if user can modify a specific document"""
        if self.is_superadmin:
            return True
        
        if not self.can_access_document(document):
            return False
        
        # Check if user has upload permission (implies modify)
        return self.has_organization_permission('can_upload_documents')

    def can_manage_obligations(self, org_id: Optional[uuid.UUID] = None) -> bool:
        """Check if user can manage obligations"""
        if self.is_superadmin:
            return True
        
        role = self.get_organization_role(org_id)
        return role in ['admin', 'owner'] or self.has_organization_permission('can_generate_reports', org_id)

    def can_view_org_billing(self, org_id: Optional[uuid.UUID] = None) -> bool:
        """Check if user can view organization billing information"""
        if self.is_superadmin:
            return True
        
        return self.has_organization_permission('can_view_billing', org_id)

    def can_manage_org_users(self, org_id: Optional[uuid.UUID] = None) -> bool:
        """Check if user can manage organization users"""
        if self.is_superadmin:
            return True
        
        return self.has_organization_permission('can_manage_users', org_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user context to dictionary for serialization"""
        return {
            'user_id': str(self.user_id),
            'email': self.email,
            'full_name': self.full_name,
            'is_superadmin': self.is_superadmin,
            'current_org_id': str(self._current_org.id) if self._current_org else None,
            'current_org_name': self._current_org.name if self._current_org else None,
            'current_org_role': self.get_organization_role(),
            'organizations_count': len(self._organizations) if self._organizations else 0,
            'jwt_claims': self.jwt_claims
        }


class OrganizationContext:
    """Represents organization-specific context and settings"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
        self._usage_data: Optional[OrganizationUsage] = None

    async def get_current_usage(self) -> Optional[OrganizationUsage]:
        """Get current month's usage data"""
        if self._usage_data is None:
            try:
                current_month = date.today().replace(day=1)
                # In a real implementation, this would query organization_usage table
                # For now, return None as usage tracking might not be implemented yet
                self._usage_data = None
                logger.info(f"Retrieved usage data for organization {self.organization.id}")
            except Exception as e:
                logger.error(f"Error getting usage data for organization {self.organization.id}: {e}")
                self._usage_data = None
        return self._usage_data

    async def check_document_limit(self) -> bool:
        """Check if organization is within document processing limits"""
        try:
            usage = await self.get_current_usage()
            # Default limit if no usage tracking
            default_limit = 1000
            
            if not usage:
                return True  # Allow if no usage tracking
            
            return usage.documents_processed < default_limit
        except Exception as e:
            logger.error(f"Error checking document limit: {e}")
            return True  # Allow on error

    async def check_storage_limit(self) -> bool:
        """Check if organization is within storage limits"""
        try:
            usage = await self.get_current_usage()
            # Default limit if no usage tracking
            default_limit_gb = 100
            
            if not usage:
                return True  # Allow if no usage tracking
            
            return usage.storage_used_gb < default_limit_gb
        except Exception as e:
            logger.error(f"Error checking storage limit: {e}")
            return True  # Allow on error


# Authentication Functions
async def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    try:
        # Mock implementation for development
        # In production, use proper JWT library validation with secret key
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        payload = parts[1]
        # Add padding if necessary
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        
        # Basic validation
        if 'sub' not in claims:
            raise ValueError("Token missing subject")
        
        return claims
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}")
        raise AuthenticationError("Invalid or malformed token")


async def get_user_from_token(token: str) -> UserContext:
    """Extract user information from JWT token"""
    try:
        claims = await decode_jwt_token(token)
        
        # Extract user information from claims
        user_id_str = claims.get('sub', '')
        if not user_id_str:
            raise AuthenticationError("Token missing user ID")
        
        user_id = uuid.UUID(user_id_str)
        email = claims.get('email', '')
        full_name = claims.get('name', claims.get('full_name', ''))
        
        if not email:
            raise AuthenticationError("Token missing email")
        
        # Check if user is superadmin
        is_superadmin = False
        try:
            superadmin_record = await database_service.get_record_by_id('superadmins', user_id)
            is_superadmin = superadmin_record is not None
        except Exception as e:
            logger.warning(f"Error checking superadmin status for user {user_id}: {e}")
            is_superadmin = False
        
        user_context = UserContext(
            user_id=user_id,
            email=email,
            full_name=full_name,
            is_superadmin=is_superadmin,
            jwt_claims=claims
        )
        
        logger.info(f"Authenticated user {user_id} ({email}), superadmin: {is_superadmin}")
        return user_context
        
    except ValueError as e:
        logger.error(f"Invalid user data in token: {e}")
        raise AuthenticationError("Invalid user data in token")
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        raise AuthenticationError("Authentication failed")


# FastAPI Dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    """FastAPI dependency to get current authenticated user"""
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Authentication token required")
    
    try:
        return await get_user_from_token(credentials.credentials)
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Authentication failed")


async def get_current_user_with_org(
    request: Request,
    user: UserContext = Depends(get_current_user)
) -> UserContext:
    """FastAPI dependency to get current user with organization context"""
    try:
        # Try to get organization ID from various sources
        org_id_header = request.headers.get('x-organization-id')
        org_id_path = request.path_params.get('org_id')
        
        org_id_str = org_id_header or org_id_path
        
        if org_id_str:
            try:
                org_id = uuid.UUID(org_id_str)
                await user.set_current_organization(org_id)
                logger.info(f"Set organization context: {org_id}")
            except (ValueError, AuthorizationError) as e:
                logger.warning(f"Invalid organization context: {e}")
                # Don't raise error here, let the endpoint handler decide
        else:
            logger.debug("No organization context provided")
        
        return user
    except Exception as e:
        logger.error(f"Error setting organization context: {e}")
        return user


def require_organization_permission(permission: str):
    """Decorator factory for requiring specific organization permissions"""
    def permission_dependency(user: UserContext = Depends(get_current_user_with_org)) -> UserContext:
        if not user.has_organization_permission(permission):
            raise AuthorizationError(f"Insufficient permissions: {permission}")
        return user
    return permission_dependency


def require_superadmin():
    """Dependency for requiring superadmin access"""
    def superadmin_dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not user.is_superadmin:
            raise AuthorizationError("Superadmin access required")
        return user
    return superadmin_dependency


def require_organization_role(min_role: str):
    """Decorator factory for requiring minimum organization role"""
    role_hierarchy = {'viewer': 0, 'editor': 1, 'admin': 2, 'owner': 3}
    min_level = role_hierarchy.get(min_role, 0)
    
    def role_dependency(user: UserContext = Depends(get_current_user_with_org)) -> UserContext:
        current_role = user.get_organization_role()
        current_level = role_hierarchy.get(current_role, 0)
        
        if current_level < min_level and not user.is_superadmin:
            raise AuthorizationError(f"Role '{min_role}' or higher required. Current role: {current_role}")
        return user
    return role_dependency


def require_organization_context():
    """Dependency for requiring organization context to be set"""
    async def org_context_dependency(user: UserContext = Depends(get_current_user_with_org)) -> UserContext:
        await user.require_organization_context()
        return user
    return org_context_dependency


# Audit Logging Helper
async def log_user_action(
    user: UserContext, 
    action: str, 
    scope: str,
    record_id: Optional[uuid.UUID] = None,
    diff: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    category_id: Optional[uuid.UUID] = None
):
    """Log user action for audit trail"""
    try:
        org_id = user._current_org.id if user._current_org else None
        ip_address = None
        user_agent = None
        
        if request:
            # Get client IP (considering proxy headers)
            ip_address = (
                request.headers.get('x-forwarded-for', '').split(',')[0].strip() or
                request.headers.get('x-real-ip') or
                (request.client.host if request.client else None)
            )
            user_agent = request.headers.get('user-agent')
        
        await database_service.create_audit_log(
            scope=scope,
            action=action,
            org_id=org_id,
            actor_user_id=user.user_id,
            record_id=record_id,
            diff=diff,
            category_id=category_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"Logged audit event: {action} on {scope} by user {user.user_id}")
    except Exception as e:
        logger.error(f"Error logging user action: {e}")
        # Don't fail the request if audit logging fails


# Organization Context Helpers
async def get_organization_context(org_id: uuid.UUID) -> OrganizationContext:
    """Get organization context for business logic"""
    try:
        org = await database_service.get_organization(org_id)
        if not org:
            raise AuthorizationError(f"Organization {org_id} not found")
        
        return OrganizationContext(org)
    except Exception as e:
        logger.error(f"Error getting organization context: {e}")
        raise


async def check_organization_limits(org_context: OrganizationContext, operation: str) -> bool:
    """Check if organization can perform operation within limits"""
    try:
        if operation == 'upload_document':
            return await org_context.check_document_limit()
        elif operation == 'storage':
            return await org_context.check_storage_limit()
        
        return True  # Allow unknown operations
    except Exception as e:
        logger.error(f"Error checking organization limits: {e}")
        return True  # Allow on error


# Utility Functions
def mask_sensitive_data(data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:
    """Mask sensitive data in dictionary for logging"""
    if sensitive_fields is None:
        sensitive_fields = ['password', 'api_key', 'secret', 'token', 'hash']
    
    masked_data = data.copy()
    for field in sensitive_fields:
        if field in masked_data:
            masked_data[field] = '***masked***'
    
    # Also mask fields that look sensitive
    for key, value in list(masked_data.items()):
        if isinstance(key, str) and any(word in key.lower() for word in ['password', 'secret', 'key', 'token']):
            masked_data[key] = '***masked***'
    
    return masked_data


def get_user_display_name(user: UserContext) -> str:
    """Get user's display name for UI/logging"""
    return user.full_name if user.full_name and user.full_name != user.email else user.email


async def validate_organization_access(user: UserContext, org_id: uuid.UUID) -> bool:
    """Validate that user has access to organization"""
    if user.is_superadmin:
        return True
    
    try:
        organizations = await user.get_organizations()
        return any(org.id == org_id for org in organizations)
    except Exception as e:
        logger.error(f"Error validating organization access: {e}")
        return False


# Error Handlers
class AuthErrorHandler:
    @staticmethod
    def invalid_token():
        return AuthenticationError("Invalid or expired token")
    
    @staticmethod
    def insufficient_permissions(required_permission: str):
        return AuthorizationError(f"Insufficient permissions: {required_permission}")
    
    @staticmethod
    def organization_access_denied(org_id: uuid.UUID):
        return AuthorizationError(f"Access denied to organization {org_id}")
    
    @staticmethod
    def resource_not_found(resource_type: str, resource_id: uuid.UUID):
        return HTTPException(status_code=404, detail=f"{resource_type} {resource_id} not found")