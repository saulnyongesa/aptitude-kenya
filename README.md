# Aptitude Kenya - Excellence in Digital Assessments

**Aptitude Kenya** is a specialized, secure, and scalable Computer-Based Testing (CBT) platform tailored for the Kenyan educational landscape. It bridges the gap between traditional teaching and modern examination methods with a focus on integrity, transparency, and ease of use for both Tutors and Students.

## ✨ Key Features

* **Dual-Role Authentication**: Unified login/register system with explicit role confirmation (Student vs. Tutor) to ensure data integrity and prevent account type errors.
* **Modern Minimalist UI**: Built with a "Corporate Minimalist" aesthetic—using thin borders (1px), subtle Emerald & Slate tones, and high-quality typography (Inter font).
* **Tutor Control**: Dedicated dashboards for educators to manage classrooms, host exams, and monitor student progress in real-time.
* **Student Portals**: Fully responsive interface allowing students to take exams securely across all devices—mobile, tablet, or desktop.
* **Real-time Analytics**: Instant auto-grading and institutional performance tracking to identify learning gaps immediately.
* **Security Focused**: Designed to minimize exam malpractice through secure proctoring environments and tutor-led session management.

## 🛠️ Tech Stack

* **Backend**: Python 3.x / Django
* **Frontend**: HTML5, CSS3 (Modern Minimalist Framework), JavaScript (ES6+)
* **UI Components**: Bootstrap 5 
* **Database**: PostgreSQL / SQLite
* **Authentication**: Custom User Model (Email-based login)

## 🚀 Getting Started

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/saulnyongesa/aptitude-kenya.git](https://github.com/saulnyongesa/aptitude-kenya.git)
    cd aptitude-kenya
    ```

2.  **Set up virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Migrations**:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Start the server**:
    ```bash
    python manage.py runserver
    ```

## 🎨 Design Philosophy
Aptitude Kenya moves away from aggressive "Neo-brutalist" styles toward a **Clean-Border UX**. By utilizing 1px borders, 12px border-radius, and a specific Emerald Green (`#10b981`) palette, the platform fosters a calm, professional environment suitable for high-stakes academic testing.

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Built with precision to serve the Kenyan Education Sector.*
