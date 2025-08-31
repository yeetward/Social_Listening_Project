```mermaid
sequenceDiagram
    autonumber
    title Simple data flow: User Search to Results 
    actor U as User
    participant F as Frontend (UI)
    participant B as Backend (API)
    participant X as External Sources (Public APIs)
    participant D as Database
    participant A as AI/NLP Engine

    U->>F: Enter keyword & press Search
    F->>B: Send search request (HTTPS/JSON)
    B->>X: Fetch public posts/articles (GET)
    X-->>B: Return raw articles (JSON)

    B->>D: Store raw articles/metadata
    D-->>B: Confirm save

    B->>A: Submit articles for ranking & summarisation
    A->>A: Compute relevance scores & generate summaries
    A-->>B: Return ranked results

    B-->>F: Return ranked results (JSON)
    F-->>U: Display ranked results to user

    note over B,X: If an API fails or rate limits → continue with available sources
