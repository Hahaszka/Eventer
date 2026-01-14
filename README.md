# Eventer
## Author: Kacper Michalski

Eventer is a location-based social platform designed to help users organize and join real-time events in their vicinity. The main goal of the application is to facilitate spontaneous interactions and build local communities.

---

## 🚀 How to Run

There are two ways to start the program. Choose the one that suits your environment best.

### Option 1: Docker (Recommended)
This is the easiest method as it handles all dependencies and environment isolation automatically.

1. Ensure you have **Docker** installed on your machine.
2. Clone the repository.
3. Open a terminal in the project directory.
4. Build and run the container:
   ```bash
   docker-compose up --build

*(Or use the specific docker run command if no compose file is present)*.

### Option 2: Native Windows Start (`start.bat`)

Use this method if you want to run the application directly on your Windows machine without Docker.

**Prerequisites:**

-   **Python** (3.9 or higher recommended)

-   **PostgreSQL** database installed and **running**.

**Steps:**

1.  Ensure your PostgreSQL server is active.

2.  Configure your database connection strings in the environment variables or config file.

3.  Run the automated startup script:

    DOS

    ```
    start.bat

    ```

    *This script will automatically install required Python dependencies and start the FastAPI server.*

* * * * *

⚙️ Configuration (`config.yaml`)
--------------------------------

The application is highly configurable via the `config.yaml` file. You can modify this file to change application behavior without touching the code.

Key settings include:

-   **Admin Setup:** You can define the default Administrator account credentials.

-   **Data Seeding (Random Events):**

    -   Set `generate_random_events: true` (or equivalent flag) to populate the database with dummy events upon startup.

    -   This is useful for testing the UI and "Events nearby" features immediately.

* * * * *

🛠️ Tech Stack
--------------

-   **Backend:** Python, FastAPI (Async)

-   **Database:** PostgreSQL, SQLAlchemy (Async)

-   **Frontend:** HTML5, Bootstrap 5, JavaScript/jQuery

-   **DevOps:** Docker

📝 Features
-----------

-   **User System:** Registration, Login, Session Management.

-   **Profiles:** Separation between Private (editable) and Public (read-only) profiles to protect sensitive data (e.g., email).

-   **Events:** Create, view, and manage local events with descriptions, dates, and locations.

-   **Privacy:** Dedicated data schemas to ensure user privacy in public views.

* * * * *

### Project Status

The application is currently in the **MVP (Minimum Viable Product)** stage. It was developed in 2-week sprints using **Jira** for task management.
