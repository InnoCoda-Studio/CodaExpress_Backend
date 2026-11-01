⚙️ CodaExpress — Backend API & Core EngineThe central RESTful API engine powering the CodaExpress logistics & on-demand dispatch ecosystem.
Built with Django and Django REST Framework (DRF), this backend handles role-based routing, identity verification (KYC), real-time location capture, secure authentication, and transactional wallet ledgers.🛠 Tech StackCore Framework: Python 3.11+, Django, Django REST Framework (DRF)Database & Persistence: PostgreSQL (Supabase)Authentication & Security: JWT / Token Authentication, Role-Based Access Control (RBAC)Media & File Storage: Cloudinary API (Asynchronous Image Processing & CDN)Notifications & Messaging: Resend API & Google SMTP (OTP / Password Recovery)Hosting & Deployment: Render🌟 Key Functional Architecture🔀 1. Dynamic Role-Based Onboarding & Routing EngineUnified Onboarding Gateway: Single-entry portal that dynamically determines user intent (Rider vs. Customer) and routes them to specialized signup workflows.Direct Image Uploads: Integrated Cloudinary pipeline for immediate profile image capture and transformation during initial registration.🛡 2. Multi-Tiered Driver KYC & Approval SystemIdentity Verification: Riders submit government-issued credentials including National Identification Number (NIN), Driver’s License, and vehicle documentation.Location Capture: Stores initial rider operating zones and GPS baseline data.Admin Approval Queue: Status tracking system (Pending Approval → Verified / Rejected) allowing system administrators to audit credentials before granting dispatch access.🔐 3. Dual-Channel Password Recovery (Email & Phone OTP)Multi-Channel Reset: Secure password reset pipeline supporting both email-based tokens and phone number SMS OTP verification.Non-Blocking Notifications: Asynchronous email and message delivery pipelines to ensure microsecond API response times.📡 Essential API Endpoints🔑 Authentication & Identity (/api/v1/auth/)EndpointMethodDescription/api/v1/auth/register/POSTDynamic signup entry point for Customers & Riders/api/v1/auth/login/POSTAuthenticates user & returns token session/api/v1/auth/password-reset/POSTTriggers OTP / reset link via SMS or Email/api/v1/auth/password-reset/confirm/POSTVerifies OTP and updates user password🏍 Rider KYC & Onboarding (/api/v1/riders/)EndpointMethodDescription/api/v1/riders/kyc/POSTSubmits NIN, Driver’s License, vehicle info, and location/api/v1/riders/status/GETFetches current approval status (Pending, Approved)⚙️ Local Development Setup1. Clone the RepositoryBashgit clone https://github.com/InnoCoda/coda-express-backend.git
cd coda-express-backend

2. Create & Activate Virtual EnvironmentBash# On Linux / macOS
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
.\venv\Scripts\activate
3. Install DependenciesBashpip install -r requirements.txt
4. Environment Variables SetupCreate a .env file in the root directory (refer to .env.example):Code snippetSECRET_KEY=your_django_secret_key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:1234/codaexpress_db
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
RESEND_API_KEY=your_resend_api_key
5. Apply Migrations & Run Development ServerBashpython manage.py migrate
python manage.py runserver
🔗 Connected Repositories & PlatformMobile App Frontend: CodaExpress Mobile RepoParent Agency: innocoda.comLead Engineer Portfolio: me.innocoda.com
