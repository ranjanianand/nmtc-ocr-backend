"""
API Endpoint Validation Utility
Prevents duplicate endpoints and validates route definitions
"""

from fastapi import FastAPI
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EndpointValidator:
    """Validates API endpoints to prevent duplicates and conflicts"""

    def __init__(self):
        self.endpoints = defaultdict(list)
        self.duplicates_found = []

    def validate_app_routes(self, app: FastAPI) -> dict:
        """Validate all routes in a FastAPI application"""
        route_info = []
        duplicates = []

        # Collect all routes
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    route_key = f"{method}:{route.path}"
                    route_info.append({
                        'method': method,
                        'path': route.path,
                        'name': getattr(route, 'name', 'unnamed'),
                        'key': route_key
                    })

        # Find duplicates
        route_counts = defaultdict(int)
        for route in route_info:
            route_counts[route['key']] += 1

        duplicates = [
            route for route in route_info
            if route_counts[route['key']] > 1
        ]

        if duplicates:
            logger.error(f"Duplicate endpoints found: {duplicates}")
            self.duplicates_found = duplicates

        return {
            'total_routes': len(route_info),
            'unique_routes': len(set(r['key'] for r in route_info)),
            'duplicates': duplicates,
            'duplicate_count': len(duplicates),
            'is_valid': len(duplicates) == 0
        }

    def check_endpoint_conflicts(self, method: str, path: str) -> bool:
        """Check if an endpoint would conflict with existing ones"""
        route_key = f"{method}:{path}"
        return route_key in [ep['key'] for ep in self.duplicates_found]

    def get_route_summary(self, app: FastAPI) -> str:
        """Get a summary of all routes for debugging"""
        validation_result = self.validate_app_routes(app)

        summary = f"""
API Route Validation Summary:
- Total Routes: {validation_result['total_routes']}
- Unique Routes: {validation_result['unique_routes']}
- Duplicates Found: {validation_result['duplicate_count']}
- Validation Status: {'✅ PASSED' if validation_result['is_valid'] else '❌ FAILED'}
"""

        if not validation_result['is_valid']:
            summary += "\nDuplicate Endpoints:\n"
            for dup in validation_result['duplicates']:
                summary += f"  - {dup['method']} {dup['path']} ({dup['name']})\n"

        return summary

    def create_route_documentation(self, app: FastAPI, output_file: str = "api_routes.md"):
        """Create documentation of all API routes"""
        validation_result = self.validate_app_routes(app)

        content = f"""# API Routes Documentation
Generated automatically to prevent endpoint conflicts

## Route Summary
- **Total Routes:** {validation_result['total_routes']}
- **Unique Routes:** {validation_result['unique_routes']}
- **Duplicates:** {validation_result['duplicate_count']}
- **Status:** {'✅ Valid' if validation_result['is_valid'] else '❌ Has Conflicts'}

## All Routes
"""

        # Group routes by path prefix
        routes_by_prefix = defaultdict(list)
        all_routes = []

        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method != 'HEAD':  # Skip HEAD methods for cleaner output
                        prefix = route.path.split('/')[1] if '/' in route.path else 'root'
                        route_data = {
                            'method': method,
                            'path': route.path,
                            'name': getattr(route, 'name', 'unnamed'),
                            'prefix': prefix
                        }
                        routes_by_prefix[prefix].append(route_data)
                        all_routes.append(route_data)

        # Sort and display by prefix
        for prefix in sorted(routes_by_prefix.keys()):
            content += f"\n### /{prefix}\n"
            routes = sorted(routes_by_prefix[prefix], key=lambda x: (x['path'], x['method']))
            for route in routes:
                content += f"- **{route['method']}** `{route['path']}` - {route['name']}\n"

        if validation_result['duplicates']:
            content += "\n## ⚠️ Duplicate Endpoints Found\n"
            for dup in validation_result['duplicates']:
                content += f"- **{dup['method']}** `{dup['path']}` - {dup['name']}\n"

        try:
            with open(output_file, 'w') as f:
                f.write(content)
            logger.info(f"API routes documentation written to {output_file}")
        except Exception as e:
            logger.error(f"Failed to write route documentation: {e}")

        return content


# Global validator instance
endpoint_validator = EndpointValidator()


def validate_fastapi_app(app: FastAPI) -> bool:
    """Validate a FastAPI application for endpoint conflicts"""
    result = endpoint_validator.validate_app_routes(app)

    if not result['is_valid']:
        logger.error(f"❌ API validation failed: {result['duplicate_count']} duplicate endpoints")
        logger.error("Duplicate endpoints:")
        for dup in result['duplicates']:
            logger.error(f"  - {dup['method']} {dup['path']} ({dup['name']})")
        return False

    logger.info(f"✅ API validation passed: {result['unique_routes']} unique endpoints")
    return True


def startup_validation_middleware(app: FastAPI):
    """Middleware to validate endpoints on startup"""

    @app.on_event("startup")
    async def validate_endpoints():
        logger.info("Validating API endpoints...")
        is_valid = validate_fastapi_app(app)

        if not is_valid:
            logger.warning("API has duplicate endpoints - consider fixing before production")

        # Create route documentation
        endpoint_validator.create_route_documentation(app)

        # Log route summary
        summary = endpoint_validator.get_route_summary(app)
        logger.info(summary)

    return app