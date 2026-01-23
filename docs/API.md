# API Documentation

## Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://yourdomain.com/api/v1`

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Authentication

#### POST /auth/register

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "display_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "role": "student"
}
```

#### POST /auth/login

Authenticate and get tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "mfa_code": "123456"  // Optional, if MFA enabled
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /auth/refresh

Refresh access token.

**Query Parameters:**
- `refresh_token`: The refresh token

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### Resources

#### GET /resources

List resources with pagination.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `size` (int): Items per page (default: 20, max: 100)

**Response (200):**
```json
{
  "results": [...],
  "total": 150,
  "page": 1,
  "pages": 8
}
```

#### POST /resources/upload

Upload a new resource. Requires authentication.

**Request (multipart/form-data):**
- `file`: The file to upload
- `title`: Resource title
- `course_code`: Course code (e.g., CS101)
- `description` (optional): Description
- `department` (optional): Department name
- `semester` (optional): Semester
- `tags` (optional): Comma-separated tags
- `visibility` (optional): public, unlisted, private

**Response (201):**
```json
{
  "id": "uuid",
  "title": "Data Structures Notes",
  "slug": "data-structures-notes-abc123",
  "course_code": "CS101"
}
```

#### GET /resources/{id}/download

Download a resource file.

**Query Parameters:**
- `password` (optional): If password-protected

**Response:** File stream

---

### Search

#### GET /search

Search resources.

**Query Parameters:**
- `q`: Search query
- `course_code` (optional): Filter by course
- `department` (optional): Filter by department
- `tags` (optional): Comma-separated tags
- `sort_by`: recent, downloads, rating, relevance
- `page`, `size`: Pagination

**Response (200):**
```json
{
  "results": [...],
  "total": 25,
  "page": 1,
  "pages": 3,
  "query": "algorithms"
}
```

#### GET /search/filters

Get available filter options.

**Response (200):**
```json
{
  "courses": ["CS101", "CS201", ...],
  "departments": ["Computer Science", ...],
  "tags": ["notes", "exam", ...]
}
```

---

### Ratings

#### POST /ratings/resources/{resource_id}

Submit a rating. Requires authentication.

**Request:**
```json
{
  "value": 5,
  "review": "Excellent notes!"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "value": 5,
  "review": "Excellent notes!"
}
```

---

### Admin

*Requires admin role*

#### GET /admin/dashboard

Get platform statistics.

**Response (200):**
```json
{
  "total_users": 1500,
  "total_resources": 3200,
  "total_downloads": 25000,
  "total_storage_gb": 45.5,
  "pending_reports": 3,
  "new_users_7d": 50,
  "new_resources_7d": 120
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

**Status Codes:**
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Server Error
