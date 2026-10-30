# 📖 User Guide — Student Resource Library

> Your complete guide to sharing and discovering study materials on the Student Resource Library platform.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Homepage](#homepage)
3. [Browsing Resources](#browsing-resources)
4. [Viewing a Resource](#viewing-a-resource)
5. [Uploading a Resource](#uploading-a-resource)
6. [Downloading Files](#downloading-files)
7. [Rating & Reviewing](#rating--reviewing)
8. [Reporting Content](#reporting-content)
9. [Your Profile](#your-profile)
10. [Account Settings](#account-settings)
11. [Security Features](#security-features)
12. [FAQ](#faq)

---

## Getting Started

### Creating an Account

1. Go to the website homepage
2. Click the **user icon** (👤) in the top-right corner → **Register**
3. Fill in:
   - **Full Name**
   - **Email Address**
   - **Password** (minimum 8 characters)
4. Click **Create Account**
5. You'll be automatically logged in and redirected to the homepage

### Logging In

1. Click the **user icon** → **Login**
2. Enter your **email** and **password**
3. If MFA is enabled, enter your **6-digit code** from your authenticator app
4. Click **Sign In**

### Navigation

The top navigation bar provides quick access to:

| Item | Description |
|------|-------------|
| **Home** | Platform homepage with search and live stats |
| **Browse** | Browse all available resources |
| **Upload** | Upload a new resource |
| **Search** (🔍) | Quick search bar for instant results |
| **Upload** button (blue) | Quick upload shortcut |
| **Profile** (👤) | Your profile, settings, and logout |

On **mobile devices**, the navigation collapses into a **hamburger menu** (☰) accessible from the top-right corner.

---

## Homepage

The homepage is your starting point:

### Hero Section
- **Search Bar** — Search for resources by title, course code, or description
- **Browse All** — Go to the full resource browser
- **Upload Resource** — Quick link to upload a file

### Live Statistics
The homepage shows real-time platform stats:
- 📚 **Resources** — Total uploaded study materials
- 👥 **Users** — Registered students
- ⬇️ **Downloads** — Total file downloads
- 📘 **Courses** — Available course categories

### Recent Resources
The latest uploaded and approved resources appear on the homepage for quick access.

---

## Browsing Resources

**URL**: `/browse`

### Search & Filter

1. **Search Box** — Type keywords (title, course code, description)
2. Click **Search** or press **Enter**
3. Click **Filters** to expand advanced options:

| Filter | Description |
|--------|-------------|
| **Department** | Filter by academic department (e.g., Computer Science) |
| **Course Code** | Filter by specific course (e.g., CS101) |
| **Semester** | Filter by semester |
| **Tags** | Filter by resource tags |

### Resource Cards

Each resource card shows:
- 📄 **Title** — Resource name
- 👤 **Uploader** — Who uploaded it
- 📘 **Course Code** — Associated course
- 📏 **File Size** — e.g., "2.5 MB"
- ⬇️ **Downloads** — Download count
- 👁️ **Views** — View count
- 🏷️ **Tags** — Clickable tag badges

Click any card to open the **resource detail page**.

---

## Viewing a Resource

**URL**: `/resources/{slug}`

The resource detail page has two columns:

### Left Column — Content
1. **Header** — Title, course badge, department, semester
2. **Stats Bar** — Downloads, views, average rating, upload date
3. **Description** — Full description text
4. **Tags** — Clickable tags that link to filtered browse results
5. **Ratings & Reviews** — Star ratings and user comments

### Right Column — Actions (Sticky Sidebar)
The right sidebar stays visible as you scroll:

1. **File Size & Type** — e.g., "2.5 MB — PDF file"
2. **Download Button** — Click to download with progress bar
3. **Preview Button** — (for PDF, DOCX, PPTX, XLSX, TXT, MD, JPG, and PNG files; ZIP shows a file listing) Opens an in-browser preview modal
4. **Share Button** — Copies the resource URL to clipboard
5. **Report Button** — Report inappropriate content
6. **File Information** — Filename, MIME type, size, upload date, visibility

### Preview Modal

Clicking **Preview File** opens a modal that renders the file right in your browser — no download needed:

- **PDF & images (JPG/PNG)** — inline viewer, centered
- **DOCX** — formatted document text
- **PPTX** — slides listed in order, scrollable
- **XLSX** — spreadsheet tables with sheet tabs
- **TXT & MD** — plain text / rendered markdown
- **ZIP** — list of the archive's files and sizes

Header buttons: **Download**, **Fullscreen study mode** (edge-to-edge, distraction-free — ideal for slides and notes; press `Esc` to leave fullscreen, `Esc` again to close), and **Close**.

---

## Uploading a Resource

**URL**: `/upload`

### Step-by-Step

1. Navigate to **Upload** (top nav or homepage button)
2. **Drag & Drop** a file onto the upload zone, or click **"click to browse"**
3. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| **File** | ✅ | The file to upload (max 50 MB) |
| **Title** | ✅ | Descriptive title for the resource |
| **Department** | ✅ | Select from dropdown |
| **Course Code** | ✅ | Select from available courses |
| **Semester** | ❌ | e.g., "1st Semester" |
| **Description** | ❌ | Detailed description of the content |
| **Tags** | ❌ | Comma-separated keywords |
| **Visibility** | ❌ | `Public` (default) or `Private` |
| **Password** | ❌ | Optional password protection |

4. Click **Upload Resource**
5. Progress bar shows upload status
6. On success, you're redirected to the resource detail page

### Accepted File Formats

| Category | Extensions |
|----------|------------|
| Documents | PDF, DOC, DOCX |
| Presentations | PPT, PPTX |
| Spreadsheets | XLS, XLSX |
| Archives | ZIP, RAR |
| Text | TXT, MD |
| Images | JPG, PNG |

### File Size Limit
- **Maximum**: 50 MB per file
- **Storage Quota**: Unlimited

---

## Downloading Files

### Standard Download
1. Open the resource detail page
2. Click the **Download** button
3. The download starts with a progress bar
4. File saves to your browser's default download location

### Password-Protected Files
1. Click **Download**
2. A password field appears
3. Enter the password provided by the uploader
4. Click **Download** again

### Previewing Before Download
For PDFs and images:
1. Click **Preview File** instead of Download
2. View the content in the browser
3. Use the download button in the preview modal if you want to save it

---

## Rating & Reviewing

### Star Rating
1. Open a resource detail page
2. Scroll to **"Ratings & Reviews"**
3. Click on 1–5 stars to select your rating
4. Click **Confirm Rating** to save

### Writing a Review
1. Below the star rating, type in the **"Add a Review / Comment"** text box
2. Share your thoughts, feedback, or questions
3. Click **Post Comment**

### Viewing Reviews
- All reviews appear below the rating form
- Each review shows:
  - User avatar and name
  - Star rating (1–5)
  - Comment text
  - Date posted

> 💡 You must be **logged in** to leave a rating or review.

---

## Reporting Content

If you find inappropriate, copyrighted, or incorrect content:

1. Open the resource detail page
2. Click the **Report** button (flag icon) in the sidebar
3. Fill in the report form:
   - **Reason** — why you're reporting
   - **Details** — additional context
4. Submit the report
5. A moderator will review and take action

---

## Your Profile

**URL**: `/profile`

### Profile Dashboard

Your profile page displays:
- **Name & Email** — Your account information
- **Role Badge** — Student, Moderator, or Admin
- **Quick Actions** — Admin panel (if admin), Settings, Logout

### Statistics
- 📦 **Storage Used** — Your total upload size (with unlimited quota)
- ⬆️ **Total Uploads** — Resources you've uploaded
- ⬇️ **Total Downloads** — Downloads across your resources
- ⭐ **Average Rating** — Average rating of your resources

### Your Resources
A table of all resources you've uploaded, showing:
- Title, course code, size
- Download count and status
- Moderation status (pending/approved/rejected)

---

## Account Settings

**URL**: `/settings`

### Profile Settings
- Update your **display name**
- Change your **email address**
- Change your **password**

### Two-Factor Authentication (MFA)
1. Go to **Settings → Security**
2. Click **Enable 2FA**
3. Scan the QR code with Google Authenticator (or similar app)
4. Enter the 6-digit verification code
5. Click **Verify & Enable**

To disable MFA:
1. Go to **Settings → Security**
2. Enter your current MFA code
3. Click **Disable 2FA**

---

## Security Features

### Password Requirements
- Minimum 8 characters
- We recommend using a mix of letters, numbers, and symbols

### Session Security
- **Access tokens** expire after **24 hours**
- **Refresh tokens** last **30 days**
- Logging out invalidates all active sessions

### Two-Factor Authentication
- Uses **TOTP** (Time-based One-Time Password)
- Compatible with:
  - Google Authenticator
  - Microsoft Authenticator
  - Authy
  - Any TOTP app

### Rate Limiting
The platform limits requests to prevent abuse (60 requests/minute). If you hit the limit, wait briefly before retrying.

---

## FAQ

### How large can my files be?
Up to **50 MB** per file. There's no limit on total storage.

### What file types can I upload?
PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, ZIP, RAR, TXT, MD, JPG, and PNG.

### Can I edit a resource after uploading?
Yes, you can update the **title, description, tags, and visibility** from the resource detail page.

### Can I delete my own uploads?
Yes, go to the resource detail page and click **Delete** (if you're the uploader).

### Who can see my uploads?
- **Public** resources are visible to everyone
- **Private** resources are only visible to you

### How do password-protected files work?
When uploading, set a password. Anyone who wants to download or preview the file must enter that password.

### I forgot my password. What do I do?
Use the **"Forgot Password?"** link on the login page. A reset link will be sent to your email (if SMTP is configured).

### My upload is stuck as "pending." Why?
Your resource may be awaiting moderator approval. This depends on the platform settings. Contact your administrator if it takes too long.

### How do I report a problem?
1. Use the **Report** button on any resource page
2. Or contact the platform administrator directly

### Can I search for resources?
Yes! Use the search bar on the **Homepage** or **Browse** page. You can search by title, course code, description, and filter by department, course, semester, or tags.

---

<p align="center">
  Need admin help? See the <a href="OWNER_GUIDE.md">Owner Guide</a>.
</p>
