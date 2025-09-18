# DATABASE SCHEMA DEPLOYMENT INSTRUCTIONS

## 🚨 **REQUIRED: Deploy Database Schema First**

The MVP workflow backend is ready, but requires database schema deployment.

### **Step 1: Deploy Allocation Years Schema**
```sql
-- Copy and run this in your Supabase SQL Editor:
-- File: database_allocation_years_2025_09_14.sql
```

### **Step 2: Deploy MVP Workflow Schema** 
```sql
-- Copy and run this in your Supabase SQL Editor:
-- File: database_mvp_workflow_2025_09_14.sql  
```

### **Step 3: Verify Deployment**
```sql
-- Run this to verify tables were created:
SELECT table_name, column_name, data_type
FROM information_schema.columns 
WHERE table_name IN ('allocation_years', 'qlici_loans')
ORDER BY table_name, column_name;
```

## 📋 **Deployment Order**

1. **First:** `database_allocation_years_2025_09_14.sql`
2. **Second:** `database_mvp_workflow_2025_09_14.sql`

## ✅ **After Database Deployment**

Run this to test backend:
```bash
python test_mvp_workflow_complete.py
```

**Expected Result:** All tests should pass with [SUCCESS] messages.

---

**Note:** The backend code is complete and tested. Only database schema deployment is needed before proceeding with frontend integration.