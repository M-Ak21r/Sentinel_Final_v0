# MongoDB Configuration & User Credential Verification Guide

## 🔍 Step-by-Step Verification Process

Follow these steps in order to diagnose and fix your MongoDB connection:

---

## Step 1: Test MongoDB Connection

Run the connection test script to verify MongoDB is accessible:

```powershell
cd Sentinel_Unified\Web_Interface
node scripts\test-mongodb-connection.js
```

**What to look for:**
- ✅ "Successfully connected to MongoDB!" = Connection works
- ❌ Connection failed = Check the troubleshooting tips in the output

**Common Issues:**
- **ENOTFOUND**: Check internet connection or MongoDB Atlas hostname
- **Authentication failed**: Wrong username/password in MONGODB_URI
- **Timeout**: Firewall blocking or IP not whitelisted in MongoDB Atlas

---

## Step 2: Verify Environment Variables

Check that `.env.local` exists in the Web_Interface folder:

```powershell
Get-Content Sentinel_Unified\Web_Interface\.env.local
```

**Required variables:**
```env
MONGODB_URI=mongodb+srv://123mohammadakbar_db_user:Sentinel_V03@cluster0.l8vwx9u.mongodb.net/?appName=Cluster0
MONGODB_DB=security_dashboard
```

If the file doesn't exist:
```powershell
Copy-Item .env.example Sentinel_Unified\Web_Interface\.env.local
```

---

## Step 3: Test User Creation & Storage

Run the signup test to create a test user and verify it's saved:

```powershell
cd Sentinel_Unified\Web_Interface
node scripts\test-signup.js
```

**What it does:**
1. Connects to MongoDB
2. Creates a test user (test@sentinel.com / test123)
3. Verifies the user is actually saved in the database
4. Tests password hashing and verification

**If successful**, you'll see:
```
✅ SUCCESS! MongoDB is saving users correctly!

📝 Test credentials:
   Email: test@sentinel.com
   Password: test123
```

---

## Step 4: Create Your Admin User

Once MongoDB is working, create your actual admin account:

```powershell
cd Sentinel_Unified\Web_Interface
node scripts\create-admin-user.js
```

**Default credentials created:**
- Email: admin@sentinel.com
- Password: admin123

**⚠️ IMPORTANT:** Change this password after first login!

To customize the credentials, edit the script first:
```javascript
// In scripts/create-admin-user.js, change these lines:
const email = 'your@email.com'
const password = 'YourSecurePassword'
const name = 'Your Name'
```

---

## Step 5: Check MongoDB Atlas Dashboard

Login to your MongoDB Atlas account and verify:

1. **Cluster is running** (green status)
2. **Database "security_dashboard" exists**
3. **Collection "users" has documents**
4. **Network Access**: Add IP `0.0.0.0/0` to allow all IPs (or your specific IP)
5. **Database Access**: User `123mohammadakbar_db_user` has read/write permissions

---

## Step 6: Test Login with Web Interface

1. Start the Sentinel system:
```powershell
cd C:\Users\Mohammad Akbar\Documents\GitHub\Sentinel_Final_v0\Sentinel_Unified
python start_sentinel.py
```

2. Open browser and go to: `http://localhost:3000/auth/login`

3. Login with your credentials:
   - Email: admin@sentinel.com (or test@sentinel.com)
   - Password: admin123 (or test123)

4. **Watch the terminal output** for these log messages:
   - ✅ `[LOGIN] Connected to MongoDB users collection` = MongoDB working
   - ❌ `[LOGIN] MongoDB CONNECTION FAILED!` = Using mock users (temporary)

---

## Step 7: Monitor Logs for Issues

When you try to signup/login, watch the Web Interface terminal output:

**Good (MongoDB working):**
```
✅ [SIGNUP] Connected to MongoDB users collection
✅ [SIGNUP] User saved to MongoDB! ID: 676...
```

**Bad (Fallback to mock):**
```
❌ [SIGNUP] MongoDB CONNECTION FAILED!
⚠️  [SIGNUP] FALLING BACK TO MOCK USERS (IN-MEMORY ONLY)
⚠️  [SIGNUP] User will NOT be saved to database!
```

If you see the warning messages, MongoDB is not connecting properly.

---

## Troubleshooting Checklist

### ❌ "Invalid credentials" error:

**Cause:** No users exist in database yet
**Solution:** Run `node scripts/create-admin-user.js`

### ❌ MongoDB connection timeout:

**Cause:** IP not whitelisted or firewall blocking
**Solution:** 
1. Go to MongoDB Atlas → Network Access
2. Add IP Address: `0.0.0.0/0` (allow all)
3. Wait 2-3 minutes for changes to propagate

### ❌ Authentication failed:

**Cause:** Wrong credentials in MONGODB_URI
**Solution:** 
1. Check MongoDB Atlas → Database Access
2. Verify username: `123mohammadakbar_db_user`
3. Reset password if needed and update `.env.local`

### ❌ Users saved to mock instead of MongoDB:

**Cause:** `.env.local` not in Web_Interface folder
**Solution:** 
```powershell
Copy-Item .env.example Sentinel_Unified\Web_Interface\.env.local
```

### ❌ Next.js not reading environment variables:

**Cause:** Need to restart development server after changing .env.local
**Solution:** Stop and restart the Sentinel system

---

## Verification Commands Summary

```powershell
# 1. Test MongoDB connection
cd Sentinel_Unified\Web_Interface
node scripts\test-mongodb-connection.js

# 2. Test user creation
node scripts\test-signup.js

# 3. Create admin user
node scripts\create-admin-user.js

# 4. Start Sentinel
cd ..
python start_sentinel.py
```

---

## Success Indicators

✅ Connection test passes  
✅ Test user is saved to MongoDB  
✅ Admin user is created  
✅ Login works without "invalid credentials" error  
✅ Terminal shows "Connected to MongoDB users collection"  
✅ Users persist after server restart  

---

## Still Having Issues?

If all tests pass but login still fails, check:

1. **Browser console** (F12) for JavaScript errors
2. **Web Interface terminal** for server-side errors
3. **MongoDB Atlas Metrics** to see if connections are happening
4. Clear browser cache and cookies
5. Try incognito/private browsing mode

For more help, share the output of:
```powershell
node scripts\test-mongodb-connection.js
```
