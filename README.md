# Payday Budget

A comprehensive budgeting application designed around pay periods, allowing you to track expenses, manage budgets, and generate reports based on your paycheck schedule.

## Features

- **Pay Period Management**: Support for Weekly, Bi-Weekly, and Monthly pay periods
- **Category System**: Organize expenses with categories and sub-categories
- **Transaction Tracking**: Record and manage all your expenses
- **Budget Planning**: Set budgets per category for each pay period
- **Reporting**: Visual charts and reports to analyze spending patterns
- **Password Protection**: Secure authentication system
- **Multi-User Support**: Each user has their own isolated budget data

## Requirements

- Python 3.8 or higher
- Linux operating system
- Internet connection (for CDN resources)

## Quick Start

### Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Run the installation script:

```bash
chmod +x install.sh
./install.sh
```

### Running the Application

```bash
chmod +x start.sh
./start.sh
```

The application will be available at `http://localhost:5000`

### First Time Setup

1. Open your browser to `http://localhost:5000`
2. Click "Register" to create your account
3. Login with your credentials
4. Create your first pay period
5. Add categories (default categories are provided)
6. Start tracking transactions

## Usage Guide

### Pay Periods

1. Navigate to **Pay Periods** from the menu
2. Select your pay period type (Weekly, Bi-Weekly, or Monthly)
3. Enter the start date and your income
4. The end date is calculated automatically

### Categories

- Default categories are created on registration
- Create main categories with custom colors
- Add sub-categories under any main category
- Categories are used to organize transactions

### Transactions

1. Go to **Transactions**
2. Select the pay period
3. Choose a category
4. Enter description, amount, and date
5. Click "Add Transaction"

### Budgets

1. Navigate to **Budgets**
2. Select a category
3. Optionally select a specific pay period
4. Set your planned spending amount

### Reports

- View spending by category (pie chart)
- Analyze monthly spending trends (line chart)
- Filter reports by pay period
- See detailed breakdowns

## Updating the Application

To update dependencies or apply changes:

```bash
chmod +x update.sh
./update.sh
```

## Running as a System Service

To run Payday Budget as a systemd service that starts on boot:

```bash
chmod +x create_service.sh
sudo ./create_service.sh
```

Then manage the service with:

```bash
sudo systemctl start payday-budget
sudo systemctl enable payday-budget
sudo systemctl status payday-budget
```

## Deployment Options

### LXC/LXD Container

1. Create an Ubuntu LXC container:
```bash
lxc launch ubuntu:22.04 payday-budget
```

2. Access the container:
```bash
lxc exec payday-budget -- bash
```

3. Install Python and dependencies:
```bash
apt update
apt install python3 python3-venv python3-pip git -y
```

4. Clone and install the application
5. Expose the port:
```bash
lxc config device add payday-budget payday-port proxy listen=tcp:0.0.0.0:5000 connect=tcp:127.0.0.1:5000
```

### Podman (Docker Alternative)

1. Create a Containerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python3", "app.py"]
```

2. Build and run:
```bash
podman build -t payday-budget .
podman run -d -p 5000:5000 -v payday-data:/app payday-budget
```

### Standalone Linux Server

Simply follow the Quick Start instructions. The application runs on any Linux distribution with Python 3.8+.

## File Structure

```
Payday-Budget/
├── app.py                  # Main Flask application
├── models.py               # Database models
├── requirements.txt        # Python dependencies
├── install.sh             # Installation script
├── start.sh               # Startup script
├── update.sh              # Update script
├── create_service.sh      # Systemd service creator
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── pay_periods.html
│   ├── categories.html
│   ├── transactions.html
│   ├── budgets.html
│   └── reports.html
└── payday_budget.db       # SQLite database (created on first run)
```

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key (auto-generated if not set)

### Database

The application uses SQLite by default, with the database file stored as `payday_budget.db` in the application directory.

## Security Notes

- Change the default SECRET_KEY in production
- Use HTTPS in production (configure reverse proxy)
- Regular backups of payday_budget.db recommended
- Keep dependencies updated with update.sh

## Troubleshooting

### Port already in use
If port 5000 is in use, modify `app.py` line:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

### Database errors
Reset the database:
```bash
rm payday_budget.db
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Permission errors
Ensure scripts are executable:
```bash
chmod +x *.sh
```

## Backup and Restore

### Backup
```bash
cp payday_budget.db payday_budget_backup_$(date +%Y%m%d).db
```

### Restore
```bash
cp payday_budget_backup_YYYYMMDD.db payday_budget.db
```

## Support and Updates

This application is designed for easy updates via short prompts. To request features or modifications, simply describe the change needed.

## License

This project is provided as-is for personal and commercial use.
