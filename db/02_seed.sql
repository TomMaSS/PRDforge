-- SnapHabit — Mobile habit tracker with AWS backend
-- Sample PRD demonstrating PRD Forge with 12 sections and 10 dependencies.

INSERT INTO projects (id, name, slug, description, version)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'SnapHabit',
    'snaphabit',
    'Mobile habit-tracking app with streak photos, social accountability, and an AWS serverless backend',
    1
);

-- 0: Overview
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'overview',
    'Overview & Goals',
    'overview',
    0,
    'approved',
    ARRAY['mvp', 'core'],
    'SnapHabit is a **mobile habit-tracking application** that combines daily streak tracking with photo proof and lightweight social accountability. Users create habits, log completions with optional photos, and share progress with accountability partners.

The primary goal is to increase habit retention by 40% compared to simple checklist apps by adding visual proof and social pressure. The app targets individuals aged 18-35 who want to build consistent routines around fitness, reading, meditation, or creative practices.

Key objectives:
- Simple habit creation with configurable frequency (daily, weekdays, custom)
- Photo-based completion logging with streak calendar visualization
- Accountability partner system with push notification nudges
- Cloud sync across devices with offline-first architecture
- Privacy-first: photos stored encrypted, shared only with explicit consent

The backend runs entirely on AWS serverless infrastructure to minimize ops overhead and scale automatically from zero to thousands of users.',
    'Mobile habit tracker with streak photos and social accountability. Targets 40% better retention vs checklist apps for users aged 18-35. AWS serverless backend with offline-first mobile architecture.',
    'Q: Should we support habit templates (pre-built habits) in v1?
Decision: Yes, ship 10 starter templates for common habits (exercise, reading, meditation, water intake).'
);

-- 1: User Research
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    'user-research',
    'User Research & Personas',
    'general',
    1,
    'approved',
    ARRAY['core'],
    'Three primary personas identified through 40 user interviews:

**Persona 1: "Gym Alex" (25, software engineer)**
- Wants to track gym visits with progress photos
- Current pain: forgets to log, loses streaks in existing apps
- Key need: frictionless logging (< 5 seconds), photo attachment
- Willing to pay $4.99/month for premium features

**Persona 2: "Reader Maya" (30, product manager)**
- Tracks reading habit (30 min/day) and meditation
- Current pain: no accountability, easy to skip without consequence
- Key need: accountability partner who gets notified on missed days
- Values privacy — won''t use apps that share data publicly

**Persona 3: "Creative Sam" (22, design student)**
- Tracks daily sketching, journaling, and language practice
- Current pain: too many apps for different habits
- Key need: single app for all habits with visual calendar
- Price-sensitive, prefers free tier with ads over subscription

**Key findings:**
- 85% of interviewees abandoned previous habit apps within 2 weeks
- Top reason for abandonment: "forgot to open the app" (62%)
- Social accountability rated as most desired missing feature (78%)
- Photo proof considered "fun and motivating" by 71% of respondents',
    'Three personas from 40 interviews: fitness tracker, reader/meditator, creative student. 85% abandon habit apps within 2 weeks. Top needs: frictionless logging, accountability partners, visual calendar.',
    ''
);

-- 2: Tech Stack
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000001',
    'tech-stack',
    'Technology Stack',
    'tech_spec',
    2,
    'approved',
    ARRAY['mvp', 'backend'],
    'Core technology decisions for SnapHabit:

**Mobile (cross-platform):**
- React Native 0.73 with Expo managed workflow
- TypeScript for type safety
- React Navigation for routing
- Zustand for client state management
- WatermelonDB for offline-first local database (SQLite-backed)
- expo-camera for photo capture, expo-notifications for push

**Backend (AWS serverless):**
- API Gateway (HTTP API) → Lambda (Node.js 20 runtime)
- Amazon DynamoDB for user data, habits, and completions
- Amazon S3 for encrypted photo storage (AES-256 server-side encryption)
- Amazon Cognito for authentication (email + Apple/Google social login)
- Amazon SNS for push notification delivery
- AWS CDK (TypeScript) for infrastructure as code

**Database design:**
- DynamoDB single-table design with GSI for access patterns
- PostgreSQL on Amazon RDS (db.t4g.micro) for analytics aggregation and reporting queries that don''t fit DynamoDB patterns
- S3 lifecycle rules: move photos to Glacier after 1 year

**CI/CD:**
- GitHub Actions for Lambda deployment and Expo EAS builds
- Jest + React Native Testing Library for unit tests
- Detox for end-to-end mobile tests',
    'React Native + Expo mobile app with TypeScript. AWS serverless backend: API Gateway, Lambda, DynamoDB, S3, Cognito. PostgreSQL on RDS for analytics. CDK for IaC, GitHub Actions CI/CD.',
    'TODO: Evaluate Supabase as simpler alternative to raw AWS services.
TODO: Benchmark DynamoDB vs PostgreSQL for habit completion queries at scale.'
);

-- 3: Data Model
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    'data-model',
    'Data Model',
    'data_model',
    3,
    'in_progress',
    ARRAY['mvp', 'backend'],
    'DynamoDB single-table design with composite keys and GSIs.

**Primary table: SnapHabit**

| PK | SK | Attributes |
|----|----|----|
| USER#userId | PROFILE | email, name, avatar_url, timezone, created_at |
| USER#userId | HABIT#habitId | title, frequency, reminder_time, color, icon, streak_current, streak_best, created_at |
| USER#userId | COMPLETION#habitId#date | photo_key (S3), note, completed_at |
| USER#userId | PARTNER#partnerId | status (pending/accepted), since |

**GSI1 (partner lookup):**
| GSI1PK | GSI1SK |
|--------|--------|
| PARTNER#partnerId | USER#userId |

**GSI2 (completions by date for analytics):**
| GSI2PK | GSI2SK |
|--------|--------|
| USER#userId | DATE#YYYY-MM-DD |

**PostgreSQL analytics tables (RDS):**
- `daily_aggregates` — per-user daily completion counts, synced from DynamoDB via Lambda
- `cohort_metrics` — retention curves, streak distributions
- `notification_log` — push notification delivery and open rates

**S3 structure:**
- `photos/{userId}/{habitId}/{date}.jpg` — completion photos (encrypted, lifecycle to Glacier at 365 days)
- `avatars/{userId}.jpg` — profile pictures',
    'DynamoDB single-table with USER/HABIT/COMPLETION/PARTNER entities. Two GSIs for partner lookup and date-based queries. PostgreSQL on RDS for analytics aggregation. S3 for encrypted photo storage.',
    'Q: Should completions be stored per-date (one item) or per-event (multiple)?
Decision: Per-date — one completion per habit per day, last write wins.'
);

-- 4: API Specification
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000005',
    'a0000000-0000-0000-0000-000000000001',
    'api-spec',
    'API Specification',
    'api_spec',
    4,
    'in_progress',
    ARRAY['mvp', 'backend'],
    'REST API via API Gateway + Lambda. All endpoints require Cognito JWT auth.

**Base URL:** `https://api.snaphabit.app/v1`

**Habits:**
- `POST /habits` — Create habit {title, frequency, reminder_time, color, icon}
- `GET /habits` — List user''s habits with current streak info
- `PUT /habits/{id}` — Update habit settings
- `DELETE /habits/{id}` — Archive habit (soft delete, preserves completions)

**Completions:**
- `POST /habits/{id}/complete` — Log completion {photo?: File, note?: string}
- `GET /habits/{id}/completions?month=YYYY-MM` — Monthly completion calendar
- `DELETE /habits/{id}/completions/{date}` — Undo completion

**Partners:**
- `POST /partners/invite` — Send partner request {email}
- `GET /partners` — List partners with statuses
- `PUT /partners/{id}/accept` — Accept partner request
- `DELETE /partners/{id}` — Remove partner

**Feed:**
- `GET /feed` — Partner activity feed (recent completions from partners)

**Photo upload:**
- `POST /photos/presign` — Get S3 pre-signed upload URL
- Photos uploaded directly to S3, then referenced in completion

**Rate limiting:** 100 req/min per user via API Gateway throttling.
**Pagination:** Cursor-based using `?cursor={lastKey}&limit=20`.',
    'REST API with Cognito JWT auth. CRUD for Habits, Completions (with photo upload via S3 pre-signed URLs), Partners (invite/accept flow), and activity Feed. Rate limited at 100 RPM.',
    'TODO: Add WebSocket endpoint for real-time partner activity updates.'
);

-- 5: Mobile App Design
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000006',
    'a0000000-0000-0000-0000-000000000001',
    'mobile-app',
    'Mobile App Design',
    'ui_design',
    5,
    'draft',
    ARRAY['mvp', 'frontend'],
    'React Native app with four primary screens:

**1. Today** — Daily habit checklist with one-tap completion.
- Habit cards with title, streak count, and completion button
- Long-press to attach photo and note
- Streak calendar ribbon at top showing last 7 days
- Pull-to-refresh for partner nudge notifications

**2. Calendar** — Monthly grid view per habit.
- Color-coded completion dots (green = done, gray = missed, yellow = rest day)
- Tap any day to see completion details and photo
- Swipe between months
- Streak statistics below calendar (current, best, total completions)

**3. Partners** — Accountability partner management.
- Partner list with their today status (completed/pending)
- "Nudge" button sends push notification to partner
- Activity feed showing recent partner completions with photos
- Invite flow via email or share link

**4. Profile** — Settings and statistics.
- Account settings (name, email, timezone, notification preferences)
- Overall statistics (habits active, total completions, longest streak)
- Export data as CSV
- Subscription management (free tier vs premium)

**Design system:**
- Colors: Warm palette — primary #FF6B35 (orange), bg #FAFAF8, surface #FFFFFF
- Typography: SF Pro (iOS) / Roboto (Android), system defaults
- Animations: Lottie for streak celebrations, spring animations for card interactions
- Offline: all screens work offline, sync indicator in nav bar',
    'Four-screen React Native app: Today (checklist + photo), Calendar (monthly grid + stats), Partners (accountability + nudges), Profile (settings + export). Warm color palette with offline-first architecture.',
    ''
);

-- 6: Push Notifications
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000007',
    'a0000000-0000-0000-0000-000000000001',
    'push-notifications',
    'Push Notifications',
    'tech_spec',
    6,
    'draft',
    ARRAY['mvp'],
    'Push notification system built on Amazon SNS with scheduled Lambda triggers.

**Notification types:**

1. **Habit reminder** — Sent at user''s configured reminder time for each habit.
   - Trigger: EventBridge scheduled rule → Lambda scans due reminders
   - Template: "Time for {habit_name}! You''re on a {streak} day streak"
   - Frequency: respects habit schedule (daily, weekdays, custom)

2. **Partner nudge** — Manual nudge from accountability partner.
   - Trigger: API call from partner → Lambda → SNS
   - Template: "{partner_name} is checking in — have you done {habit_name} today?"
   - Rate limit: max 2 nudges per partner per day

3. **Streak at risk** — Sent 2 hours before midnight if habit not completed.
   - Trigger: EventBridge rule at 10 PM user''s timezone → Lambda checks
   - Template: "Don''t break your {streak}-day streak on {habit_name}!"
   - Only sent if user hasn''t completed today

4. **Streak milestone** — Celebration at 7, 30, 100, 365 days.
   - Trigger: completion Lambda checks streak milestones
   - Template: "{streak} days of {habit_name}! You''re unstoppable."

**Infrastructure:**
- SNS platform applications for APNs (iOS) and FCM (Android)
- Device token stored in DynamoDB user profile
- Notification preferences: per-habit toggle, quiet hours, partner nudge opt-out
- Delivery tracking via SNS delivery logs → CloudWatch → PostgreSQL analytics',
    'Four notification types via SNS: habit reminders, partner nudges, streak-at-risk warnings, and milestone celebrations. EventBridge + Lambda triggers respect user timezone and preferences.',
    ''
);

-- 7: Authentication
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000008',
    'a0000000-0000-0000-0000-000000000001',
    'auth',
    'Authentication & Security',
    'security',
    7,
    'approved',
    ARRAY['mvp', 'backend'],
    'Authentication and security model built on Amazon Cognito.

**Authentication:**
- Email/password sign-up with verification
- Social login: Apple Sign-In (required for App Store) and Google Sign-In
- Cognito User Pool with custom attributes (timezone, subscription_tier)
- JWT tokens: 1-hour access token, 30-day refresh token
- Expo SecureStore for token persistence on device

**Authorization:**
- All API endpoints validate Cognito JWT via API Gateway authorizer
- Users can only access their own data (userId extracted from JWT sub claim)
- Partner data accessible only for accepted partnerships
- Photo URLs are pre-signed with 1-hour expiry

**Data protection:**
- S3 server-side encryption (AES-256) for all photos
- DynamoDB encryption at rest (AWS managed keys)
- TLS 1.3 for all API communication
- No PII stored beyond email, name, and photos
- GDPR: account deletion removes all data within 24 hours (Lambda cleanup job)

**Mobile security:**
- Certificate pinning for API domain
- Biometric unlock option (Face ID / fingerprint) via expo-local-authentication
- App lock after 5 minutes of inactivity (configurable)',
    'Cognito auth with email + Apple/Google social login. JWT-based API authorization. S3 AES-256 encryption for photos, TLS 1.3, certificate pinning. GDPR-compliant account deletion within 24 hours.',
    ''
);

-- 8: AWS Deployment
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000009',
    'a0000000-0000-0000-0000-000000000001',
    'deployment',
    'AWS Deployment',
    'deployment',
    8,
    'approved',
    ARRAY['backend'],
    'Fully serverless AWS deployment managed by CDK (TypeScript).

**Infrastructure stack:**
- API Gateway (HTTP API) with custom domain api.snaphabit.app
- Lambda functions (Node.js 20, ARM64, 256MB memory, 30s timeout)
- DynamoDB table with on-demand capacity (auto-scales to zero)
- S3 bucket with lifecycle rules and CloudFront CDN for photo delivery
- Cognito User Pool with hosted UI for social login callbacks
- RDS PostgreSQL (db.t4g.micro, single-AZ for dev, multi-AZ for prod)
- EventBridge rules for scheduled notification triggers
- CloudWatch dashboards and alarms

**Environments:**
- dev: single AWS account, minimal resources, deployed on every push to main
- staging: mirrors prod config, used for QA and load testing
- prod: multi-AZ RDS, CloudFront, Route 53, WAF on API Gateway

**CI/CD pipeline (GitHub Actions):**
1. Push to main → run unit tests + lint
2. CDK diff → deploy to dev
3. Manual approval → deploy to staging
4. Load test passes → deploy to prod
5. Expo EAS build → TestFlight (iOS) + Play Store internal track (Android)

**Cost estimate (1000 MAU):**
- Lambda: ~$2/month (500K invocations)
- DynamoDB: ~$5/month (on-demand)
- S3 + CloudFront: ~$3/month (10GB storage)
- RDS: ~$15/month (db.t4g.micro)
- Cognito: free tier (50K MAU)
- Total: ~$25/month',
    'CDK-managed serverless stack: API Gateway, Lambda, DynamoDB (on-demand), S3 + CloudFront, Cognito, RDS PostgreSQL. Three environments with GitHub Actions CI/CD. ~$25/month at 1000 MAU.',
    ''
);

-- 9: Analytics
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000010',
    'a0000000-0000-0000-0000-000000000001',
    'analytics',
    'Analytics & Monitoring',
    'tech_spec',
    9,
    'draft',
    ARRAY['backend'],
    'Analytics pipeline and operational monitoring for SnapHabit.

**Product analytics:**
- Mixpanel for user behavior tracking (habit creation, completion patterns, partner engagement)
- Key metrics: DAU/MAU ratio, 7-day retention, average streak length, completion rate by habit type
- Funnel: onboard → create first habit → first completion → 7-day streak → invite partner
- A/B testing via LaunchDarkly feature flags (notification copy, onboarding flow)

**Operational monitoring:**
- CloudWatch dashboards: Lambda duration/errors, API Gateway 4xx/5xx, DynamoDB consumed capacity
- CloudWatch Alarms → SNS → PagerDuty for P1 issues (API error rate > 5%, Lambda cold starts > 2s)
- X-Ray tracing on Lambda for request path analysis
- DynamoDB contributor insights for hot partition detection

**Analytics aggregation (PostgreSQL):**
- Lambda streams DynamoDB changes to PostgreSQL via DynamoDB Streams → Lambda → RDS
- Daily aggregation job: completion counts, streak distributions, cohort retention
- Metabase dashboard connected to RDS for business intelligence
- Weekly email report to stakeholders with key metric trends

**Privacy:**
- Analytics events contain no PII (anonymized user IDs)
- Mixpanel data retention: 12 months
- Users can opt out of analytics tracking in app settings',
    'Mixpanel for product analytics, CloudWatch + X-Ray for ops monitoring. DynamoDB Streams pipeline to PostgreSQL for aggregation. Metabase BI dashboards. Privacy-first with anonymized tracking.',
    ''
);

-- 10: Testing Strategy
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000011',
    'a0000000-0000-0000-0000-000000000001',
    'testing-strategy',
    'Testing Strategy',
    'testing',
    10,
    'in_progress',
    ARRAY['core'],
    'Testing pyramid for SnapHabit covering mobile and backend.

**Unit tests (80% coverage target):**
- Mobile: Jest + React Native Testing Library for component logic
- Backend: Jest for Lambda handlers with mocked AWS SDK (aws-sdk-client-mock)
- Run on every PR via GitHub Actions

**Integration tests:**
- Backend: LocalStack for AWS service mocking (DynamoDB, S3, Cognito)
- API contract tests: Pact for consumer-driven contracts between mobile and API
- Database: test DynamoDB access patterns with real table (on-demand, dev account)

**End-to-end tests:**
- Detox for React Native E2E on iOS simulator and Android emulator
- Critical flows: sign up → create habit → complete with photo → verify streak
- Run nightly on CI, results posted to Slack

**Load testing:**
- k6 scripts simulating 1000 concurrent users
- Target: p99 API latency < 500ms, zero DynamoDB throttling
- Run before every production deployment in staging environment

**Manual QA:**
- TestFlight + Play Store internal track for beta testing
- Checklist: offline mode, timezone edge cases, photo upload with poor connectivity
- Accessibility audit with VoiceOver (iOS) and TalkBack (Android)',
    'Testing pyramid: Jest unit tests (80% coverage), LocalStack integration tests, Detox E2E for mobile, k6 load tests (p99 < 500ms). Pact contract testing between mobile and API.',
    ''
);

-- 11: Timeline
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000012',
    'a0000000-0000-0000-0000-000000000001',
    'timeline',
    'Implementation Timeline',
    'timeline',
    11,
    'in_progress',
    ARRAY['mvp'],
    'Phased implementation plan for SnapHabit MVP and beyond.

**Phase 1 — Foundation (Weeks 1-4):**
- CDK infrastructure setup (DynamoDB, S3, Cognito, API Gateway)
- Lambda CRUD handlers for habits and completions
- React Native project setup with Expo, navigation, and offline DB
- Authentication flow (sign up, login, social auth)
- CI/CD pipeline for both backend and mobile

**Phase 2 — Core Features (Weeks 5-8):**
- Habit creation and completion with photo upload
- Streak calculation engine and calendar visualization
- Push notification system (reminders + streak-at-risk)
- Offline-first sync between WatermelonDB and DynamoDB
- Basic analytics instrumentation (Mixpanel + CloudWatch)

**Phase 3 — Social & Polish (Weeks 9-12):**
- Accountability partner system (invite, accept, nudge)
- Partner activity feed
- Streak celebration animations (Lottie)
- Onboarding flow with habit templates
- Beta testing via TestFlight and Play Store internal track

**Phase 4 — Launch Prep (Weeks 13-14):**
- Load testing and performance optimization
- App Store and Play Store submission
- Landing page and marketing site
- Analytics dashboard setup (Metabase)

**MVP definition:** Phases 1-3 complete. Users can create habits, log completions with photos, track streaks, and share with accountability partners.

**Post-MVP backlog:**
- Premium subscription tier (unlimited habits, advanced stats, custom themes)
- Habit groups and challenges
- Widget support (iOS WidgetKit, Android Glance)
- Apple Watch companion app',
    'Four-phase plan: Foundation (weeks 1-4, AWS + RN setup), Core Features (5-8, habits + streaks + notifications), Social & Polish (9-12, partners + onboarding), Launch Prep (13-14). MVP = phases 1-3.',
    'Blocked on: Apple Developer Program enrollment (in progress).'
);

-- Dependencies (12 total)
-- tech-stack → data-model
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000003', 'implements', 'DynamoDB schema decisions from tech stack');

-- tech-stack → api-spec
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000003', 'implements', 'API Gateway + Lambda patterns from tech stack');

-- data-model → api-spec
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000004', 'references', 'API endpoints mirror DynamoDB access patterns');

-- api-spec → mobile-app
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000006', 'b0000000-0000-0000-0000-000000000005', 'implements', 'Mobile app consumes the REST API');

-- tech-stack → auth
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000008', 'b0000000-0000-0000-0000-000000000003', 'implements', 'Cognito configuration from tech stack decisions');

-- api-spec → push-notifications
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000007', 'b0000000-0000-0000-0000-000000000005', 'references', 'Nudge endpoint triggers push notifications');

-- tech-stack → deployment
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000003', 'implements', 'CDK stack mirrors tech stack choices');

-- deployment → analytics
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000009', 'references', 'CloudWatch and RDS from deployment stack');

-- data-model → timeline
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000012', 'b0000000-0000-0000-0000-000000000004', 'references', 'Phase 1 scope includes data model implementation');

-- mobile-app → timeline
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000012', 'b0000000-0000-0000-0000-000000000006', 'references', 'Phase 2-3 scope includes mobile app features');

-- user-research → mobile-app (personas inform UX decisions)
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000006', 'b0000000-0000-0000-0000-000000000002', 'references', 'Persona needs drive screen design and feature priorities');

-- api-spec → testing-strategy (test plan validates API contracts)
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES ('a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000011', 'b0000000-0000-0000-0000-000000000005', 'references', 'Pact contract tests and k6 load tests target API endpoints');
