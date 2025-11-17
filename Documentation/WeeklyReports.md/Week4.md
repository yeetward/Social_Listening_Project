# Thread Title: Group 22 Week4

## MEETINGS WITH CLIENT
- **Date:** 21/08/25  
- **Time:** 5:00 PM  
- **Location:** Microsoft Teams  
- **Attendees:** Yousef, Anirudh, Edward, Eric, Khawaja, Miroslav(Sponsor), Humayun(Sponsor)

## MEETING WITH TEAM

### Meeting 1
- **Date:** 22/08/25  
- **Time:** 3:00 PM  
- **Location:** Discord  
- **Attendees:** Amr, Yousef, Edward, Eric, Anirudh, Khawaja

---

## WHAT DID WE DO THIS WEEK?

- Completed the first batch of wireframes while keeping them flexible to allow adjustments based on sponsor feedback. 
- Explored modern frontend techniques, especially Tailwind CSS with Django templates in order to improve maintainability and design consistency.
- Completed the initial setup and serialisation for the Django REST backend. 
- Began planning the process of wiring the API so that the frontend and AI modules can consume data consistently.
- Anirudh designed a relevancy score algorithm and presented it to the sponsor, who was supportive with only minor suggestions.
- - Approach 1: Use LangChain with an LLM to score article relevancy.
- - Approach 2: Weighted scoring combining TF-IDF, SBERT, Engagement metrics, and LLM outputs.


---

## WHAT WILL WE BE DOING NEXT WEEK?

- Submit draft documents (feasibility report, team manual, project plan, SRS) for sponsor review, then refine based on feedback.
- On our next team meeting, we will discuss and strategise how to complete deliverable 2. 


---

## ARE THERE ANY OBSTACLES / POTENTIAL OBSTACLES?

- Progress on certain parts of the system depends on the availability and clarity of data, which is not fully defined yet.

---

## INDIVIDUAL REFLECTIONS

- **Khawaja:** This week I shifted from feasibility to execution. I coordinated with the team to draft the backbone of our SRS, especially the NLP features (pre-processing, TF-IDF, SBERT similarity, hybrid ranking, engagement scoring) and non-functional targets (query latency, privacy compliance). In parallel, I prepared draft points for the Project Plan: roles, tools, low-cost data sources, risks, and a sprint schedule that keeps docs and build moving together. The sponsor’s constraint of “no paid LLM APIs” forced clearer technical choices; I outlined a local, affordable stack (spaCy, MiniLM, MongoDB Atlas, Celery) and a gold-set evaluation plan. 

What went well: team alignment on scope, concrete milestones, and an ambiguity-handling approach (entity biasing + semantic similarity).
Challenge: balancing documentation deadlines with setting up ingestion pipelines.
Next week: I’ll finalize SRS Section 3 (System Features).

- **Anirudh:** This week, I came up with a design for the relevancy score algorithm. I then presented the design to the sponsors and they seemed to be onboard with the proposed design with minor suggestions. To further work on the algorithm, I need to make myself familiar with some concepts foreign to me. I have learnt how to use pretrained models using hugging face this week. This will be extremely useful in text summarization and other NLP tasks we will need to implement to make the said design successful. From the documentation standpoint, I have contributed in the project plan, project progress, srs, team manual and feasibility report which are due for deliverable 2. 

- **Yousef:** This week, I concentrated on completing the first batch of wireframes for the core application screens, developing the drafts I began in week 3. I worked on the search results screen and the history screen, ensuring that both designs are clear and usable. I also explored modern front-end techniques, with an eye on Tailwind CSS and its integration with Django templates, as a way of keeping the UI lightweight and adaptable. One challenge I ran into was wireframing while not having the final backend data structures confirmed. This clouded my judgment about how much detail to embed in certain components. In response, I made the wireframes flexible so that they could adjust to whatever form the backend design ended up taking. I will next share the wireframes with the sponsor and team. I need their feedback and confirmation to move forward and prepare the Django template setup. Then i'll make the front end align with the backend workflow.

- **Eric:** This week I focused on catching up with the backend progress and reviewing what has been done so far. I have also been researching how to wire the API and thinking about the planning process to ensure smooth integration. Additionally, I have been working on improving the feasibility report and team manual based on the feedback given. I also worked on contributing the first draft for deliverable 2. My goal for next week is to start wiring the API, test the endpoints and document the backend so the team can build on it confidently.

- **Amr:** This week involved working on improving the feasibility report and team manual, in order to address the feedback given in Deliverable 1. Also contributed to the first draft of Deliverable 2. Goals for next week is to finalise the Deliverable 2 draft, and learn more about the NLP techniques to be used for the project.

- **Edward:** This week, I set up the database in the Django project and completed the initial migrations, created a basic serializer for handling data conversion, and researched materials related to building and structuring API endpoints to prepare for the next development steps, I also create bulletpoint for project progression report.
