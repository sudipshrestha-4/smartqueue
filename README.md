# SmartQueue

A smart, token-based queue management system for banks, with real-time queue monitoring, priority handling, and live announcements.

Built for the Minor Project (BE Computer Engineering, Pokhara University)
by Sudip Shrestha, Saru Chauwal, and Pratik Karki — Nepal College of Information Technology (NCIT).

## Features

- **Token-based queuing**: customers join a service queue and receive a token (QR code supported)
- **Priority handling**: queue order is Emergency → Priority → Normal, then FIFO within each level
  - Token prefixes: `N` (Normal), `P` (Priority), `E` (Emergency)
- **Real-time updates**: Flask-SocketIO pushes live queue changes to customers, staff, and displays
- **Public counter display**: a `/display` screen showing currently served tokens
- **Live notifications**: audio alerts and voice announcements (browser Speech API) when a token is called
- **Role-based access**: separate customer, staff, and admin interfaces (Flask blueprints)
- **Admin dashboard**: manage services, counters, and staff; assign staff and services to counters
- **Multi-service support**: e.g. Cash Deposit, Cash Withdrawal, Customer Service
- **Wait-time estimation**: deterministic estimate shown to customers

## Tech Stack

- **Frontend:** HTML, Tailwind CSS, JavaScript, Bootstrap 5
- **Backend:** Python, Flask, Flask-SocketIO (eventlet), Flask-Login, Flask-WTF, Flask-Migrate
- **Database:** PostgreSQL (psycopg2, SQLAlchemy)

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL

### Installation

```bash
git clone https://github.com/sudipshrestha-4/smartqueue.git
cd smartqueue

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/smartqueue
```

### Database Setup

```bash
flask db upgrade
python seed_data.py            # seeds default services
python create_admin_staff.py   # creates an admin/staff account
```

### Run

```bash
python run.py
```

Then open `http://localhost:5000`.

## Project Structure

```
smartqueue/
├── app/
│   ├── customer/      # customer blueprint
│   ├── staff/         # staff blueprint
│   ├── admin/         # admin blueprint
│   ├── models/        # SQLAlchemy models
│   ├── templates/
│   └── static/
├── migrations/
├── seed_data.py
├── create_admin_staff.py
├── reset_services.py
├── list_users.py
├── verify_staff.py
└── run.py
```

## Helper Scripts

| Script | Purpose |
|---|---|
| `seed_data.py` | Seed default services |
| `create_admin_staff.py` | Create admin/staff accounts |
| `reset_services.py` | Reset services |
| `list_users.py` | List registered users |
| `verify_staff.py` | Verify staff accounts |

## Status

✅ Completed — developed as the Minor Project for BE Computer Engineering, Pokhara University.

## Team

- Sudip Shrestha
- Saru Chauwal
- Pratik Karki

## License

Academic project — Nepal College of Information Technology, Pokhara University.
