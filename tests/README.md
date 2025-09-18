# NMTC Backend Tests

This directory contains all testing and debugging utilities organized by category.

## Folder Structure

- **auth/** - Authentication and user management tests
- **azure/** - Azure Document Intelligence testing utilities  
- **database/** - Database schema and query tests
- **debug/** - General debugging and troubleshooting scripts
- **railway/** - Railway deployment testing (deprecated)
- **supabase/** - Supabase integration tests
- **workflow/** - End-to-end workflow and pipeline tests

## Usage

All testing files have been moved from the root directory to maintain a clean project structure. Run tests from the project root using:

```bash
python tests/[category]/[test_file].py
```

## Note

Railway-related tests are kept for historical reference but are no longer active as the project has moved away from Railway deployment.