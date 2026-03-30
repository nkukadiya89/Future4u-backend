# Frontend data contracts (current, backward-compatible)

These contracts describe **the current API shapes as implemented**.  
Per production safety rules, **existing response structures are not changed** here.

## Common patterns in this codebase

- Many endpoints respond with:
  - `{"success": true, "data": ...}` optionally with `message`
- Some newly added endpoints respond with:
  - `{"success": true, "status": true, "message": "", "data": ...}`

Frontend should treat:
- `success` as the primary boolean
- `message` as optional
- `data` as the payload (object or list depending on endpoint)

## 1) Profile API

### GET `/api/profile/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `status`: boolean (present)
  - `message`: string (present, may be empty)
  - `data`: object

`data` fields:
- `id`: string/UUID
- `user`: integer (user id)
- `education_level`: UUID or null
- `stream`: UUID or null

### POST `/api/profile/`
- **Body**
  - `education_level` (optional): UUID or null
  - `stream` (optional): UUID or null
- **Response**: same shape as GET

### PATCH `/api/profile/`
- **Body**: partial of POST
- **Response**: same shape as GET

Null handling:
- `education_level`, `stream` can be `null` if not set.

## 2) Assessment APIs

### GET `/api/assessment/questions/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object keyed by `dimension`

`data` example shape:
- `data["interest"]`: array of questions

Question object fields:
- `id`: integer
- `question_text`: string
- `dimension`: string
- `is_active`: boolean
- `options`: array

Option object fields:
- `id`: integer
- `option_text`: string
- `score_value`: integer

### POST `/api/assessment/submit/`
- **Auth**: Bearer JWT
- **Body**
  - `responses`: array of `{ question_id: int, option_id: int }`
- **Response**
  - `success`: boolean
  - `message`: string
  - `data`: object `{ submitted: number }`

### GET `/api/assessment/summary/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object keyed by `dimension` with integer totals

## 3) Recommendation APIs

### GET `/api/recommendations/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object

`data` fields:
- `top_domains`: array
- `top_careers`: array
- `skill_gaps`: array

### GET `/api/recommendations/domain/{id}/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object

`data` fields:
- `domain`: object
- `related_careers`: array of `{ id, name }`
- `required_skills`: array of `{ id, name }`

### GET `/api/careers/{id}/details/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object

`data` fields:
- `id`, `code`, `name`, `description`
- `required_skills`: array of `{ id, name }`
- `eligibility`: object
  - `min_education_level`: `{ id, name }`
  - `max_education_level`: `{ id, name }`

## 4) User Skill APIs

### GET `/user-skills/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: array

Array item fields:
- `id`: UUID
- `user`: integer
- `skill`: UUID
- `proficiency_score`: integer (0–100)
- `is_active`: boolean
- `deleted`: boolean
- `created_at`: datetime string
- `updated_at`: datetime string

### POST `/user-skills/`
- **Auth**: Bearer JWT
- **Body**
  - `skill`: UUID
  - `proficiency_score`: integer (0–100)
  - `is_active`: boolean (optional)

### PATCH `/user-skills/{id}/`
- **Auth**: Bearer JWT
- **Body**: partial of POST

