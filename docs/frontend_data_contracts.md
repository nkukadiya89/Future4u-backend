# Frontend data contracts

These contracts describe the current frontend-facing API shapes used by the new
student flow.

## Common patterns in this codebase

All endpoints respond with:
- `{"success": true, "data": ...}` — success response
- `{"success": false, "message": "..."}` — error response

Frontend should treat:
- `success` as the primary boolean
- `message` as available on errors and some success responses
- `data` as the payload (object or list depending on endpoint)

## 1) Student Profile API

### GET `/api/student-profile/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `message`: string (optional)
  - `data`: object

`data` fields:
- `id`: string/UUID
- `user`: integer (user id)
- `role`: string
- `language`: array
- `country`, `state`, `city`: integer or null
- `country_name`, `state_name`, `city_name`: string or null
- `science_track`: string or null
- `medium`: string or null
- `education_level`: UUID or null
- `education_level_code`: string or null
- `education_level_name`: string or null
- `stream`: UUID or null
- `stream_code`: string or null
- `stream_name`: string or null
- `career_direction`: array
- `education`: array
- `skills`: array
- `projects`: array
- `internships`: array
- `certifications`: array
- `achievements`: array
- `extra_activities`: array
- `additional_insights`: array
- `linkedin_url`, `github_url`, `portfolio`: string or null

### PATCH `/api/student-profile/{profile_id}/`
- **Body**
  - any editable field from the profile, including:
  - `language`: array of UUIDs
  - `education_level`: UUID or null
  - `stream`: UUID or null
  - `science_track`: string or null
  - `medium`: string or null
  - `career_direction`, `education`, `skills`, `projects`, etc.
- **Response**: same shape as GET (success, data)

Current backend routing requires the profile id for PATCH. Use
`GET /api/student-profile/` first if the frontend does not already have
`profile_id`.

Null handling:
- `education_level` and `stream` can be `null` if not set.
- `stream` is only part of the student flow for secondary, higher_secondary, ITI, and diploma users.

## 2) Assessment APIs

Old assessment endpoints are removed:
- `GET /api/assessment/questions/`
- `POST /api/assessment/submit/`
- `GET /api/assessment/summary/`

Use the student assessment session endpoints below.

### POST `/api/student/assessments/`
- **Auth**: Bearer JWT
- **Body**: empty, or `{ "force_new": true }`
- **Response**
  - `success`: boolean
  - `message`: string
  - `resume`: boolean
  - `data`: object

If the user has an incomplete active assessment, this endpoint returns that
assessment with `resume=true`. Use `force_new=true` to create a new assessment
anyway.

`data` fields:
- `id`: assessment id
- `current_screen`: calculated screen key for resume
- `is_completed`: boolean

### GET `/api/student/assessments/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: array or paginated payload depending on pagination params

### GET `/api/student/assessments/status/`
- **Auth**: Bearer JWT
- **Purpose**: read the latest assessment resume state. Does not create an assessment.
- **Response**
  - `success`: boolean
  - `has_assessment`: boolean
  - `assessment_id`: integer or null
  - `is_completed`: boolean
  - `current_screen`: string
  - `data`: object or null

If no assessment exists:

```json
{
  "success": true,
  "has_assessment": false,
  "assessment_id": null,
  "is_completed": false,
  "current_screen": "education_level",
  "data": null
}
```

If an assessment exists, `data` contains:
- `education_level`: education level code or null
- `stream`: stream code or null
- `domain_category`: UUID or null
- `domain`: UUID or null

### GET `/api/student/assessments/{id}/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: assessment object

Assessment object fields:
- `id`
- `domain_category`: UUID or null
- `domain`: UUID or null
- `career_direction`: array
- `parent_support`: string or null
- `concerns`: array
- `career_values`: array
- `user_goals`: array
- `current_screen`: string, calculated by backend
- `user`: object
- `is_completed`: boolean
- audit fields from the base serializer

### PATCH `/api/student/assessments/{id}/`
- **Auth**: Bearer JWT
- **Body**: partial assessment fields
  - `domain_category`: UUID or null
  - `domain`: UUID or null
  - `career_direction`: array
  - `parent_support`: string or null
  - `concerns`: array
  - `career_values`: array
  - `user_goals`: array
- **Response**
  - `success`: boolean
  - `data`: updated assessment object

`current_screen` is read-only. Backend recalculates it after assessment PATCH,
answer save, and complete.

Domain validation:
- `domain_category` must be a parent domain (`parent = null`)
- `domain` must be a child domain
- `domain.parent` must equal `domain_category`

### GET `/api/questions/next/?assessment_id={id}`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: question object or null
  - `progress`: object

If there are no more questions:
- `data`: null
- `message`: string
- `progress.is_complete`: true

Question object fields:
- `id`: integer
- `question_text`: string
- `dimension`: string
- `question_type`: string (`mcq` or `text`)
- `options`: array

Option object fields:
- `id`: integer
- `option_text`: string
- `sequence_order`: integer

Progress object fields:
- `question_number`: integer
- `total_questions`: integer
- `answered`: integer
- `remaining`: integer
- `is_complete`: boolean

### POST `/api/responses/`
- **Auth**: Bearer JWT
- **Body**
  - `assessment`: assessment id
  - `question`: question id
  - `selected_option`: option id, required when `question_type` is `mcq`
  - `text_answer`: string, required when `question_type` is `text` (maximum 1000 characters)
- **Response**
  - `success`: boolean
  - `message`: string
  - `data`: object `{ current_screen: string }`

### POST `/api/student/assessments/{id}/complete/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `message`: string
  - `data`: object

`data` fields:
- `id`: assessment id
- `current_screen`: `complete`
- `is_completed`: true

## 3) Recommendation APIs

### GET `/api/ai-recommendations/{assessment_id}/`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object

`data` fields:
- `ai_disclaimer`: string
- `ai_insight`: string
- `top_suggestions`: array
- `easy_decision_making`: array
- `last_recommended_at`: datetime string

### GET `/api/ai-recommendations/{assessment_id}/chat/?suggestion_id={id}`
- **Auth**: Bearer JWT
- **Response**
  - `success`: boolean
  - `data`: object

### POST `/api/ai-recommendations/{assessment_id}/chat/`
- **Auth**: Bearer JWT
- **Body**
  - `suggestion_id`: integer
  - `message`: string
